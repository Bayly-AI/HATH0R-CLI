"""Tests for AgentGraphBot: autonomous graph synchronization, healing, and cross-repo audits."""

from __future__ import annotations

import json
from pathlib import Path

from hath0r_cli.bots.agentgraph_bot import AgentGraphBot


def test_bot_sync_and_index(tmp_path: Path):
    """Test that AgentGraphBot correctly discovers and indexes files into AgentGraph."""
    # Setup mock workspace
    (tmp_path / "AGENTS.md").write_text("# Mock Agent\n| Role | Engine Specialist |\n", encoding="utf-8")
    (tmp_path / "rules.md").write_text("# Rules\nCR-CLI-ENTRY-001: Start with CLI.\n", encoding="utf-8")
    contracts_dir = tmp_path / "contracts"
    contracts_dir.mkdir()
    (contracts_dir / "test-v1.schema.json").write_text(
        json.dumps({"title": "Test Contract", "type": "object"}),
        encoding="utf-8",
    )

    bot = AgentGraphBot(cwd=tmp_path)
    sync_res = bot.sync(path=str(tmp_path), persist=True)

    assert sync_res["success"] is True
    assert sync_res["sync"]["nodes_indexed"] >= 3
    assert (tmp_path / ".hath0r" / "agentgraph" / "snapshot.json").is_file()

    status = bot.get_status(path=str(tmp_path))
    assert status["status"]["total_nodes"] >= 3
    assert "rules" in status["status"]["planes"]
    assert "knowledge" in status["status"]["planes"]


def test_bot_healing_and_orphan_cleanup(tmp_path: Path):
    """Test that AgentGraphBot detects and heals orphan edges and dependency cycles."""
    bot = AgentGraphBot(cwd=tmp_path)

    # Construct graph with an orphan edge and a cycle
    graph = {
        "schema_version": "hath0r.agentgraph/1",
        "graph_id": "test-heal",
        "nodes": [
            {"id": "role:a", "plane": "rules", "type": "agent_role", "label": "Role A", "properties": {}},
            {"id": "role:b", "plane": "rules", "type": "agent_role", "label": "Role B", "properties": {}},
        ],
        "edges": [
            # Orphan edge: target does not exist
            {"source": "role:a", "target": "role:ghost", "relation": "relates_to", "is_current": True},
            # Cycle: A -> B and B -> A
            {"source": "role:a", "target": "role:b", "relation": "INHERITS_FROM", "is_current": True},
            {"source": "role:b", "target": "role:a", "relation": "INHERITS_FROM", "is_current": True},
        ],
    }
    bot.save_graph(graph, target_path=str(tmp_path))

    # Pre-check validation fails
    val_before = bot.validate(path=str(tmp_path))
    assert val_before["validation"]["valid"] is False
    assert val_before["validation"]["cycles_detected"] >= 1

    # Run heal
    heal_res = bot.heal(path=str(tmp_path))
    assert heal_res["success"] is True
    assert heal_res["orphans_pruned"] >= 1
    assert heal_res["cycles_broken"] >= 1

    # Post-check validation
    val_after = bot.validate(path=str(tmp_path))
    assert val_after["validation"]["valid"] is True


def test_bot_bitemporal_invalidation(tmp_path: Path):
    """Test that invalidating a node or edge marks valid_to and links SUPERSEDES."""
    bot = AgentGraphBot(cwd=tmp_path)
    graph = {
        "schema_version": "hath0r.agentgraph/1",
        "graph_id": "test-bitemp",
        "nodes": [
            {"id": "rule:old-rule", "plane": "rules", "type": "rule_policy", "label": "Old Rule", "is_current": True},
            {"id": "rule:new-rule", "plane": "rules", "type": "rule_policy", "label": "New Rule", "is_current": True},
        ],
        "edges": [],
    }
    bot.save_graph(graph, target_path=str(tmp_path))

    inv_res = bot.invalidate_bitemporal(
        target_id="rule:old-rule",
        superseding_id="rule:new-rule",
        path=str(tmp_path),
    )
    assert inv_res["success"] is True

    loaded = bot.load_graph(target_path=str(tmp_path))
    old_node = next(n for n in loaded["nodes"] if n["id"] == "rule:old-rule")
    assert old_node["is_current"] is False
    assert old_node.get("valid_to") is not None

    supersedes_edge = next(e for e in loaded["edges"] if e.get("relation") == "SUPERSEDES")
    assert supersedes_edge["source"] == "rule:new-rule"
    assert supersedes_edge["target"] == "rule:old-rule"


def test_bot_cross_repo_audit(tmp_path: Path):
    """Test cross-repo rule alignment audit across multiple workspace folders."""
    # Repo 1: fully compliant
    repo1 = tmp_path / "repo1"
    repo1.mkdir()
    (repo1 / "AGENTS.md").write_text("CR-CLI-ENTRY-001\nCR-BRANCH-GOV-001\nCR-DOCKER-HATH0R-GROUP-001\nCR-HATH0R-ROOT-001", encoding="utf-8")

    # Repo 2: missing some rules
    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    (repo2 / "AGENTS.md").write_text("CR-CLI-ENTRY-001\n", encoding="utf-8")

    bot = AgentGraphBot(cwd=repo1)
    audit = bot.audit_cross_repo(base_dir=str(tmp_path))

    assert audit["success"] is True
    assert "repo1" in audit["repos_scanned"]
    assert "repo2" in audit["repos_scanned"]
    assert len(audit["missing_by_repo"]["repo2"]) > 0
    assert audit["alignment_score"] > 0
    assert len(audit["recommendations"]) >= 1
