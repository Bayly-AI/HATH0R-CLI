"""Unit tests for Hath0r CLI MCP connection management and commands."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from hath0r_cli import cli
from hath0r_cli.mcp import (
    McpConnectionStatus,
    check_mcp_connection,
    load_mcp_connections,
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_load_mcp_connections_returns_default_servers() -> None:
    servers = load_mcp_connections()
    assert len(servers) >= 3
    server_ids = [s["id"] for s in servers]
    assert "hath0r-mcp" in server_ids
    assert "bai-mcp" in server_ids
    assert "1-nation-mcp" in server_ids


def test_check_mcp_connection_mocked_success() -> None:
    server = {
        "id": "test-mcp",
        "name": "TestMCP",
        "group": "test",
        "base_url": "http://127.0.0.1:9999",
        "health_endpoint": "/health",
        "ready_endpoint": "/health",
        "mcp_endpoint": "/mcp",
        "transport": "streamable-http",
    }

    with patch("hath0r_cli.mcp._http_get") as mock_get, patch("hath0r_cli.mcp._http_jsonrpc") as mock_rpc:
        mock_get.return_value = (200, {"status": "healthy"}, None)
        mock_rpc.return_value = (
            200,
            {"result": {"tools": [{"name": "tool_a"}, {"name": "tool_b"}]}},
            None,
        )

        status = check_mcp_connection(server)
        assert status.state == "ok"
        assert status.tools_count == 2
        assert "tool_a" in status.tools
        assert status.health_status == "healthy"


def test_check_mcp_connection_unreachable() -> None:
    server = {
        "id": "dead-mcp",
        "name": "DeadMCP",
        "group": "test",
        "base_url": "http://127.0.0.1:9999",
        "health_endpoint": "/health",
        "ready_endpoint": "/health",
        "mcp_endpoint": "/mcp",
        "transport": "streamable-http",
    }

    with patch("hath0r_cli.mcp._http_get") as mock_get:
        mock_get.return_value = (0, None, "Connection refused")

        status = check_mcp_connection(server)
        assert status.state == "unreachable"
        assert status.tools_count == 0
        assert "Connection refused" in status.message


def test_cli_mcp_list(runner: CliRunner) -> None:
    res = runner.invoke(cli.main, ["mcp", "list"])
    assert res.exit_code == 0
    assert "Hath0rMCP" in res.stdout
    assert "BaylyAIMCP" in res.stdout
    assert "1-NationMCP" in res.stdout


def test_cli_mcp_list_json(runner: CliRunner) -> None:
    res = runner.invoke(cli.main, ["--output", "json", "mcp", "list"])
    assert res.exit_code == 0
    payload = json.loads(res.stdout)
    assert payload["command"] == "mcp.list"
    assert payload["state"] == "ok"
    assert "servers" in payload["data"]
    assert payload["data"]["count"] >= 3


def test_cli_mcp_check_mocked(runner: CliRunner) -> None:
    mock_status = McpConnectionStatus(
        server_id="mock-mcp",
        name="MockMCP",
        group="test",
        base_url="http://127.0.0.1:9999",
        transport="streamable-http",
        state="ok",
        latency_ms=12,
        health_status="healthy",
        ready=True,
        tools_count=3,
        tools=["t1", "t2", "t3"],
        message="Connected successfully",
    )

    with patch("hath0r_cli.mcp.check_all_mcp_connections", return_value=[mock_status]):
        res = runner.invoke(cli.main, ["--output", "text", "mcp", "check"])
        assert res.exit_code == 0
        assert "MockMCP" in res.stdout
        assert "OK" in res.stdout

        res_json = runner.invoke(cli.main, ["--output", "json", "mcp", "check"])
        assert res_json.exit_code == 0
        data = json.loads(res_json.stdout)
        assert data["command"] == "mcp.check"
        assert data["state"] == "ok"
        assert data["data"]["ok_count"] == 1


def test_cli_mcp_call_mocked(runner: CliRunner) -> None:
    with patch("hath0r_cli.mcp.call_mcp_tool", return_value={"echo": "success"}):
        res = runner.invoke(cli.main, ["mcp", "call", "hath0r-mcp", "suite_info"])
        assert res.exit_code == 0
        assert "echo" in res.stdout
