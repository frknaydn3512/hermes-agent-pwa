"""Bridge to Hermes Agent: chat, tasks, cron jobs -> push, model settings.

Hermes runs on the same machine (`hermes gateway`, 127.0.0.1:8642, API_SERVER_KEY): directly on
Linux/VPS, inside WSL on Windows. Tasks are async: start, the ticker watches, push when done.
"""

import json
import os
import re
import shlex
import subprocess
from contextlib import closing
from pathlib import Path

import httpx

from core import db, local, log, now_iso, send_push

HERMES_URL = os.getenv("HERMES_URL", "http://127.0.0.1:8642")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "")
# Repo the Dev tab shows changes for (where you let Hermes write code).
REPO_DIR = Path(os.getenv("REPO_DIR") or Path.home() / "hermes-workspace")
DONE = ("completed", "failed", "cancelled", "stopped", "error", "expired")

# Hermes' shell: bash on Linux, bash inside WSL on Windows.
SHELL = (
    ["wsl", "-d", os.getenv("WSL_DISTRO", "Ubuntu"), "--", "bash", "-l"] if os.name == "nt"
    else ["bash", "-l"]
)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_gateway = None  # gateway process we started


def sh(script, timeout=60, check=True):
    """Runs a script in Hermes' shell, returns stdout. The script goes via stdin (no secrets or
    quoting issues on the command line), as bytes: text=True turns \n into \r\n on Windows."""
    r = subprocess.run(
        SHELL + ["-s"], input=script.encode(), capture_output=True, timeout=timeout,
        creationflags=NO_WINDOW,
    )
    out = r.stdout.decode("utf-8", "replace")
    if check and r.returncode:
        raise ValueError(f"hermes: {(r.stderr.decode('utf-8', 'replace') or out).strip()[-300:]}")
    return out


def enabled():
    return bool(HERMES_API_KEY)


def _api(method, path, **kw):
    if not HERMES_API_KEY:
        raise ValueError("HERMES_API_KEY missing in .env")
    try:
        r = httpx.request(
            method, f"{HERMES_URL}{path}",
            headers={"Authorization": f"Bearer {HERMES_API_KEY}"}, timeout=30, **kw,
        )
    except httpx.ConnectError:
        raise ValueError("Hermes is down (gateway not running)")
    if r.status_code >= 400:
        raise ValueError(f"hermes {r.status_code}: {r.text[:300]}")
    return r.json()


def healthy():
    try:
        return httpx.get(f"{HERMES_URL}/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def ensure_gateway():
    """Starts the gateway if it is down. Called at startup and after a model change."""
    global _gateway
    if not enabled() or healthy():
        return
    if _gateway and _gateway.poll() is None:
        return
    _gateway = subprocess.Popen(
        SHELL + ["-c", "mkdir -p ~/.hermes/logs; exec hermes gateway >> ~/.hermes/logs/gateway.out 2>&1"],
        creationflags=NO_WINDOW,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


# --- Tasks ---


def start_task(prompt, session_id=None):
    """Gives Hermes a task, records it, returns immediately."""
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("empty task")
    body = {"input": prompt}
    if session_id:
        body["session_id"] = session_id
    run = _api("POST", "/v1/runs", json=body)
    # In a new session Hermes uses the run_id as session id; later tasks continue with it.
    session_id = session_id or run.get("session_id") or run["run_id"]
    with closing(db()) as con:
        cur = con.execute(
            "insert into agent_tasks (run_id, session_id, prompt, status, output, created, updated)"
            " values (?, ?, ?, 'running', '', ?, ?)",
            (run["run_id"], session_id, prompt, now_iso(), now_iso()),
        )
        con.commit()
        log(con, "hermes", prompt, f"run {run['run_id']}")
    return {"id": cur.lastrowid, "run_id": run["run_id"], "session_id": session_id, "status": "running"}


def tasks(limit=20, session_id=None):
    with closing(db()) as con:
        q = "select id, run_id, session_id, prompt, status, output, pending, created from agent_tasks"
        args = ()
        if session_id:
            q, args = q + " where session_id = ?", (session_id,)
        rows = con.execute(q + " order by id desc limit ?", args + (limit,)).fetchall()
    return [
        {"id": i, "run_id": r, "session_id": s, "prompt": p, "status": st, "output": o,
         "pending": json.loads(pe) if pe else None, "created": local(c)}
        for i, r, s, p, st, o, pe, c in rows
    ]


def _output(run):
    out = run.get("output")
    if isinstance(out, list):  # Responses-style output: collect text parts
        parts = []
        for item in out:
            for c in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(c, dict) and c.get("text"):
                    parts.append(c["text"])
        out = "\n".join(parts)
    return str(out or run.get("error") or "")


def poll_tasks():
    """From the ticker: poll running tasks, push on change. Opens its own connection."""
    with closing(db()) as con:
        rows = con.execute(
            "select id, run_id, status, pending from agent_tasks where status in ('running', 'waiting')"
        ).fetchall()
    for tid, run_id, status, pending in rows:
        run = _api("GET", f"/v1/runs/{run_id}")
        new = run.get("status", "running")
        controls = run.get("pending_controls") or None
        with closing(db()) as con:
            if new in DONE:
                out = _output(run)
                con.execute(
                    "update agent_tasks set status = ?, output = ?, pending = null, updated = ? where id = ?",
                    (new, out[:20000], now_iso(), tid),
                )
                con.commit()
                first = out.strip().split("\n")[0][:200] if out.strip() else new
                send_push("Hermes done" if new == "completed" else f"Hermes: {new}", first, "/#dev")
            elif controls:
                con.execute(
                    "update agent_tasks set status = 'waiting', pending = ?, updated = ? where id = ?",
                    (json.dumps(controls), now_iso(), tid),
                )
                con.commit()
                if status != "waiting":  # one push per approval
                    send_push("Hermes needs approval", describe(controls)[:200], "/#dev")
            elif status == "waiting":
                con.execute(
                    "update agent_tasks set status = 'running', pending = null, updated = ? where id = ?",
                    (now_iso(), tid),
                )
                con.commit()


# --- Hermes cron -> telefon push ---

_job_runs = None  # job id -> last seen last_run_at; None = first poll not done yet


def _job_output(job_id):
    """Answer part of the job's latest output file (after the last '## ' heading)."""
    if not re.fullmatch(r"[0-9a-f]+", job_id or ""):
        return ""
    out = sh(
        f'f=$(ls -t ~/.hermes/cron/output/{job_id}/*.md 2>/dev/null | head -1); [ -n "$f" ] && cat "$f"',
        check=False,
    )
    return out.rsplit("\n## ", 1)[-1].split("\n", 1)[-1].strip()


def poll_jobs():
    """From the ticker: turns finished Hermes cron runs into pushes.

    This app is not a Hermes delivery target; jobs use deliver=local and the bridge is here.
    Model-free reminder (phone-reminder skill): the text is the job name.
    ponytail: seen runs live in memory; runs that finish while the server is down are not pushed.
    """
    global _job_runs
    jobs = _api("GET", "/api/jobs?include_disabled=true").get("jobs", [])
    first = _job_runs is None
    seen, _job_runs = _job_runs or {}, {j["id"]: j.get("last_run_at") for j in jobs}
    if first:
        return
    for j in jobs:
        ran = j.get("last_run_at")
        if not ran or seen.get(j["id"]) == ran:
            continue
        name = j.get("name") or "Hermes"
        if j.get("last_status") == "error":
            send_push(f"Hermes job failed: {name}", (j.get("last_error") or "")[:200], "/")
        elif j.get("no_agent"):
            send_push("Reminder", name, "/")
        else:
            send_push(name, (_job_output(j["id"]) or "done")[:300], "/")


def describe(controls):
    """Human readable text from pending_controls."""
    c = controls[0] if isinstance(controls, list) and controls else controls
    if not isinstance(c, dict):
        return str(c)
    return str(c.get("description") or c.get("command") or c.get("prompt") or json.dumps(c)[:200])


def answer(task_id, choice):
    """Answers Hermes' pending approval. choice: one of the options Hermes offered."""
    with closing(db()) as con:
        row = con.execute(
            "select run_id, pending from agent_tasks where id = ? and status = 'waiting'", (task_id,)
        ).fetchone()
    if not row or not row[1]:
        raise ValueError("no pending approval")
    run_id, pending = row
    controls = json.loads(pending)
    c = controls[0] if isinstance(controls, list) else controls
    body = {
        "request_id": c.get("request_id"),
        "execution_generation": c.get("execution_generation"),
        "choice": choice,
    }
    res = _api("POST", f"/v1/runs/{run_id}/approval", json=body)
    with closing(db()) as con:
        con.execute(
            "update agent_tasks set status = 'running', pending = null, updated = ? where id = ?",
            (now_iso(), task_id),
        )
        con.commit()
        log(con, "hermes", f"approval #{task_id} {choice}", json.dumps(res)[:300])
    return res


def stop(task_id):
    with closing(db()) as con:
        row = con.execute("select run_id from agent_tasks where id = ?", (task_id,)).fetchone()
    if not row:
        raise ValueError("no such task")
    _api("POST", f"/v1/runs/{row[0]}/stop")
    with closing(db()) as con:
        con.execute(
            "update agent_tasks set status = 'stopped', updated = ? where id = ?", (now_iso(), task_id)
        )
        con.commit()
    return "Stopped"


def repo_diff():
    """Uncommitted changes Hermes made in REPO_DIR."""
    r = subprocess.run(
        ["git", "-C", str(REPO_DIR), "diff", "--stat", "--patch"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    s = subprocess.run(
        ["git", "-C", str(REPO_DIR), "status", "--short"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    status = "\n".join(line.strip() for line in s.stdout.splitlines() if line.strip())
    return {"status": status, "diff": r.stdout[-20000:]}


# --- Chat (Hermes Sessions API) ---


async def new_session():
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{HERMES_URL}/api/sessions", json={"source": "api_server"},
            headers={"Authorization": f"Bearer {HERMES_API_KEY}"},
        )
    if r.status_code >= 400:
        raise ValueError(f"hermes {r.status_code}: {r.text[:300]}")
    data = r.json()
    return data.get("id") or data.get("session_id") or data["session"]["id"]


async def chat_stream(session_id, message):
    """Sends a message to a Hermes session, yields the reply piece by piece.

    SSE events: assistant.delta (piece), assistant.completed (full text; the only piece when
    streaming is off), run.failed/run.cancelled (error). Tool steps show as short lines.
    """
    sent = False
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, read=600)) as client:
        async with client.stream(
            "POST", f"{HERMES_URL}/api/sessions/{session_id}/chat/stream",
            json={"message": message}, headers={"Authorization": f"Bearer {HERMES_API_KEY}"},
        ) as r:
            if r.status_code >= 400:
                yield f"[error] hermes {r.status_code}: {(await r.aread()).decode(errors='replace')[:300]}"
                return
            event = ""
            async for line in r.aiter_lines():
                if line.startswith("event:"):
                    event = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:])
                except ValueError:
                    continue
                if event == "assistant.delta" and data.get("delta"):
                    sent = True
                    yield data["delta"]
                elif event == "tool.started" and data.get("tool_name"):
                    yield f"\n⚙ {data['tool_name']}\n"
                elif event == "assistant.completed" and not sent and data.get("content"):
                    yield data["content"]
                elif event in ("run.failed", "run.cancelled"):
                    yield f"\n[error] {data.get('error') or event}"


# --- Model settings (from the phone) ---

# A selection of Hermes' providers: id -> (label, env name of its key).
# "custom": any OpenAI-compatible endpoint (Groq, Cerebras, Ollama, vLLM...).
PROVIDERS = {
    "openrouter": ("OpenRouter", "OPENROUTER_API_KEY"),
    "gemini": ("Google AI Studio (Gemini)", "GEMINI_API_KEY"),
    "anthropic": ("Anthropic (Claude)", "ANTHROPIC_API_KEY"),
    "openai-api": ("OpenAI", "OPENAI_API_KEY"),
    "deepseek": ("DeepSeek", "DEEPSEEK_API_KEY"),
    "xai": ("xAI (Grok)", "XAI_API_KEY"),
    "nvidia": ("NVIDIA NIM", "NVIDIA_API_KEY"),
    "huggingface": ("Hugging Face", "HF_TOKEN"),
    "zai": ("Z.AI (GLM)", "GLM_API_KEY"),
    "ollama-cloud": ("Ollama Cloud", "OLLAMA_API_KEY"),
    "custom": ("OpenAI-compatible endpoint", "CUSTOM_API_KEY"),
}
PROFILES = ("", "-p coder")  # both use the same model; coder is optional


def get_model():
    out = sh(
        "hermes config get model.provider; hermes config get model.default; "
        "hermes config get model.base_url; "
        "grep -oE '^[A-Z_]+=.' ~/.hermes/.env | cut -d= -f1 | tr '\\n' ' '; echo"
    ).split("\n")
    provider, model, base_url, keys = (out + ["", "", "", ""])[:4]
    keys = set(keys.split())
    return {
        "provider": provider.strip(), "model": model.strip(), "base_url": base_url.strip(),
        "providers": [{"id": k, "label": v[0], "key_set": v[1] in keys} for k, v in PROVIDERS.items()],
    }


def set_model(provider, model, api_key="", base_url=""):
    """Switches Hermes' profiles to the new model. A given key is written to ~/.hermes/.env
    (never read back) and the gateway restarts so it picks the key up."""
    if provider not in PROVIDERS:
        raise ValueError("unknown provider")
    model, api_key, base_url = model.strip(), api_key.strip(), base_url.strip()
    if not re.fullmatch(r"[A-Za-z0-9._:/@+-]{1,120}", model):
        raise ValueError("invalid model name")
    if api_key and not re.fullmatch(r"[\x21-\x7e]{8,400}", api_key):
        raise ValueError("invalid API key")
    if provider == "custom":
        if not re.fullmatch(r"https?://[A-Za-z0-9._:/-]{3,200}", base_url):
            raise ValueError("custom needs a valid URL (https://.../v1)")
    else:
        base_url = ""
    env = PROVIDERS[provider][1]
    lines = ["set -e"]
    if api_key:
        lines.append(f"KEY={shlex.quote(api_key)}")
        for d in ("~/.hermes", "~/.hermes/profiles/coder"):
            lines.append(
                f'if [ -d {d} ]; then f={d}/.env; touch $f; grep -v "^{env}=" $f > $f.tmp || true; '
                f'printf "%s=%s\\n" {env} "$KEY" >> $f.tmp; mv $f.tmp $f; chmod 600 $f; fi'
            )
    key_ref = shlex.quote("${CUSTOM_API_KEY}") if provider == "custom" else "''"
    for p in PROFILES:
        block = "; ".join(
            f"hermes {p} config set {k} {v} >/dev/null"
            for k, v in (
                ("model.provider", provider), ("model.default", shlex.quote(model)),
                ("model.base_url", shlex.quote(base_url)), ("model.api_key", key_ref),
            )
        )
        lines.append(f"if [ -d ~/.hermes/profiles/coder ]; then {block}; fi" if p else block)
    if api_key:
        lines.append("pkill -f 'hermes gateway' || true")
    sh("\n".join(lines) + "\n", timeout=120)
    if api_key:
        restart_gateway()
    return get_model()


def restart_gateway():
    """Restarts the gateway and waits for it (up to ~30 s)."""
    import time

    global _gateway
    _gateway = None
    time.sleep(2)  # after pkill the old process may still answer /health
    for _ in range(30):
        if healthy():
            return True
        if _gateway is None or _gateway.poll() is not None:
            ensure_gateway()
        time.sleep(1)
    return healthy()
