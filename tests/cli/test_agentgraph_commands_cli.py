"""Text-mode CLI tests for `hath0r agentgraph` with AgentGraphBot mocked."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

import hath0r_cli.bots.agentgraph_owl as agentgraph_owl
import hath0r_cli.commands.agentgraph as agentgraph_cmd
from hath0r_cli.cli import main
from tests.fakebot import Seq, patch_bot

STATUS = {
    "success": True,
    "graph_id": "g1",
    "snapshot_path": "/s.json",
    "status": {"planes": {"rules": 2}, "edge_types": {"GOVERNS": 1}, "total_nodes": 2, "total_edges": 1},
}
SYNC = {"sources_scanned": 3, "nodes_indexed": 2, "edges_indexed": 1}
VALID = {"valid": True, "nodes_validated": 2, "edges_validated": 1, "warnings": ["unlinked ref"], "errors": []}

CASES = [
    (["status"], [STATUS, {**STATUS, "snapshot_path": None, "status": {"total_nodes": 0, "total_edges": 0}}],
     ["Cognitive Planes", "No saved snapshot"]),
    (["query", "deploy", "--plane", "rules", "--all"],
     [{"success": True, "query": {"results_count": 1, "results": [
         {"score": 0.9, "plane": "rules", "type": "rule", "label": "L", "id": "r1", "snippet": "a\nb"}]}},
      {"success": True, "query": {"results_count": 0, "results": []}}],
     ["Search Results", "No matching nodes"]),
    (["validate", "--strict"], [{"success": True, "validation": VALID},
                                {"success": True, "validation": {"valid": False, "errors": ["cycle"]}}],
     ["Validation PASSED", "cycle"]),
    (["sync", "--dry-run"], [{"success": True, "sync": SYNC, "snapshot_file": "/s.json"}], ["Sync Completed"]),
    (["export", "--format", "json"], [STATUS], ["planes"]),
    (["route", "--role", "developer", "--tool", "git"],
     [{"success": True, "routing": {"role": "developer", "role_found": True, "inherited_roles": ["base"],
                                    "authorized_tools": ["git"], "forbidden_tools": ["rm"],
                                    "restricted_actions": ["push"], "tool_authorized": True}},
      {"success": True, "routing": {"role": "guest", "authorized_tools": [], "tool_authorized": False}}],
     ["AUTHORIZED for role", "NOT AUTHORIZED"]),
    (["bot", "--cross-repo"],
     [{"subcommand": "cross_repo", "alignment_score": 90, "repos_scanned": ["a"], "recommendations": ["align"]}],
     ["Cross-Repository Alignment"]),
    (["bot", "--heal"], [{"subcommand": "heal", "orphans_pruned": 1, "cycles_broken": 0, "remaining_edges": 3}],
     ["Healing Completed"]),
    (["bot", "--audit"], [{"success": True, "health": "healthy", "validation": {"valid": True}}], ["Report"]),
    (["migrate", "--all"], [{"subcommand": "migrate_all", "migrated_count": 2,
                             "results": [{"success": True, "repo": "a"}, {"success": False, "repo": "b"}]}],
     ["Batch Migration Completed"]),
    (["migrate", "--path", "."], [{"success": True, "repo": "cli", "path": "."}], ["Migration for cli"]),
    (["migrate"], [{"success": False, "repo": "cli"}], ["Migration for cli"]),
]


@pytest.mark.parametrize("args, results, fragments", CASES, ids=[" ".join(c[0][:2]) for c in CASES])
def test_agentgraph_commands_text(monkeypatch, args, results, fragments):
    for result, fragment in zip(results, fragments):
        patch_bot(monkeypatch, agentgraph_cmd, "AgentGraphBot", result)
        res = CliRunner().invoke(main, ["-o", "text", "agentgraph", *args])
        assert res.exception is None or isinstance(res.exception, SystemExit), res.output
        assert fragment in res.output, (args, result, res.output)


def test_agentgraph_bot_run_loop(monkeypatch):
    patch_bot(
        monkeypatch,
        agentgraph_cmd,
        "AgentGraphBot",
        Seq([{"sync": SYNC}, {"total_healed": 2}, {"success": True, "health": "healthy"}]),
    )
    res = CliRunner().invoke(main, ["-o", "text", "agentgraph", "bot", "--run"])
    assert res.exit_code == 0, res.output
    assert "Repaired 2 issues" in res.output


def test_agentgraph_validate_with_owl(monkeypatch):
    class Reasoner:
        def __init__(self, ok):
            self.ok = ok

        def validate_ontology_consistency(self):
            return {"is_valid": self.ok, "conflicts": [] if self.ok else [{"message": "disjoint classes"}]}

    for ok, fragment in ((True, "OWL Reasoner"), (False, "OWL Contradiction")):
        patch_bot(monkeypatch, agentgraph_cmd, "AgentGraphBot", {"success": True, "validation": {**VALID, "errors": []}})
        monkeypatch.setattr(agentgraph_owl, "agentgraph_owl_reasoner", Reasoner(ok))
        res = CliRunner().invoke(main, ["-o", "text", "agentgraph", "validate", "--owl"])
        assert fragment in res.output, res.output


def test_agentgraph_sync_persists_turtle(monkeypatch, tmp_path):
    class Exporter:
        def sync_to_file(self):
            return tmp_path / "snapshot.ttl"

        def export_ttl(self, output_format):
            return f"@prefix ag: <{output_format}> ."

    patch_bot(monkeypatch, agentgraph_cmd, "AgentGraphBot", {"success": True, "sync": SYNC})
    monkeypatch.setattr(agentgraph_owl, "agentgraph_owl_exporter", Exporter())
    res = CliRunner().invoke(main, ["-o", "text", "agentgraph", "sync"])
    assert "Turtle saved" in res.output
    res = CliRunner().invoke(main, ["-o", "text", "agentgraph", "export"])
    assert "@prefix" in res.output
