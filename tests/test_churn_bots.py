"""Unit tests for ChurnManagerBot and HotspotRefactorBot."""

from hath0r_cli.bots.churn_manager_bot import ChurnManagerBot, HotspotRefactorBot


def test_churn_manager_bot_doctor():
    bot = ChurnManagerBot()
    doc = bot.doctor()
    assert doc["status"] == "OK"
    assert doc["is_git_repository"] is True
    assert doc["mcp_registered"] is True


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
