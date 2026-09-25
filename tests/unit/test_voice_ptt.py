"""Unit tests for Hath0r Voice Subsystem and Push-to-Talk configuration."""

from pathlib import Path
from unittest.mock import patch

from hath0r_cli.voice import (
    PushToTalkConfig,
    evaluate_and_dispatch_voice,
    get_push_to_talk_config,
    inspect_voice_subsystem,
    save_push_to_talk_config,
    validate_trust_tier,
    wait_for_push_to_talk_trigger,
)


def test_push_to_talk_config_defaults(tmp_path: Path):
    cfg_file = tmp_path / "voice.json"
    cfg = get_push_to_talk_config(cfg_file)
    assert cfg.enabled is True
    assert cfg.default_key == "right_ctrl"
    assert cfg.prompt_for_key is True
    assert "right_ctrl" in cfg.supported_keys


def test_save_and_load_push_to_talk_config(tmp_path: Path):
    cfg_file = tmp_path / "voice.json"
    custom_cfg = PushToTalkConfig(
        enabled=True,
        default_key="space",
        prompt_for_key=False,
        supported_keys=["space", "enter"],
    )
    save_push_to_talk_config(custom_cfg, config_path=cfg_file)
    loaded = get_push_to_talk_config(cfg_file)

    assert loaded.enabled is True
    assert loaded.default_key == "space"
    assert loaded.prompt_for_key is False
    assert loaded.supported_keys == ["space", "enter"]


def test_inspect_voice_subsystem_contains_push_to_talk():
    status = inspect_voice_subsystem()
    assert status["status"] == "ready"
    assert "push_to_talk" in status
    assert status["push_to_talk"]["enabled"] is True
    assert status["push_to_talk"]["default_key"] == "right_ctrl"
    assert status["push_to_talk"]["prompt_for_key"] is True


def test_validate_trust_tier_guest_restrictions():
    # Doctor allowed in guest
    permitted, reason = validate_trust_tier(
        intent="cli_command",
        command="hath0r doctor",
        current_tier="guest",
    )
    assert permitted is True
    assert reason is None

    # Dangerous command blocked in guest
    permitted, reason = validate_trust_tier(
        intent="cli_command",
        command="rm -rf /",
        current_tier="guest",
    )
    assert permitted is False
    assert "blocked in guest tier" in (reason or "")


def test_evaluate_and_dispatch_fastpath():
    data, diagnostics, state = evaluate_and_dispatch_voice(
        transcript="hath0r version",
        trust_tier="elevated",
        dry_run=True,
    )
    assert state == "ok"
    assert data["executed"] is False
    assert data["dry_run"] is True
    assert data["action"]["intent"] == "cli_command"
    assert data["action"]["payload"]["command"] == "hath0r version"


def test_wait_for_push_to_talk_trigger_non_interactive():
    # In non-interactive test harness, returns True immediately
    with patch("os.isatty", return_value=False):
        assert wait_for_push_to_talk_trigger("right_ctrl", timeout_seconds=1.0) is True
