"""Unit tests for hath0r churn CLI command group."""

from pathlib import Path
from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_churn_doctor():
    runner = CliRunner()
    result = runner.invoke(main, ["churn", "doctor", "--json"])
    assert result.exit_code == 0
    assert '"status": "OK"' in result.output
    assert '"is_git_repository": true' in result.output
    assert '"schema_contract"' in result.output


def test_cli_churn_analyze():
    runner = CliRunner()
    result = runner.invoke(main, ["churn", "analyze", "--days", "30", "--json"])
    assert result.exit_code == 0
    assert '"schema_version": "hath0r.pmat.churn/1"' in result.output
    assert '"summary"' in result.output
    assert '"hotspots"' in result.output


def test_cli_churn_hotspots():
    runner = CliRunner()
    result = runner.invoke(main, ["churn", "hotspots", "--limit", "5", "--json"])
    assert result.exit_code == 0
    assert "[" in result.output
    assert "]" in result.output


def test_cli_churn_pr_risk():
    runner = CliRunner()
    result = runner.invoke(main, ["churn", "pr-risk", "--base", "development", "--json"])
    assert result.exit_code == 0
    assert '"base_branch": "development"' in result.output
    assert '"overall_risk_tier"' in result.output
    assert '"recommended_reasoning_tier"' in result.output


def test_cli_churn_ui_generation(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["churn", "ui"])
    assert result.exit_code == 0
    assert "Generative UI Churn Heatmap rendered to:" in result.output


def test_cli_churn_refactor_plan():
    runner = CliRunner()
    result = runner.invoke(main, ["churn", "refactor-plan", "src/hath0r_cli/cli.py", "--json"])
    assert result.exit_code == 0
    assert '"refactoring_type": "MODULAR_DECOUPLING"' in result.output
    assert '"proposed_steps"' in result.output
