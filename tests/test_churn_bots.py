"""Unit tests for ChurnManagerBot and HotspotRefactorBot."""

import json

import pytest

from hath0r_cli.bots.churn_manager_bot import ChurnManagerBot, HotspotRefactorBot


def _write_mcp_config(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_churn_manager_bot_doctor(tmp_path, monkeypatch):
    cfg = _write_mcp_config(tmp_path / "mcp.json", {"servers": [{"id": "pmat-mcp", "command": "pmat"}]})
    monkeypatch.setenv("HATH0R_MCP_CONFIG", str(cfg))
    bot = ChurnManagerBot()
    doc = bot.doctor()
    assert doc["status"] == "OK"
    assert doc["is_git_repository"] is True
    assert doc["mcp_registered"] is True


@pytest.mark.parametrize(
    "data, expected",
    [
        ({"mcpServers": {"pmat-mcp": {"command": "pmat"}}}, True),
        ({"servers": [{"id": "hath0r-mcp"}]}, False),
        ({}, False),
    ],
)
def test_churn_manager_bot_doctor_mcp_registration(tmp_path, monkeypatch, data, expected):
    cfg = _write_mcp_config(tmp_path / "mcp.json", data)
    monkeypatch.setenv("HATH0R_MCP_CONFIG", str(cfg))
    doc = ChurnManagerBot().doctor(repo_path=tmp_path)
    assert doc["mcp_registered"] is expected
    assert doc["is_git_repository"] is False


def test_churn_manager_bot_doctor_invalid_mcp_config(tmp_path, monkeypatch):
    cfg = tmp_path / "mcp.json"
    cfg.write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("HATH0R_MCP_CONFIG", str(cfg))
    assert ChurnManagerBot().doctor(repo_path=tmp_path)["mcp_registered"] is False


def test_churn_manager_bot_analysis():
    bot = ChurnManagerBot()
    report = bot.analyze(days=30)
    assert report["schema_version"] == "hath0r.pmat.churn/1"
    assert "summary" in report
    assert "hotspots" in report
    assert isinstance(report["hotspots"], list)


def test_churn_manager_bot_pr_risk():
    bot = ChurnManagerBot()
    eval_res = bot.pr_risk(base_branch="development")
    assert eval_res["base_branch"] == "development"
    assert eval_res["overall_risk_tier"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert eval_res["recommended_reasoning_tier"] in ("LIGHT", "STANDARD", "REASONING")


def test_hotspot_refactor_bot_proposal():
    bot = HotspotRefactorBot()
    plan = bot.propose_refactoring("src/hath0r_cli/cli.py")
    assert plan["file_path"] == "src/hath0r_cli/cli.py"
    assert plan["refactoring_type"] == "MODULAR_DECOUPLING"
    assert len(plan["proposed_steps"]) > 0
