"""Unit tests for hath0r pmat CLI command group."""

from click.testing import CliRunner
from hath0r_cli.cli import main


def test_cli_pmat_doctor():
    runner = CliRunner()
    result = runner.invoke(main, ["pmat", "doctor", "--json"])
    assert result.exit_code == 0
    assert '"status": "OK"' in result.output
    assert '"bot_name": "PmatBot"' in result.output


def test_cli_pmat_stats_json():
    runner = CliRunner()
    result = runner.invoke(main, ["pmat", "stats", "--window", "30", "--format", "json"])
    assert result.exit_code == 0
    assert '"schema_version": "hath0r.pmat.stats/1"' in result.output
    assert '"provability"' in result.output
    assert '"complexity"' in result.output


def test_cli_pmat_stats_markdown():
    runner = CliRunner()
    result = runner.invoke(main, ["pmat", "stats", "--format", "markdown"])
    assert result.exit_code == 0
    assert "# PMAT Multi-Dimensional Report:" in result.output
    assert "| File Path |" in result.output


def test_cli_pmat_bot_run():
    runner = CliRunner()
    result = runner.invoke(main, ["pmat", "bot-run", "check provability score"])
    assert result.exit_code == 0
    assert '"provability"' in result.output
