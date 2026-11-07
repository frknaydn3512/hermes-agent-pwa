"""One-time setup, safe to re-run: .env, push keys, Hermes API server, Hermes add-ons.

    python scripts/setup.py

Never overwrites a value that is already set. Works on Linux (VPS) and on Windows (Hermes in WSL).
"""

import base64
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
PEM = ROOT / "data" / "vapid_private.pem"


def read_env(path):
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines() if "=" in line)
    return {k.strip(): v.strip() for k, v in pairs}


def add_env(path, values):
    """Appends only the keys that are missing or empty."""
    have = read_env(path)
    new = {k: v for k, v in values.items() if not have.get(k)}
    if new:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        # drop empty "KEY=" lines we are about to fill
        lines = [ln for ln in text.splitlines() if ln.split("=", 1)[0].strip() not in new]
        lines += [f"{k}={v}" for k, v in new.items()]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return new


def vapid_public_key():
    """Creates the push signing key once; returns its public half (base64url)."""
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid01
    from py_vapid.utils import b64urlencode

    PEM.parent.mkdir(exist_ok=True)
    if PEM.exists():
        v = Vapid01.from_file(str(PEM))
    else:
        v = Vapid01()
        v.generate_keys()
        v.save_key(str(PEM))
    raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return b64urlencode(raw)


def hermes_api_key():
    """Turns on Hermes' local API server (if needed) and returns its key."""
    sys.path.insert(0, str(ROOT / "server"))
    import hermes

    out = hermes.sh("grep -E '^API_SERVER_KEY=.' ~/.hermes/.env 2>/dev/null | tail -1 | cut -d= -f2-", check=False)
    key = out.strip()
    if key:
        return key
    key = secrets.token_urlsafe(32)
    hermes.sh(
        "mkdir -p ~/.hermes && touch ~/.hermes/.env && chmod 600 ~/.hermes/.env\n"
        "sed -i '/^API_SERVER_\\(ENABLED\\|KEY\\|HOST\\|PORT\\)=/d' ~/.hermes/.env\n"
        f"printf '%s\\n' API_SERVER_ENABLED=true API_SERVER_KEY={key} API_SERVER_HOST=127.0.0.1 "
        "API_SERVER_PORT=8642 >> ~/.hermes/.env\n"
    )
    print("Hermes API server enabled on 127.0.0.1:8642")
    return key


def install_hermes_addons():
    """Phone reminder skill + script + SOUL.md note (see hermes/)."""
    sys.path.insert(0, str(ROOT / "server"))
    import hermes

    src = ROOT / "hermes"

    def b64(p):
        return base64.b64encode(p.read_bytes()).decode()

    hermes.sh(
        "set -e\n"
        "mkdir -p ~/.hermes/scripts ~/.hermes/skills/productivity/phone-reminder\n"
        f"echo {b64(src / 'scripts' / 'phone_reminder.sh')} | base64 -d > ~/.hermes/scripts/phone_reminder.sh\n"
        "chmod +x ~/.hermes/scripts/phone_reminder.sh\n"
        f"echo {b64(src / 'skills' / 'phone-reminder' / 'SKILL.md')} | base64 -d"
        " > ~/.hermes/skills/productivity/phone-reminder/SKILL.md\n"
        "touch ~/.hermes/SOUL.md\n"
        f"grep -q '## Phone app' ~/.hermes/SOUL.md || echo {b64(src / 'SOUL-addon.md')} | base64 -d >> ~/.hermes/SOUL.md\n"
    )
    print("Hermes add-ons installed (phone-reminder skill, SOUL.md note)")


def main():
    added = add_env(ENV, {
        "APP_TOKEN": secrets.token_urlsafe(32),
        "VAPID_PUBLIC_KEY": vapid_public_key(),
        "VAPID_SUBJECT": "mailto:admin@example.com",
        "HERMES_API_KEY": hermes_api_key(),
    })
    os.chmod(ENV, 0o600)
    install_hermes_addons()
    print(f".env: {', '.join(added) or 'nothing new'}")
    if "APP_TOKEN" in added:
        print(f"\nLogin token for the phone app (also in .env as APP_TOKEN):\n\n  {read_env(ENV)['APP_TOKEN']}\n")


if __name__ == "__main__":
    main()
