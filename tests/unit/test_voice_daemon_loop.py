"""Run the voice daemon loop in-process: socket IPC, spool draining, shutdown."""

from __future__ import annotations

import json
import os
import threading

import pytest

from hath0r_cli.bots import voice_daemon
from hath0r_cli.bots.voice_daemon import VoiceDaemonBot


class _Speaker:
    spoken: list[str] = []

    def speak(self, text):
        self.spoken.append(text)
        return {"success": True}


@pytest.fixture
def speaker(monkeypatch):
    _Speaker.spoken = []
    monkeypatch.setattr(voice_daemon, "VoiceSpeakerBot", _Speaker)
    return _Speaker


def test_daemon_loop_handles_socket_and_spool_events(tmp_path, monkeypatch, speaker):
    bot = VoiceDaemonBot(cwd=tmp_path)
    bot._ensure_dirs()
    bot.socket_path.write_text("stale", encoding="utf-8")
    spool = [
        {"message": "spooled **build** done", "speak": True},
        {"message": "quiet", "speak": False},
    ]
    bot.events_file.write_text("\n".join(json.dumps(e) for e in spool) + "\n\n", encoding="utf-8")

    handlers = {}
    monkeypatch.setattr(voice_daemon.signal, "signal", lambda sig, fn: handlers.__setitem__(sig, fn))
    real_sleep = voice_daemon.time.sleep
    ticks = {"n": 0}

    def fake_sleep(_s):
        ticks["n"] += 1
        if ticks["n"] == 1:
            sender = VoiceDaemonBot(cwd=tmp_path)
            t = threading.Thread(target=lambda: sender.emit_event("task_end", "socket event", speak=True))
            t.start()
            t.join(5)
        elif ticks["n"] == 2:
            bot.events_file.write_text("not json\n", encoding="utf-8")
        elif ticks["n"] >= 3:
            handlers[voice_daemon.signal.SIGTERM](voice_daemon.signal.SIGTERM, None)
        real_sleep(0)

    monkeypatch.setattr(voice_daemon.time, "sleep", fake_sleep)
    bot.run_daemon_loop()

    state = json.loads(bot.state_file.read_text(encoding="utf-8"))
    assert state["running"] is False
    assert state["events_processed"] >= 2
    assert any("spooled" in s for s in speaker.spoken)
    assert not bot.pid_file.exists()


def test_start_status_and_stop_with_fake_process(tmp_path, monkeypatch, speaker):
    bot = VoiceDaemonBot(cwd=tmp_path)
    alive = {"pids": {4242}}

    def fake_kill(pid, sig):
        if pid not in alive["pids"]:
            raise ProcessLookupError(pid)
        if sig != 0:
            alive["pids"].discard(pid)

    class _Proc:
        pid = 4242

    monkeypatch.setattr(voice_daemon.os, "kill", fake_kill)
    monkeypatch.setattr(voice_daemon.subprocess, "Popen", lambda *a, **k: _Proc())
    monkeypatch.setattr(voice_daemon.time, "sleep", lambda _s: None)

    started = bot.start_daemon(background=True)
    assert started["status"] == "started" and started["pid"] == 4242
    assert bot.start_daemon()["status"] == "already_running"

    bot.state_file.write_text(json.dumps({"uptime_seconds": 3.5, "events_processed": 2}), encoding="utf-8")
    st = bot.status()
    assert st["running"] and st["events_processed"] == 2
    bot.state_file.write_text("{bad", encoding="utf-8")
    assert bot.status()["events_processed"] == 0

    emitted = bot.emit_event("ping", "hello", speak=True)
    assert emitted["ipc_delivery"] == "file_spool"

    bot.socket_path.write_text("", encoding="utf-8")
    stopped = bot.stop_daemon()
    assert stopped["status"] == "stopped" and not bot.socket_path.exists()
    assert bot.stop_daemon()["status"] == "not_running"


def test_is_running_clears_bad_pid_file(tmp_path):
    bot = VoiceDaemonBot(cwd=tmp_path)
    bot._ensure_dirs()
    bot.pid_file.write_text("not-a-pid", encoding="utf-8")
    assert bot.is_running() == (False, None)
    assert not bot.pid_file.exists()
    bot.pid_file.write_text(str(os.getpid()), encoding="utf-8")
    assert bot.is_running() == (True, os.getpid())


def test_foreground_start_runs_loop(tmp_path, monkeypatch):
    bot = VoiceDaemonBot(cwd=tmp_path)
    monkeypatch.setattr(VoiceDaemonBot, "run_daemon_loop", lambda self: None)
    assert bot.start_daemon(background=False) == {"success": True, "status": "stopped"}
