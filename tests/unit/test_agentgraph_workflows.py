"""Tests for AgentGraph integration into Preflight, PR Bot, and Clean-Repo workflows."""

from __future__ import annotations

from pathlib import Path

from hath0r_cli.bots import PRBot
from hath0r_cli.bots.agentgraph_bot import AgentGraphBot
from hath0r_cli.bots.quality import PreflightBot
from hath0r_cli.bots.repo_clean import CleanReposWorkflowBot


def test_preflight_passes_with_valid_agentgraph(tmp_path: Path):
    """Preflight passes when AgentGraph is valid."""
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    bot = AgentGraphBot(cwd=tmp_path)
    bot.sync(persist=True)

    preflight = PreflightBot(cwd=tmp_path)
    ag_check = preflight._agentgraph_ok()
    assert ag_check["ok"] is True
    assert "AgentGraph valid" in ag_check["message"]


def test_preflight_fails_with_cyclic_agentgraph(tmp_path: Path):
    """Preflight fails when cyclic inheritance dependencies exist in AgentGraph."""
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    bot = AgentGraphBot(cwd=tmp_path)
    graph = {
        "schema_version": "hath0r.agentgraph/1",
        "graph_id": "test-preflight-fail",
        "nodes": [
            {"id": "role:x", "plane": "rules", "type": "agent_role", "label": "Role X"},
            {"id": "role:y", "plane": "rules", "type": "agent_role", "label": "Role Y"},
        ],
        "edges": [
            {"source": "role:x", "target": "role:y", "relation": "INHERITS_FROM", "is_current": True},
            {"source": "role:y", "target": "role:x", "relation": "INHERITS_FROM", "is_current": True},
        ],
    }
    bot.save_graph(graph, target_path=str(tmp_path))

    preflight = PreflightBot(cwd=tmp_path)
    ag_check = preflight._agentgraph_ok()
    assert ag_check["ok"] is False
    assert "Cyclic inheritance" in ag_check["error"]


def test_pr_bot_injects_agentgraph_summary(tmp_path: Path):
    """PR Bot injects AgentGraph audit summaries into PR descriptions."""
    bot = AgentGraphBot(cwd=tmp_path)
    bot.sync(persist=True)

    pr_bot = PRBot(cwd=tmp_path)
    res = pr_bot.create_pr(
        title="feat: test pr",
        body="Initial description",
        dry_run=True,
    )
    assert res["success"] is True
    assert "### AgentGraph Audit Summary" in res["body"]
    assert "Cycles Detected" in res["body"]


def test_repo_clean_step7_agentgraph_sync(tmp_path: Path):
    """RepoCleanLifecycleBot Step 7 runs agentgraph sync and validate."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "branch", "-M", "development"], cwd=tmp_path, check=True)

    clean_bot = CleanReposWorkflowBot(cwd=tmp_path)
    res = clean_bot.run_clean_repo_workflow(target_repos=[tmp_path], auto_commit=False)

    repo_report = res["repos"][0]
    step7 = repo_report["steps"].get("7_update_documentation")
    assert step7 is not None
    assert step7["agentgraph_synced"] is True
    assert step7["agentgraph_valid"] is True
    assert (tmp_path / ".hath0r" / "agentgraph" / "snapshot.json").is_file()
