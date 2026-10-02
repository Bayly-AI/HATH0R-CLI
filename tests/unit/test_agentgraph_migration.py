"""Unit tests for AgentGraph migration command and bot functionality."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.agentgraph_bot import AgentGraphBot
from hath0r_cli.commands.agentgraph import agentgraph


def test_migrate_repo_extracts_rules_and_roles(tmp_path: Path):
    """migrate_repo extracts rules from AGENTS.md and links default role."""
    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text(
        "# AGENTS.md\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        "| Role | Developer |\n\n"
        "## CR-CLI-ENTRY-001 — CLI-First\n"
        "## CR-BRANCH-GOV-001 — Promotion\n"
        "## CR-DOCKER-HATH0R-GROUP-001 — Docker\n",
        encoding="utf-8",
    )
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")

    bot = AgentGraphBot(cwd=tmp_path)
    res = bot.migrate_repo(tmp_path, update_agents_md=True)

    assert res["success"] is True
    assert res["rules_migrated"] >= 3
    assert res["validation"]["valid"] is True
    assert res["validation"]["cycles_detected"] == 0

    snapshot = tmp_path / ".hath0r" / "agentgraph" / "snapshot.json"
    assert snapshot.is_file()

    # Verify AGENTS.md updated with pointer
    content = agents_md.read_text(encoding="utf-8")
    assert "## AgentGraph Substrate" in content


def test_migrate_all_custom_dirs(tmp_path: Path):
    """migrate_all executes batch migration across candidate dirs."""
    repo1 = tmp_path / "repo1"
    repo1.mkdir()
    (repo1 / "AGENTS.md").write_text("# Repo 1\nCR-HATH0R-ROOT-001\n", encoding="utf-8")

    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    (repo2 / "AGENTS.md").write_text("# Repo 2\nCR-BRANCH-GOV-001\n", encoding="utf-8")

    bot = AgentGraphBot(cwd=tmp_path)
    res = bot.migrate_all(base_dirs=[str(repo1), str(repo2)])

    assert res["success"] is True
    assert res["migrated_count"] == 2
    assert res["all_valid"] is True


def test_cli_agentgraph_migrate(tmp_path: Path):
    """CLI hath0r agentgraph migrate runs cleanly."""
    import json

    (tmp_path / "AGENTS.md").write_text("# Test Repo\nCR-CLI-ENTRY-001\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(agentgraph, ["migrate", "--path", str(tmp_path)])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["state"] == "ok"
    assert data["data"]["success"] is True
    assert data["data"]["rules_migrated"] >= 1
