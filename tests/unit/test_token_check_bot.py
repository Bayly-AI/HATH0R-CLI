"""Unit tests for TokenCheckWorkflowBot, CLI command, and FastMCP tool."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.token_check_bot import TokenCheckWorkflowBot
from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot
from hath0r_cli.cli import main as cli
from hath0r_cli.server.mcp_server import create_mcp_server


def test_token_check_workflow_bot():
    """Verify TokenCheckWorkflowBot execution and artifact rendering."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cwd = Path(tmp_dir)
        telemetry_bot = TokenTelemetryCLIBot(cwd=cwd)
        telemetry_bot.record(prompt="hello world", user_id="test_user", model="claude-3-5-sonnet")

        check_bot = TokenCheckWorkflowBot(cwd=cwd)
        artifact_dir = cwd / "artifacts"
        res = check_bot.run_token_check(user_id="test_user", days=90, artifact_dir=artifact_dir)

        assert res["success"] is True
        assert res["total_records"] == 1
        assert "FinOps Token Telemetry" in res["markdown_report"]
        assert (artifact_dir / "finops_token_histogram.html").exists()


def test_finops_tokens_check_cli():
    """Verify 'hath0r finops tokens check' CLI command."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        cwd = Path(tmp_dir)
        telemetry_bot = TokenTelemetryCLIBot(cwd=cwd)
        telemetry_bot.record(prompt="cli test prompt", user_id="raybayly")

        res = runner.invoke(cli, ["-o", "text", "finops", "tokens", "check", "--user", "raybayly"])
        assert res.exit_code == 0, res.output
        assert "FinOps Token Telemetry" in res.output


def test_mcp_server_token_check_tool():
    """Verify hath0r_finops_token_check tool registration in FastMCP server."""
    server = create_mcp_server()
    assert "hath0r_finops_token_check" in server._tool_manager._tools
