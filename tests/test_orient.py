"""Test suite for OrientBot and 'hath0r orient' command in HATH0R-CLI."""

from __future__ import annotations

import json
from pathlib import Path
from click.testing import CliRunner
import pytest

from hath0r_cli.bots.orient_bot import OrientBot
from hath0r_cli.commands.orient import orient_cmd


@pytest.fixture
def workspace_root() -> Path:
    return Path(__file__).parent.parent.resolve()


@pytest.fixture
def orient_bot(workspace_root: Path) -> OrientBot:
    return OrientBot(workspace_root=workspace_root)


def test_orient_bot_lifecycle(orient_bot: OrientBot, workspace_root: Path) -> None:
    assert orient_bot.is_triggered_by("orient")
    assert orient_bot.is_triggered_by("hath0r orient")
    res = orient_bot.run(repo_path=workspace_root, render_mode="markdown")
    assert res["bot_id"] == "orient-bot"
    assert "report" in res
    assert res["report"]["schema_version"] == "hath0r.orient.report/1"
    assert res["report"]["verdict"]["status"] in ("ORIENTED", "NEEDS_ATTENTION")
    assert "output" in res
    assert "# Repository Orientation Report" in res["output"]


def test_orient_cli_json(workspace_root: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(orient_cmd, ["--repo", str(workspace_root), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "hath0r.orient.report/1"
    assert "agentgraph" in payload
    assert "readme" in payload
    assert "code_scan" in payload
    assert "metrics" in payload
    assert "calibration" in payload
    assert "verdict" in payload


def test_orient_cli_markdown(workspace_root: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(orient_cmd, ["--repo", str(workspace_root), "--markdown"])
    assert result.exit_code == 0
    assert "Repository Orientation Report" in result.output
    assert "Executive Operational Scorecard" in result.output
