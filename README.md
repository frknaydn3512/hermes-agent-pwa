# hermes-agent-pwa

A phone control center for [Hermes Agent](https://hermes-agent.nousresearch.com).
Hermes is the brain; this is the remote control in your pocket.

- **Chat** with Hermes from your phone, streaming, with session memory.
- **Push notifications** when Hermes cron jobs finish: reminders, news digests, checks.
  Plain reminders ("remind me to X in 10 minutes") run with **zero model calls**.
- **Bring any model**: pick a provider (Gemini, OpenRouter, Anthropic, OpenAI, DeepSeek, any
  OpenAI-compatible URL...) and paste the API key from the phone. Free tiers work.
- **Dev tab**: give Hermes coding tasks, approve its risky commands from the phone, see the diff.
- **Optional PC control** (Windows): status, sleep / shut down with approval, download files.
- English and Turkish UI. Installable PWA (iOS and Android), no app store.

```
phone (PWA) --Tailscale HTTPS--> this server (FastAPI, :8000) --> Hermes gateway (:8642)
```

Nothing is exposed to the internet: the phone reaches the server over your private
[Tailscale](https://tailscale.com) network.

## Install on a Linux server / VPS (recommended)

Needs: Hermes Agent installed and set up (`hermes` works in your shell), Python 3.10+, Tailscale.

```bash
git clone https://github.com/frknaydn3512/hermes-agent-pwa.git
cd hermes-agent-pwa
./scripts/install.sh
```

The script:

1. creates `.venv` and installs `requirements.txt`,
2. runs `scripts/setup.py`: creates `.env` (login token, push keys), turns on Hermes' local API
   server (`API_SERVER_*` in `~/.hermes/.env`), installs the phone-reminder skill into Hermes,
3. installs a systemd service `hermes-agent-pwa` (skip with `--no-service`),
4. prints the login token once (it is also in `.env` as `APP_TOKEN`).

Then put it on your tailnet and open it on the phone:

```bash
tailscale serve --bg 8000
```

Open `https://<server>.<tailnet>.ts.net` on the phone (Tailscale app on), enter the token,
**Share > Add to Home Screen**. Open it from the home screen, go to **Settings > Model**, pick a
provider, paste a key. Then **Enable notifications**.

Re-running `install.sh` / `setup.py` is safe: existing values are never overwritten.

## Install on Windows (Hermes in WSL)

Hermes runs in WSL (Ubuntu); this server runs on Windows and talks to it through `wsl`.
PC control is on by default here.

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python scripts\setup.py
.\.venv\Scripts\python server\main.py
& "C:\Program Files\Tailscale\tailscale.exe" serve --bg 8000
```

`scripts/start-windows.vbs` starts the server without a console window; put a shortcut to it in
`shell:startup` to start with Windows. The server starts `hermes gateway` itself if it is down.

## Settings (`.env`)

| Name | Default | |
|---|---|---|
| `APP_TOKEN` | created by setup | Login token. Rotate with `python server/main.py kill` |
| `HERMES_API_KEY` | created by setup | Same as `API_SERVER_KEY` in `~/.hermes/.env` |
| `HERMES_URL` | `http://127.0.0.1:8642` | Hermes gateway |
| `PC_CONTROL` | `1` on Windows, `0` elsewhere | PC status, sleep/shutdown, files |
| `SHARE_DIR` | `~/Downloads` | The only folder the phone can list/download/delete |
| `REPO_DIR` | `~/hermes-workspace` | Repo the Dev tab shows changes for |
| `WSL_DISTRO` | `Ubuntu` | Windows only |
| `PORT` | `8000` | |
| `TZ_NAME` | server time | e.g. `Europe/Istanbul`, for displayed times |
| `RATE_PER_MIN`, `AUTH_FAIL_LIMIT`, `APPROVAL_TTL_MIN` | `20`, `5`, `15` | Limits |

## How it works

- **Chat** uses Hermes' Sessions API (`/api/sessions/{id}/chat/stream`). Tools Hermes uses show
  as `⚙ tool` lines.
- **Reminders and jobs**: Hermes creates cron jobs with `deliver: local`. The server polls
  `/api/jobs` every 30 s and pushes each new run to the phone. `hermes/` holds the
  `phone-reminder` skill and a `SOUL.md` note that teach Hermes to make plain reminders as
  `no_agent` jobs (no model call when they fire).
- **Model**: `hermes config set model.*` on the default profile (and `coder` if it exists). The
  key goes to `~/.hermes/.env` with mode 600, is never sent back to the phone or logged, and
  the gateway restarts to pick it up.
- **Dev tab**: tasks go to Hermes' runs API. When Hermes asks to approve a command, you get a
  push and answer from the phone. For coding, a separate Hermes profile with a sandboxed
  terminal (e.g. Docker backend) pointed at `REPO_DIR` is a good idea.
- **PC actions** (sleep, shutdown, delete file) are an allow list in `server/commands.py`
  and always go through an approval that expires in 15 minutes.

## Security

- Keep it on Tailscale. Don't expose port 8000 or 8642 to the internet.
- One login token (`APP_TOKEN`), compared in constant time; failed logins lock the API for
  5 minutes; requests are rate limited.
- **Kill switch**: `python server/main.py kill` rotates the token, stops the server and turns
  off `tailscale serve`. Undo: new token is in `.env`, start the server, `tailscale serve --bg 8000`.
- Hermes can run commands on its machine. Give it a sandboxed terminal backend if you let it
  write code, and review what you approve.
- Back up `.env` and `data/` (database, push key). Both are git-ignored.

## Development

```bash
python tests/test_main.py   # no network, uses a throwaway database
```

Layout: `server/` (FastAPI: `main.py` routes, `hermes.py` Hermes bridge, `commands.py` PC
actions, `core.py` settings/db/push), `pwa/` (plain HTML/CSS/JS, no build step), `hermes/`
(files installed into Hermes), `scripts/` (install, setup, Windows launcher), `tests/`.

## License

MIT
