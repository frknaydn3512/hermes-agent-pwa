"""hermes-agent-pwa backend: PWA, auth, approval queue, push, Hermes bridge.

Hermes Agent is the brain (chat, cron, skills). This server is the remote control between the
phone and Hermes, optional PC control (commands.py) and pushes for finished cron jobs.

Run:         python server/main.py          (server, 127.0.0.1:8000)
Kill switch: python server/main.py kill
Tests:       python tests/test_main.py
"""

import asyncio
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
from contextlib import asynccontextmanager, closing

import httpx
import psutil
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import hermes
from commands import cancel_shutdown, create_approval, decide_approval, files, pc_status, safe_path
from core import APP_TOKEN, AUTH_FAIL_LIMIT, HERE, PC_CONTROL, RATE_PER_MIN, VAPID_PUBLIC_KEY, count_since, db, log, now_iso, save_sub, send_push

# --- Ticker ---


async def ticker():
    """Every 30 s: poll Hermes tasks and jobs, push what finished."""
    while True:
        try:
            if hermes.enabled():
                await asyncio.to_thread(hermes.poll_tasks)
                await asyncio.to_thread(hermes.poll_jobs)
        except Exception as e:
            with closing(db()) as con:
                log(con, "ticker", "hermes error", str(e))
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(_app):
    await asyncio.to_thread(hermes.ensure_gateway)
    task = asyncio.create_task(ticker())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def no_stale_cache(request, call_next):
    # Without a header iOS caches files as it likes (new index.html + old app.js = broken UI).
    # no-cache = revalidate with ETag every time (304 is cheap).
    resp = await call_next(request)
    resp.headers.setdefault("Cache-Control", "no-cache")
    return resp


# --- Auth and rate limit ---


def check_token(header):
    # ponytail: one token, plain text in .env. Multiple tokens / revocation: hashed table in the DB.
    token = (header or "").removeprefix("Bearer ").strip()
    if not APP_TOKEN or not hmac.compare_digest(token, APP_TOKEN):
        raise HTTPException(401, "invalid token")


def guard(authorization: str = Header(None)):
    """Runs in front of every protected endpoint."""
    with closing(db()) as con:
        # ponytail: the failed-login lock blocks everyone (single user, acceptable).
        # Multi-user: key it by IP/token.
        if count_since(con, 300, auth_fail=True) >= AUTH_FAIL_LIMIT:
            raise HTTPException(429, "too many failed logins, wait 5 minutes")
        try:
            check_token(authorization)
        except HTTPException:
            log(con, "auth-fail", (authorization or "")[:40], "401")
            raise
        if count_since(con, 60, auth_fail=False) >= RATE_PER_MIN:
            raise HTTPException(429, f"limit of {RATE_PER_MIN} requests per minute reached")



# --- API ---



def pc_on():
    if not PC_CONTROL:
        raise HTTPException(404, "PC control is off (PC_CONTROL=0)")


class ApprovalIn(BaseModel):
    action: str
    params: dict = {}



class HermesChatIn(BaseModel):
    message: str
    session_id: str | None = None


@app.post("/chat/stream", dependencies=[Depends(guard)])
async def chat_stream(body: HermesChatIn):
    """Chat goes to Hermes with whatever model it has. Session id comes back in X-Session-Id."""
    try:
        sid = body.session_id or await hermes.new_session()
    except (ValueError, httpx.HTTPError) as e:
        raise HTTPException(502, f"Hermes unreachable: {e}")

    async def gen():
        parts = []
        async for piece in hermes.chat_stream(sid, body.message):
            parts.append(piece)
            yield piece
        with closing(db()) as con:
            log(con, "/chat/stream", body.message, "".join(parts))

    return StreamingResponse(
        gen(), media_type="text/plain; charset=utf-8", headers={"X-Session-Id": sid}
    )


@app.post("/approvals", dependencies=[Depends(guard)])
def new_approval(body: ApprovalIn):
    with closing(db()) as con:
        return create_approval(con, body.action, body.params)


@app.get("/approvals", dependencies=[Depends(guard)])
def list_approvals():
    with closing(db()) as con:
        con.execute(
            "update approvals set status = 'expired' where status = 'pending' and expires < ?",
            (now_iso(),),
        )
        con.commit()
        rows = con.execute(
            "select id, ts, action, params, expires from approvals where status = 'pending'"
            " order by id"
        ).fetchall()
    return [
        {"id": i, "ts": ts, "action": a, "params": json.loads(p), "expires": e}
        for i, ts, a, p, e in rows
    ]


@app.post("/approvals/{aid}/approve", dependencies=[Depends(guard)])
def approve_approval(aid: int):
    with closing(db()) as con:
        return decide_approval(con, aid, approve=True)


@app.post("/approvals/{aid}/reject", dependencies=[Depends(guard)])
def reject_approval(aid: int):
    with closing(db()) as con:
        return decide_approval(con, aid, approve=False)


@app.get("/pc/status", dependencies=[Depends(guard), Depends(pc_on)])
def pc_status_api():
    return {"text": pc_status()}


@app.post("/pc/cancel-shutdown", dependencies=[Depends(guard), Depends(pc_on)])
def cancel_shutdown_api():
    return {"text": cancel_shutdown()}


@app.get("/dev/status", dependencies=[Depends(guard)])
def dev_status_api():
    """Dev tab: is Hermes up, what changed in REPO_DIR."""
    return {
        "repo": hermes.REPO_DIR.name,
        "hermes": {"enabled": hermes.enabled(), "up": hermes.healthy()},
        "changes": hermes.repo_diff()["status"],
    }


class TaskIn(BaseModel):
    prompt: str
    session_id: str | None = None


class AnswerIn(BaseModel):
    choice: str


def _value_error(fn, *a):
    try:
        return fn(*a)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/agent/tasks", dependencies=[Depends(guard)])
def agent_start(body: TaskIn):
    # The user's own task: no extra approval. Hermes' dangerous commands still go through
    # Hermes' own approval (pending_controls -> phone).
    return _value_error(hermes.start_task, body.prompt, body.session_id)


@app.get("/agent/tasks", dependencies=[Depends(guard)])
def agent_tasks(session_id: str | None = None):
    return hermes.tasks(session_id=session_id)


@app.post("/agent/tasks/{tid}/answer", dependencies=[Depends(guard)])
def agent_answer(tid: int, body: AnswerIn):
    return _value_error(hermes.answer, tid, body.choice)


@app.post("/agent/tasks/{tid}/stop", dependencies=[Depends(guard)])
def agent_stop(tid: int):
    return {"text": _value_error(hermes.stop, tid)}


@app.get("/agent/diff", dependencies=[Depends(guard)])
def agent_diff():
    return hermes.repo_diff()


class ModelIn(BaseModel):
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""


@app.get("/hermes/model", dependencies=[Depends(guard)])
def hermes_model():
    return _value_error(hermes.get_model)


@app.post("/hermes/model", dependencies=[Depends(guard)])
def hermes_set_model(body: ModelIn):
    """Changes Hermes' model. The key never goes to the log or the response."""
    res = _value_error(hermes.set_model, body.provider, body.model, body.api_key, body.base_url)
    with closing(db()) as con:
        log(con, "/hermes/model", f"{body.provider} {body.model}", "key changed" if body.api_key else "")
    return res


@app.get("/files", dependencies=[Depends(guard), Depends(pc_on)])
def files_api():
    return files()


@app.get("/files/{name}", dependencies=[Depends(guard), Depends(pc_on)])
def file_download(name: str):
    try:
        p = safe_path(name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not p.is_file():
        raise HTTPException(404, "no such file")
    return FileResponse(p, filename=p.name)


@app.get("/push/key", dependencies=[Depends(guard)])
def push_key():
    return {"key": VAPID_PUBLIC_KEY}


@app.post("/push/subscribe", dependencies=[Depends(guard)])
def push_subscribe(sub: dict):
    with closing(db()) as con:
        try:
            return {"ok": True, "devices": save_sub(con, sub)}
        except ValueError as e:
            raise HTTPException(400, str(e))


@app.post("/push/test", dependencies=[Depends(guard)])
def push_test():
    sent = send_push("Hermes", "Test notification works.")
    if not sent:
        raise HTTPException(404, "no registered device (or all are dead)")
    return {"sent": sent}


@app.get("/health")
def health():
    return {"ok": True, "hermes": hermes.healthy(), "pc": PC_CONTROL}


# PWA. Must be last: the "/" mount doesn't shadow routes defined before it.
app.mount("/", StaticFiles(directory=os.path.join(HERE, "pwa"), html=True), name="pwa")


TAILSCALE = r"C:\Program Files\Tailscale\tailscale.exe" if os.name == "nt" else "tailscale"


def rotate_token(env_path):
    """Replaces APP_TOKEN in .env. The old token stops working right away."""
    with open(env_path, encoding="utf-8") as f:
        text = f.read()
    text, n = re.subn(r"(?m)^APP_TOKEN=.*$", f"APP_TOKEN={secrets.token_urlsafe(32)}", text)
    if n != 1:
        raise SystemExit(f"expected one APP_TOKEN line in {env_path}, found {n}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(text)


def kill_switch():
    """Emergency: new token, server stopped, Tailscale serve off. Undo steps in the README."""
    rotate_token(os.path.join(HERE, ".env"))
    print("token rotated (.env). Log in on the phone with the new token.")
    me = {os.getpid(), os.getppid()}
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        cmd = " ".join(p.info["cmdline"] or [])
        if p.info["pid"] not in me and "python" in (p.info["name"] or "") and "main.py" in cmd:
            p.kill()
            print(f"server stopped: pid {p.info['pid']}")
    r = subprocess.run([TAILSCALE, "serve", "--https=443", "off"], capture_output=True, text=True)
    print("tailscale serve off" if r.returncode == 0 else f"tailscale: {r.stderr.strip()}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "kill":
        kill_switch()
    else:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
