"""Tests for VoiceDaemonBot and voice daemon CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from hath0r_cli.bots.voice_daemon import VoiceDaemonBot
from hath0r_cli.cli import main


def test_voice_daemon_bot_lifecycle(tmp_path: Path) -> None:
    bot = VoiceDaemonBot(cwd=tmp_path)

    # Check initial stopped status
    st1 = bot.status()
    assert st1["running"] is False
    assert st1["pid"] is None

    # Test emit event (fallback spool when daemon not running)
    with patch("hath0r_cli.bots.voice_speaker.VoiceSpeakerBot.speak") as mock_speak:
        res_emit = bot.emit_event(
            event_type="task_start",
            message="Starting task compilation",
            payload={"task_id": "task-123"},
            speak=True,
        )
        assert res_emit["success"] is True
        assert res_emit["event_type"] == "task_start"
        assert res_emit["ipc_delivery"] == "file_spool"
        assert mock_speak.called

    # Verify event logged to spool file
    spool_file = tmp_path / ".hath0r" / "state" / "voice_events.jsonl"
    assert spool_file.is_file()
    lines = spool_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["type"] == "task_start"
    assert record["message"] == "Starting task compilation"


def test_voice_daemon_cli_commands(tmp_path: Path) -> None:
    runner = CliRunner()

    with (
        patch("hath0r_cli.bots.voice_daemon.VoiceDaemonBot.start_daemon") as mock_start,
        patch("hath0r_cli.bots.voice_daemon.VoiceDaemonBot.stop_daemon") as mock_stop,
        patch("hath0r_cli.bots.voice_daemon.VoiceDaemonBot.status") as mock_status,
        patch("hath0r_cli.bots.voice_daemon.VoiceDaemonBot.emit_event") as mock_emit,
    ):
        mock_start.return_value = {"success": True, "status": "started", "pid": 9999, "socket": "/tmp/sock"}
        mock_stop.return_value = {"success": True, "status": "stopped", "pid": 9999}
        mock_status.return_value = {
            "running": True,
            "pid": 9999,
            "socket": "/tmp/sock",
            "uptime_seconds": 12.5,
            "events_processed": 3,
        }
        mock_emit.return_value = {
            "success": True,
            "event_id": "evt-123",
            "event_type": "ci_failure",
            "ipc_delivery": "socket",
            "message": "CI tests failed",
        }

        # 1. Start daemon
        res_start = runner.invoke(main, ["--output", "json", "voice", "daemon", "start"])
        assert res_start.exit_code == 0
        data_start = json.loads(res_start.output)
        assert data_start["data"]["status"] == "started"

        # 2. Status daemon
        res_status = runner.invoke(main, ["--output", "json", "voice", "daemon", "status"])
        assert res_status.exit_code == 0
        data_status = json.loads(res_status.output)
        assert data_status["data"]["running"] is True
        assert data_status["data"]["pid"] == 9999

        # 3. Emit event
        res_emit = runner.invoke(main, ["voice", "daemon", "emit", "ci_failure", "CI tests failed"])
        assert res_emit.exit_code == 0
        assert "Event Emitted" in res_emit.output or "evt-123" in res_emit.output

        # 4. Stop daemon
        res_stop = runner.invoke(main, ["--output", "json", "voice", "daemon", "stop"])
        assert res_stop.exit_code == 0
        data_stop = json.loads(res_stop.output)
        assert data_stop["data"]["status"] == "stopped"
