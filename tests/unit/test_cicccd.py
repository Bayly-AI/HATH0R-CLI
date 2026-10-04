"""Unit tests for CICCCD CLI commands and CICCCDManagingBot."""

from __future__ import annotations

import json

from click.testing import CliRunner

from hath0r_cli.bots.cicccd_bot import CICCCDManagingBot
from hath0r_cli.cli import main


def test_cicccd_managing_bot_status(tmp_path):
    bot = CICCCDManagingBot(root_dir=str(tmp_path))
    status = bot.status()
    assert "state" in status
    assert "freshness" in status


def test_cicccd_managing_bot_validate(tmp_path):
    bot = CICCCDManagingBot(root_dir=str(tmp_path))
    res = bot.validate_cicccd()
    assert "valid" in res
    assert "ci" in res
    assert "cc" in res
    assert "cd" in res


def test_cicccd_managing_bot_calibrate(tmp_path):
    bot = CICCCDManagingBot(root_dir=str(tmp_path))
    res = bot.calibrate(iterations=1)
    assert res["success"] is True
    assert "calibration_id" in res
    assert "updated_parameters" in res


def test_cicccd_cli_status():
    runner = CliRunner()
    result = runner.invoke(main, ["-o", "text", "cicccd", "status"])
    assert result.exit_code == 0
    assert "CICCCD" in result.output

    # Test JSON mode
    json_res = runner.invoke(main, ["-o", "json", "cicccd", "status"])
    assert json_res.exit_code == 0
    parsed = json.loads(json_res.output)
    assert parsed["state"] == "ok"
    assert parsed["command"] == "cicccd status"


def test_cicccd_cli_validate():
    runner = CliRunner()
    result = runner.invoke(main, ["-o", "text", "cicccd", "validate"])
    assert result.exit_code == 0
    assert "Continuous Integration" in result.output

    # Test JSON mode
    json_res = runner.invoke(main, ["-o", "json", "cicccd", "validate"])
    assert json_res.exit_code == 0
    parsed = json.loads(json_res.output)
    assert parsed["state"] in ["ok", "warning"]


def test_cicccd_cli_calibrate():
    runner = CliRunner()
    result = runner.invoke(main, ["-o", "text", "cicccd", "calibrate", "--iterations", "1"])
    assert result.exit_code == 0
    assert "Continuous Calibration Run Completed" in result.output

    # Test JSON mode
    json_res = runner.invoke(main, ["-o", "json", "cicccd", "calibrate", "--iterations", "1"])
    assert json_res.exit_code == 0
    parsed = json.loads(json_res.output)
    assert parsed["state"] == "ok"


def test_cicccd_cli_autotune():
    runner = CliRunner()
    result = runner.invoke(main, ["-o", "text", "cicccd", "auto-tune", "--interval", "100"])
    assert result.exit_code == 0
    assert "Auto-Tune Daemon Active" in result.output

    # Test JSON mode
    json_res = runner.invoke(main, ["-o", "json", "cicccd", "auto-tune", "--interval", "100"])
    assert json_res.exit_code == 0
    parsed = json.loads(json_res.output)
    assert parsed["state"] == "ok"
