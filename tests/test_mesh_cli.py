"""Unit tests for hath0r mesh CLI command group."""

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_mesh_status():
    runner = CliRunner()
    result = runner.invoke(main, ["mesh", "status", "--json"])
    assert result.exit_code == 0
    assert '"status": "ONLINE"' in result.output
    assert '"bot_name": "MeshManagerBot"' in result.output


def test_cli_mesh_peers():
    runner = CliRunner()
    result = runner.invoke(main, ["mesh", "peers", "--json"])
    assert result.exit_code == 0
    assert '"peer_id": "peer-poc"' in result.output


def test_cli_mesh_ping():
    runner = CliRunner()
    result = runner.invoke(main, ["mesh", "ping", "--peer-id", "peer-poc", "--json"])
    assert result.exit_code == 0
    assert '"status": "ONLINE"' in result.output
    assert '"signature_verified": true' in result.output


def test_cli_mesh_route():
    runner = CliRunner()
    result = runner.invoke(main, ["mesh", "route", "--peer-id", "peer-poc", "--query", "governance"])
    assert result.exit_code == 0
    assert '"status": "DELIVERED"' in result.output


def test_cli_mesh_bot_run():
    runner = CliRunner()
    result = runner.invoke(main, ["mesh", "bot-run", "list peers"])
    assert result.exit_code == 0
    assert '"peer_id": "peer-poc"' in result.output
