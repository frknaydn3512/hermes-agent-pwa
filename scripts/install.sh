#!/usr/bin/env bash
# Install hermes-agent-pwa on a Linux server (VPS) next to Hermes Agent.
#   ./scripts/install.sh               venv + setup + systemd service (asks for sudo)
#   ./scripts/install.sh --no-service  skip systemd (run: .venv/bin/python server/main.py)
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)

command -v hermes >/dev/null || {
  echo "Hermes Agent not found. Install it first: https://hermes-agent.nousresearch.com"; exit 1; }
python3 -m venv .venv || {
  echo "python3 venv failed. On Debian/Ubuntu: sudo apt install python3-venv"; exit 1; }
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python scripts/setup.py

if [ "${1:-}" != "--no-service" ] && command -v systemctl >/dev/null; then
  sudo tee /etc/systemd/system/hermes-agent-pwa.service >/dev/null <<UNIT
[Unit]
Description=hermes-agent-pwa (phone control center for Hermes Agent)
After=network-online.target

[Service]
User=$USER
WorkingDirectory=$ROOT
ExecStart=$ROOT/.venv/bin/python server/main.py
Restart=always

[Install]
WantedBy=multi-user.target
UNIT
  sudo systemctl daemon-reload
  sudo systemctl enable --now hermes-agent-pwa
  echo "Service running: systemctl status hermes-agent-pwa"
fi

cat <<'NEXT'

Next: reach it from your phone over Tailscale (no public port needed)
  1. Install Tailscale on this server and on your phone, same account.
  2. tailscale serve --bg 8000
  3. Open the https://<this-machine>.<tailnet>.ts.net address on the phone,
     enter the login token, then "Add to Home Screen".
NEXT
