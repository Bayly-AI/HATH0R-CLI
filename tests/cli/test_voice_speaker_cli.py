"""CLI command tests for Phase 1 voice speaker and announcements."""

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_voice_speak_text():
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "json", "voice", "speak", "Hello operator, all systems normal."])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "voice.speak"
    assert data["state"] == "ok"
    assert "Hello operator" in data["data"]["text"]


def test_cli_voice_announce_queue_and_drain():
    runner = CliRunner()
    # 1. Enqueue announcement
    res_q = runner.invoke(main, ["--output", "json", "voice", "announce", "--queue", "Task 42 completed."])
    assert res_q.exit_code == 0
    data_q = json.loads(res_q.output)
    assert data_q["command"] == "voice.announce"
    assert data_q["data"]["queued"] is True

    # 2. Check speaker status
    res_st = runner.invoke(main, ["--output", "json", "voice", "speaker", "status"])
    assert res_st.exit_code == 0
    data_st = json.loads(res_st.output)
    assert data_st["command"] == "voice.speaker.status"
    assert data_st["data"]["pending_count"] >= 1

    # 3. Drain queue
    res_drain = runner.invoke(main, ["--output", "json", "voice", "speaker", "drain"])
    assert res_drain.exit_code == 0
    data_drain = json.loads(res_drain.output)
    assert data_drain["command"] == "voice.speaker.drain"
    assert data_drain["data"]["drained_count"] >= 1


def test_cli_voice_speaker_stop():
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "json", "voice", "speaker", "stop"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "voice.speaker.stop"
    assert data["data"]["status"] == "not_running"


def test_cli_speak_mode_on_off_status_toggle():
    runner = CliRunner()
    # 1. Enable speak mode
    res_on = runner.invoke(main, ["--output", "json", "speak", "on", "--silent"])
    assert res_on.exit_code == 0
    data_on = json.loads(res_on.output)
    assert data_on["command"] == "speak.on"
    assert data_on["data"]["enabled"] is True

    # 2. Status
    res_st = runner.invoke(main, ["--output", "json", "speak", "status"])
    assert res_st.exit_code == 0
    data_st = json.loads(res_st.output)
    assert data_st["command"] == "speak.status"
    assert data_st["data"]["enabled"] is True

    # 3. Toggle off
    res_tog = runner.invoke(main, ["--output", "json", "speak", "toggle"])
    assert res_tog.exit_code == 0
    data_tog = json.loads(res_tog.output)
    assert data_tog["command"] == "speak.toggle"
    assert data_tog["data"]["enabled"] is False

    # 4. Explicit off
    res_off = runner.invoke(main, ["--output", "json", "speak", "off", "--silent"])
    assert res_off.exit_code == 0
    data_off = json.loads(res_off.output)
    assert data_off["command"] == "speak.off"
    assert data_off["data"]["enabled"] is False

