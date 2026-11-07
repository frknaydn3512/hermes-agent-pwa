"""PC commands and the approval queue.

Two kinds:
  direct    pc_status, files, cancel_shutdown  (read-only or harmless)
  approved  ACTIONS: the phone opens an approval record, it runs only once approved

File operations stay inside SHARE_DIR (path is resolved, anything escaping it is rejected).
"""

import json
import os
import subprocess
import threading
import time
from datetime import datetime

import psutil
from fastapi import HTTPException

from core import APPROVAL_TTL_MIN, PC_CONTROL, SHARE_DIR, log, now_iso

SHUTDOWN_DELAY_SEC = 60  # can be undone with cancel_shutdown within this window


def gb(n):
    return f"{n / 2**30:.1f} GB"


# --- Direct (no approval) ---


def pc_status():
    # ponytail: no temperature, psutil can't read it on Windows. LibreHardwareMonitor if needed.
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.splitdrive(str(SHARE_DIR))[0] + os.sep)
    up = int(time.time() - psutil.boot_time())
    lines = [
        f"CPU %{psutil.cpu_percent(interval=0.5):.0f}",
        f"RAM %{vm.percent:.0f} ({gb(vm.used)} / {gb(vm.total)})",
        f"Disk free {gb(disk.free)} / {gb(disk.total)}",
        f"Uptime {up // 86400}d {up % 86400 // 3600}h {up % 3600 // 60}m",
    ]
    bat = psutil.sensors_battery()
    if bat:
        lines.append(f"Battery %{bat.percent:.0f} {'(charging)' if bat.power_plugged else '(on battery)'}")
    return "\n".join(lines)


def files(limit=30):
    """Files in the shared folder, newest first."""
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    items = sorted(
        (p for p in SHARE_DIR.iterdir() if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    return [
        {
            "name": p.name,
            "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m %H:%M"),
        }
        for p in items
    ]


def cancel_shutdown():
    r = subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
    return "Shutdown cancelled" if r.returncode == 0 else "No pending shutdown"


def safe_path(name):
    """Path of a file directly inside SHARE_DIR. '../', absolute paths and subfolders are rejected."""
    base = SHARE_DIR.resolve()
    p = (base / name).resolve()
    if p.parent != base:
        raise ValueError(f"outside the shared folder: {name}")
    return p


# --- Approved actions ---


def delete_file(name):
    p = safe_path(name)
    if not p.is_file():
        raise ValueError(f"no such file: {name}")
    p.unlink()
    return f"Deleted: {name}"


def sleep_pc():
    # 5 s delay so the HTTP reply reaches the phone first.
    # With hibernation enabled, SetSuspendState hibernates instead of sleeping.
    threading.Timer(
        5, subprocess.run, [["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]]
    ).start()
    return "PC goes to sleep in 5 seconds. The server is unreachable while it sleeps."


def shutdown_pc():
    subprocess.run(["shutdown", "/s", "/t", str(SHUTDOWN_DELAY_SEC)], check=True)
    return f"PC shuts down in {SHUTDOWN_DELAY_SEC} s. Cancel from the app."


# Allow list. Signature: fn(params: dict) -> str. "echo" is for tests.
ACTIONS = {
    "echo": lambda p: f"echo: {p.get('text', '')}",
    "delete_file": lambda p: delete_file(p["name"]),
    "sleep_pc": lambda p: sleep_pc(),
    "shutdown_pc": lambda p: shutdown_pc(),
}
if not PC_CONTROL:  # VPS: no PC actions
    ACTIONS = {"echo": ACTIONS["echo"]}


# --- Approval queue ---


def create_approval(con, action, params):
    if action not in ACTIONS:
        raise HTTPException(400, f"unknown action: {action}")
    cur = con.execute(
        "insert into approvals (ts, action, params, status, expires) values (?, ?, ?, 'pending', ?)",
        (now_iso(), action, json.dumps(params), now_iso(APPROVAL_TTL_MIN * 60)),
    )
    con.commit()
    log(con, "/approvals", f"{action} {params}", f"pending #{cur.lastrowid}")
    return {"id": cur.lastrowid, "action": action, "status": "pending"}


def decide_approval(con, aid, approve):
    row = con.execute(
        "select action, params, status, expires from approvals where id = ?", (aid,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "no such approval")
    action, params, status, expires = row
    if status != "pending":
        raise HTTPException(409, f"already handled: {status}")
    if expires < now_iso():
        con.execute("update approvals set status = 'expired' where id = ?", (aid,))
        con.commit()
        raise HTTPException(410, "approval expired, create it again")
    if not approve:
        con.execute("update approvals set status = 'rejected' where id = ?", (aid,))
        con.commit()
        log(con, "/approvals", f"#{aid} {action}", "rejected")
        return {"id": aid, "status": "rejected"}
    if action not in ACTIONS:
        raise HTTPException(400, f"action no longer defined: {action}")

    try:
        result = str(ACTIONS[action](json.loads(params)))
        status = "done"
    except Exception as e:
        result, status = f"error: {e}", "failed"
    con.execute(
        "update approvals set status = ?, result = ? where id = ?", (status, result[:1000], aid)
    )
    con.commit()
    log(con, "/approvals", f"#{aid} {action}", f"{status}: {result}")
    return {"id": aid, "status": status, "result": result}
