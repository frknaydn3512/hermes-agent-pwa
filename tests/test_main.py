"""Tests: python tests/test_main.py

No network, never touches the real database (uses data/selftest.db, deleted at the end).
"""

import asyncio
import os
import sys
from contextlib import closing

from fastapi import HTTPException

from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "server"))

import commands  # noqa: E402
import core
import hermes
import main

core.DB = os.path.join(core.HERE, "data", "selftest.db")


def expect(code, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except HTTPException as e:
        assert e.status_code == code, f"{code} bekleniyordu, {e.status_code} geldi"
        return
    raise AssertionError(f"{code} bekleniyordu, hata gelmedi")


def main_test():
    if os.path.exists(core.DB):
        os.remove(core.DB)

    # --- token ---
    main.APP_TOKEN = ""
    for header in (None, "", "Bearer "):
        expect(401, main.check_token, header)

    main.APP_TOKEN = "t" * 32
    good = f"Bearer {main.APP_TOKEN}"
    expect(401, main.check_token, "Bearer " + "t" * 31)
    main.check_token(good)

    with closing(core.db()) as con:
        # --- approval queue ---
        expect(400, main.create_approval, con, "rm -rf", {})
        a = main.create_approval(con, "echo", {"text": "merhaba"})
        assert a["status"] == "pending"
        assert main.decide_approval(con, a["id"], approve=True)["result"] == "echo: merhaba"
        expect(409, main.decide_approval, con, a["id"], True)
        expect(404, main.decide_approval, con, 9999, True)
        b = main.create_approval(con, "echo", {"text": "x"})
        assert main.decide_approval(con, b["id"], approve=False)["status"] == "rejected"

        c = main.create_approval(con, "echo", {"text": "gec"})
        con.execute(
            "update approvals set expires = ? where id = ?", (core.now_iso(-60), c["id"])
        )
        con.commit()
        expect(410, main.decide_approval, con, c["id"], True)
        durum = con.execute(
            "select status from approvals where id = ?", (c["id"],)
        ).fetchone()[0]
        assert durum == "expired", durum

        # --- push subscription ---
        try:
            core.save_sub(con, {"endpoint": "https://x/1"})
            raise AssertionError("anahtarsiz abonelik kabul edildi")
        except ValueError:
            pass
        sub = {"endpoint": "https://x/1", "keys": {"p256dh": "a", "auth": "b"}}
        assert core.save_sub(con, sub) == 1
        assert core.save_sub(con, sub) == 1, "ayni cihaz iki kez kaydedildi"

        # --- rate counter ignores auth-fail rows ---
        before = core.count_since(con, 60, auth_fail=False)
        core.log(con, "auth-fail", "x", "401")
        assert core.count_since(con, 60, auth_fail=False) == before
        assert core.count_since(con, 60, auth_fail=True) == 1

        con.execute("delete from subs")
        con.commit()

    # --- PC commands: cannot leave the shared folder ---
    share = Path(core.HERE, "data", "selftest_share")
    share.mkdir(exist_ok=True)
    commands.SHARE_DIR = share
    (share / "a.txt").write_text("x")
    for bad in ("../app.db", "..\\app.db", "C:\\Windows\\win.ini", "alt/a.txt", "."):
        try:
            commands.safe_path(bad)
            raise AssertionError(f"klasor disi kabul edildi: {bad}")
        except ValueError:
            pass
    assert [f["name"] for f in commands.files()] == ["a.txt"]
    assert "Deleted" in commands.delete_file("a.txt")
    assert not (share / "a.txt").exists()
    share.rmdir()
    assert "CPU" in commands.pc_status()

    # --- a failing action ends as 'failed' ---
    with closing(core.db()) as con:
        a = main.create_approval(con, "delete_file", {"name": "yok.txt"})
        r = main.decide_approval(con, a["id"], approve=True)
        assert r["status"] == "failed" and "no such file" in r["result"], r

    # --- Hermes bridge: task -> waiting for approval (one push) -> answer -> done ---
    calls, pushes, state = [], [], {"run": {"status": "running"}}

    def fake_api(method, path, **kw):
        calls.append((method, path, kw.get("json")))
        if method == "POST" and path == "/v1/runs":
            return {"run_id": "run_x", "status": "started"}
        if method == "GET":
            return state["run"]
        return {"ok": True}

    real_api, real_push = hermes._api, hermes.send_push
    hermes._api, hermes.send_push = fake_api, lambda *a: pushes.append(a)
    t = hermes.start_task("div'e sifir kontrolu ekle")
    ctl = [{"request_id": "r1", "execution_generation": 1, "description": "rm -rf build"}]
    state["run"] = {"status": "waiting_for_approval", "pending_controls": ctl}
    hermes.poll_tasks()
    hermes.poll_tasks()
    assert [p[0] for p in pushes] == ["Hermes needs approval"], pushes
    assert hermes.tasks()[0]["status"] == "waiting"
    hermes.answer(t["id"], "once")
    sent = calls[-1]
    assert sent[1] == "/v1/runs/run_x/approval" and sent[2]["request_id"] == "r1", sent
    state["run"] = {"status": "completed", "output": "Duzeltildi.\ndetay"}
    hermes.poll_tasks()
    assert hermes.tasks()[0]["status"] == "completed" and pushes[-1][1] == "Duzeltildi.", pushes
    hermes.poll_tasks()
    assert len(pushes) == 2, "bitmis is tekrar yoklandi"
    try:
        hermes.start_task("   ")
        raise AssertionError("bos gorev kabul edildi")
    except ValueError:
        pass

    # --- Hermes cron -> push: first poll silent, then only new runs ---
    jobs = [{"id": "a1", "name": "Su ic", "no_agent": True, "last_run_at": "t0", "last_status": "ok"},
            {"id": "b2", "name": "Haber", "no_agent": False, "last_run_at": None}]
    hermes._api = lambda *a, **kw: {"jobs": jobs}
    pushes.clear()
    hermes.poll_jobs()
    assert pushes == [], "eski calismalar push'landi"
    jobs[0]["last_run_at"] = "t1"
    jobs[1] |= {"last_run_at": "t1", "last_status": "error", "last_error": "429"}
    hermes.poll_jobs()
    hermes.poll_jobs()
    assert pushes == [("Reminder", "Su ic", "/"), ("Hermes job failed: Haber", "429", "/")], pushes
    hermes._api, hermes.send_push = real_api, real_push

    # --- model settings: bad input is rejected before reaching the shell ---
    real_wsl = hermes.sh
    hermes.sh = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("WSL'e gitti"))
    for bad in [("yok", "m"), ("gemini", "a b"), ("gemini", "m; rm -rf ~"), ("gemini", "m", "kisa"),
                ("gemini", "m", "anahtar'ile tirnak\n"), ("custom", "m", "", "ftp://x"),
                ("custom", "m", "", "https://x/$(id)")]:
        try:
            hermes.set_model(*bad)
            raise AssertionError(f"kabul edildi: {bad}")
        except ValueError:
            pass
    hermes.sh = real_wsl

    # --- kill switch: token changes, other lines kept ---
    env = Path(core.HERE, "data", "selftest.env")
    env.write_text("A=1\nAPP_TOKEN=eski\nB=2\n", encoding="utf-8")
    main.rotate_token(env)
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "A=1" and lines[2] == "B=2", lines
    assert lines[1].startswith("APP_TOKEN=") and len(lines[1]) > 40 and "eski" not in lines[1]
    env.write_text("A=1\n", encoding="utf-8")
    try:
        main.rotate_token(env)
        raise AssertionError("APP_TOKEN'siz dosya sessizce gecti")
    except SystemExit:
        pass
    env.unlink()

    # --- send_push must work from another thread (the ticker does that) ---
    assert asyncio.run(asyncio.to_thread(core.send_push, "test", "govde")) == 0

    # --- failed-login lock kicks in ---
    with closing(core.db()) as con:
        for _ in range(main.AUTH_FAIL_LIMIT):
            core.log(con, "auth-fail", "x", "401")
    expect(429, main.guard, good)

    os.remove(core.DB)
    print("tests ok")


if __name__ == "__main__":
    main_test()
