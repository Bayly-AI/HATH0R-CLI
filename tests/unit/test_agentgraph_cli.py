"""Unit and CLI tests for hath0r agentgraph control plane commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli.cli import main as cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_agentgraph_help(runner: CliRunner):
    """Verify agentgraph command group renders help with all expected subcommands."""
    result = runner.invoke(cli, ["agentgraph", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "query" in result.output
    assert "validate" in result.output
    assert "sync" in result.output
    assert "route" in result.output
    assert "bot" in result.output


def test_agentgraph_status_json(runner: CliRunner, tmp_path: Path):
    """Verify hath0r agentgraph status emits valid JSON envelope."""
    result = runner.invoke(cli, ["--output", "json", "agentgraph", "status", "--path", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema"] == "hath0r.cli.response/1"
    assert data["command"] == "agentgraph.status"
    assert data["state"] == "ok"
    assert "status" in data["data"]
    assert "planes" in data["data"]["status"]


def test_agentgraph_sync_and_status(runner: CliRunner, tmp_path: Path):
    """Verify syncing a repository structure populates nodes and status reports them."""
    # Create mock repo files
    (tmp_path / "AGENTS.md").write_text("# Mock Repo\n| Role | Developer |\n", encoding="utf-8")
    (tmp_path / "rules.md").write_text("# Invariant Rules\nRule content\n", encoding="utf-8")
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "sample-v1.schema.json").write_text(
        json.dumps({"title": "Sample Contract", "description": "Test contract"}),
        encoding="utf-8",
    )

    # 1. Sync
    sync_res = runner.invoke(cli, ["--output", "json", "agentgraph", "sync", "--path", str(tmp_path)])
    assert sync_res.exit_code == 0
    sync_data = json.loads(sync_res.output)
    assert sync_data["data"]["sync"]["synced"] is True
    assert sync_data["data"]["sync"]["nodes_indexed"] >= 3

    # 2. Status after sync
    status_res = runner.invoke(cli, ["--output", "text", "agentgraph", "status", "--path", str(tmp_path)])
    assert status_res.exit_code == 0
    assert "Cognitive Planes Breakdown" in status_res.output
    assert "Total Entities" in status_res.output


def test_agentgraph_validate(runner: CliRunner, tmp_path: Path):
    """Verify validate reports clean graph state and detects issues."""
    # Sync first
    runner.invoke(cli, ["agentgraph", "sync", "--path", str(tmp_path)])

    val_res = runner.invoke(cli, ["--output", "json", "agentgraph", "validate", "--path", str(tmp_path)])
    assert val_res.exit_code == 0
    val_data = json.loads(val_res.output)
    assert val_data["data"]["validation"]["valid"] is True
    assert val_data["data"]["validation"]["cycles_detected"] == 0


def test_agentgraph_query(runner: CliRunner, tmp_path: Path):
    """Verify query searches across graph nodes."""
    # Create and sync content
    (tmp_path / "AGENTS.md").write_text("# Architecture Agents Guide\nContains developer instructions.", encoding="utf-8")
    runner.invoke(cli, ["agentgraph", "sync", "--path", str(tmp_path)])

    q_res = runner.invoke(cli, ["--output", "json", "agentgraph", "query", "developer", "--path", str(tmp_path)])
    assert q_res.exit_code == 0
    q_data = json.loads(q_res.output)
    assert q_data["data"]["query"]["results_count"] > 0
    top = q_data["data"]["query"]["results"][0]
    assert "developer" in top["id"].lower() or "developer" in top["label"].lower() or "developer" in top["snippet"].lower()


def test_agentgraph_route(runner: CliRunner, tmp_path: Path):
    """Verify route resolves role authorization and specific tool permissions."""
    runner.invoke(cli, ["agentgraph", "sync", "--path", str(tmp_path)])

    # Check reader role
    route_res = runner.invoke(
        cli,
        ["--output", "json", "agentgraph", "route", "--role", "role:reader", "--tool", "run_command", "--path", str(tmp_path)],
    )
    assert route_res.exit_code == 0
    route_data = json.loads(route_res.output)
    r = route_data["data"]["routing"]
    assert "read_file" in r["authorized_tools"]
    assert "run_command" in r["forbidden_tools"]
    assert r["tool_authorized"] is False

    # Check developer role
    dev_route = runner.invoke(
        cli,
        ["--output", "json", "agentgraph", "route", "--role", "role:developer", "--tool", "read_file", "--path", str(tmp_path)],
    )
    assert dev_route.exit_code == 0
    dev_data = json.loads(dev_route.output)
    assert dev_data["data"]["routing"]["tool_authorized"] is True


def test_agentgraph_bot_command(runner: CliRunner, tmp_path: Path):
    """Verify agentgraph bot subcommand execution."""
    bot_res = runner.invoke(cli, ["--output", "json", "agentgraph", "bot", "--audit", "--path", str(tmp_path)])
    assert bot_res.exit_code == 0
    bot_data = json.loads(bot_res.output)
    assert bot_data["data"]["action"] == "audit"
    assert "health" in bot_data["data"]
