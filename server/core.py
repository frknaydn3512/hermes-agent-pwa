"""Plumbing: settings, database, log, push. No business logic here."""

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pywebpush import WebPushException, webpush

# Project root: one level above server/. .env, data/ and pwa/ live there.
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(HERE, ".env"))

APP_TOKEN = os.getenv("APP_TOKEN", "")
RATE_PER_MIN = int(os.getenv("RATE_PER_MIN", "20"))
AUTH_FAIL_LIMIT = int(os.getenv("AUTH_FAIL_LIMIT", "5"))
APPROVAL_TTL_MIN = int(os.getenv("APPROVAL_TTL_MIN", "15"))

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")

TZ = ZoneInfo(os.environ["TZ_NAME"]) if os.getenv("TZ_NAME") else None  # None = server local time
# PC control (status, sleep/shutdown, files) is optional: on when the server runs on the user's
# Windows PC, off on a VPS. Force with PC_CONTROL=1/0.
PC_CONTROL = os.getenv("PC_CONTROL", "1" if os.name == "nt" else "0") == "1"
# The one folder shared with the phone: listing/download/delete only inside it.
SHARE_DIR = Path(os.getenv("SHARE_DIR") or Path.home() / "Downloads")

DB = os.path.join(HERE, "data", "app.db")
VAPID_PEM = os.path.join(HERE, "data", "vapid_private.pem")


def now_iso(offset_sec=0):
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_sec)).isoformat(
        timespec="seconds"
    )


def local(iso_utc):
    """UTC record -> local time for display."""
    return datetime.fromisoformat(iso_utc).astimezone(TZ).strftime("%d.%m %H:%M")


def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute(
        "create table if not exists log("
        "ts text, endpoint text, request text, result text, tokens int)"
    )
    con.execute(
        "create table if not exists approvals("
        "id integer primary key, ts text, action text, params text, "
        "status text, expires text, result text)"
    )
    con.execute("create table if not exists subs(endpoint text primary key, data text, ts text)")
    con.execute(
        "create table if not exists agent_tasks("
        "id integer primary key, run_id text, session_id text, prompt text, status text, "
        "output text, pending text, created text, updated text)"
    )
    return con


def log(con, endpoint, request, result, tokens=0):
    con.execute(
        "insert into log values (?, ?, ?, ?, ?)",
        (now_iso(), endpoint, str(request)[:1000], str(result)[:1000], tokens),
    )
    con.commit()


def count_since(con, seconds, auth_fail):
    op = "=" if auth_fail else "!="
    return con.execute(
        f"select count(*) from log where endpoint {op} 'auth-fail' and ts > ?",
        (now_iso(-seconds),),
    ).fetchone()[0]


def save_sub(con, sub):
    """Stores a push subscription. The same device is never added twice."""
    if not sub.get("endpoint") or not sub.get("keys"):
        raise ValueError("invalid subscription")
    con.execute(
        "insert or replace into subs values (?, ?, ?)",
        (sub["endpoint"], json.dumps(sub), now_iso()),
    )
    con.commit()
    return con.execute("select count(*) from subs").fetchone()[0]


def send_push(title, body, url="/"):
    """Notifies every registered device, drops dead subscriptions, returns how many were sent.

    Opens its own connection so it can be called from another thread (sqlite connections
    can't cross threads).
    """
    payload = json.dumps({"title": title, "body": body, "url": url})
    sent = 0
    with closing(db()) as con:
        for endpoint, data in con.execute("select endpoint, data from subs").fetchall():
            try:
                webpush(
                    subscription_info=json.loads(data),
                    data=payload,
                    vapid_private_key=VAPID_PEM,
                    vapid_claims={"sub": VAPID_SUBJECT},
                    ttl=600,
                )
                sent += 1
            except WebPushException as e:
                code = getattr(e.response, "status_code", None)
                # 404/410: subscription is gone (app removed, permission revoked). Clean up.
                if code in (404, 410):
                    con.execute("delete from subs where endpoint = ?", (endpoint,))
                    con.commit()
                log(con, "push", endpoint[:60], f"error {code}: {e}")
        log(con, "push", title, f"sent to {sent} devices")
    return sent
