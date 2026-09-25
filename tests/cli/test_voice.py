"""Tests for hath0r voice command group."""

from __future__ import annotations

import json

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_voice_help():
    runner = CliRunner()
    res = runner.invoke(main, ["voice", "--help"])
    assert res.exit_code == 0
    assert "status" in res.output
    assert "exec" in res.output
    assert "listen" in res.output


def test_voice_status_json():
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "json", "voice", "status"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["schema"] == "hath0r.cli.response/1"
    assert data["command"] == "voice.status"
    assert data["state"] == "ok"
    assert data["data"]["status"] == "ready"
    assert "stt" in data["data"]
    assert "tts" in data["data"]
    assert "router" in data["data"]


def test_voice_exec_fastpath_doctor_json():
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "json", "voice", "exec", "hath0r doctor", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["state"] == "ok"
    assert data["data"]["action"]["schema"] == "hath0r.voice.action/1"
    assert data["data"]["action"]["intent"] == "cli_command"
    assert data["data"]["action"]["routing_tier"] == "system_one"
    assert data["data"]["action"]["payload"]["command"] == "hath0r doctor"


def test_voice_exec_guest_tier_blocks_unauthorized_action():
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "json", "voice", "exec", "open Spotify", "--trust-tier", "guest"])
    # Cli exits 1 on governance block
    assert res.exit_code != 0
    data = json.loads(res.output)
    assert data["state"] == "degraded"
    assert data["data"]["blocked"] is True
    assert len(data["diagnostics"]) >= 1
    assert data["diagnostics"][0]["code"] == "VOICE_GOVERNANCE_BLOCKED"


def test_voice_exec_elevated_tier_allows_computer_use():
    runner = CliRunner()
    args = ["--output", "json", "voice", "exec", "open Spotify", "--trust-tier", "elevated", "--dry-run"]
    res = runner.invoke(main, args)
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["state"] == "ok"
    assert data["data"]["executed"] is False
    assert data["data"]["dry_run"] is True
    assert data["data"]["action"]["intent"] == "computer_use"
    assert data["data"]["action"]["payload"]["target"] == "Spotify"


def test_voice_listen_simulation():
    runner = CliRunner()
    # Feed newline then simulated utterance
    res = runner.invoke(main, ["--output", "json", "voice", "listen", "--max-utterances", "1"], input="hath0r doctor\n")
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "voice.listen"
    assert data["state"] == "ok"
    assert data["data"]["captured_count"] == 1


def test_voice_service_cli_lifecycle():
    runner = CliRunner()
    # Check status initially
    res_status = runner.invoke(main, ["--output", "json", "voice", "service", "status"])
    assert res_status.exit_code == 0
    data_status = json.loads(res_status.output)
    assert data_status["command"] == "voice.service.status"
    assert data_status["state"] == "ok"
    assert data_status["data"]["running"] is False

    # Stop service when not running
    res_stop = runner.invoke(main, ["--output", "json", "voice", "service", "stop"])
    assert res_stop.exit_code == 0
    data_stop = json.loads(res_stop.output)
    assert data_stop["command"] == "voice.service.stop"
    assert data_stop["state"] == "ok"
    assert data_stop["data"]["status"] == "not_running"


def test_voice_service_cli_help():
    runner = CliRunner()
    res = runner.invoke(main, ["voice", "service", "--help"])
    assert res.exit_code == 0
    assert "install" in res.output
    assert "uninstall" in res.output
    assert "start" in res.output
    assert "stop" in res.output


