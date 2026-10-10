"""AgentGraph OWL export must handle arbitrary node ids and the reasoner must use the graph namespace (#392)."""

from __future__ import annotations

import json

from hath0r_cli.bots.agentgraph_owl import AgentGraphOWLExporter, AgentGraphOWLReasoner


def test_export_handles_ids_with_special_characters(tmp_path) -> None:
    exporter = AgentGraphOWLExporter(root_path=tmp_path)
    snap = {
        "nodes": [{"id": "role:control_tower_&_forge_(`is_control_tower:_true`)", "type": "role"}],
        "edges": [],
    }
    g = exporter.build_rdf_graph(snap)
    assert "control_tower" in g.serialize(format="turtle")


def test_reasoner_detects_cycles_in_https_namespace(tmp_path) -> None:
    snap_dir = tmp_path / ".hath0r" / "agentgraph"
    snap_dir.mkdir(parents=True)
    (snap_dir / "snapshot.json").write_text(
        json.dumps(
            {
                "nodes": [{"id": "a", "type": "rule"}, {"id": "b", "type": "rule"}],
                "edges": [
                    {"source": "a", "target": "b", "relation": "governs"},
                    {"source": "b", "target": "a", "relation": "governs"},
                ],
            }
        ),
        encoding="utf-8",
    )
    res = AgentGraphOWLReasoner(AgentGraphOWLExporter(root_path=tmp_path)).validate_ontology_consistency()
    assert res["is_valid"] is False
    assert res["conflicts_count"] >= 1
