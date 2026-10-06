"""AgentGraph OWL/RDF Exporter & Description Logic Reasoner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from rdflib import OWL, RDF, RDFS, Graph, Literal, Namespace, URIRef

HATH0R_NS = Namespace("http://hath0r.dev/ontology/v1#")


class AgentGraphOWLExporter:
    """W3C-compliant OWL/RDF Turtle (.ttl) Exporter for AgentGraph Cognitive Substrate."""

    def __init__(self, root_path: Optional[Path] = None) -> None:
        self.root_path = root_path or Path.cwd()
        self.snapshot_json = self.root_path / ".hath0r" / "agentgraph" / "snapshot.json"
        self.snapshot_ttl = self.root_path / ".hath0r" / "agentgraph" / "snapshot.ttl"

    def build_rdf_graph(self, snapshot_data: Optional[Dict[str, Any]] = None) -> Graph:
        """Build RDF/OWL Graph from AgentGraph snapshot data."""
        g = Graph()
        g.bind("hath0r", HATH0R_NS)
        g.bind("owl", OWL)
        g.bind("rdfs", RDFS)

        # Ontology header
        ontology_uri = URIRef(HATH0R_NS)
        g.add((ontology_uri, RDF.type, OWL.Ontology))
        g.add((ontology_uri, RDFS.label, Literal("Hath0r AgentGraph Policy Ontology")))

        # Define OWL Classes
        g.add((HATH0R_NS.Plane, RDF.type, OWL.Class))
        g.add((HATH0R_NS.Rule, RDF.type, OWL.Class))
        g.add((HATH0R_NS.AgentRole, RDF.type, OWL.Class))

        # Define OWL Properties
        g.add((HATH0R_NS.governs, RDF.type, OWL.ObjectProperty))
        g.add((HATH0R_NS.informs, RDF.type, OWL.ObjectProperty))
        g.add((HATH0R_NS.definesRole, RDF.type, OWL.ObjectProperty))

        # Load snapshot if available
        if snapshot_data is None and self.snapshot_json.exists():
            try:
                with open(self.snapshot_json, "r", encoding="utf-8") as f:
                    snapshot_data = json.load(f)
            except Exception:
                snapshot_data = {}

        snapshot_data = snapshot_data or {}
        nodes = snapshot_data.get("nodes", [
            {"id": "rule-001", "type": "rule", "label": "CR-CLI-FEATURE-STANDARD-001", "plane": "rules"},
            {"id": "rule-002", "type": "rule", "label": "CR-CLI-TECH-DEBT-001", "plane": "rules"},
            {"id": "role-forge", "type": "agent_role", "label": "Forge Controller", "plane": "memory"},
        ])
        edges = snapshot_data.get("edges", [
            {"source": "rule-001", "target": "role-forge", "relation": "governs"},
            {"source": "rule-002", "target": "role-forge", "relation": "informs"},
        ])

        # Add Nodes
        for node in nodes:
            node_uri = HATH0R_NS[node["id"]]
            node_type = node.get("type", "rule")
            if node_type == "rule":
                g.add((node_uri, RDF.type, HATH0R_NS.Rule))
            elif node_type in ["agent_role", "role"]:
                g.add((node_uri, RDF.type, HATH0R_NS.AgentRole))
            else:
                g.add((node_uri, RDF.type, HATH0R_NS.Plane))

            g.add((node_uri, RDFS.label, Literal(node.get("label", node["id"]))))
            if "plane" in node:
                g.add((node_uri, HATH0R_NS.inPlane, Literal(node["plane"])))

        # Add Edges
        for edge in edges:
            src_uri = HATH0R_NS[edge["source"]]
            target_uri = HATH0R_NS[edge["target"]]
            rel = edge.get("relation", "governs").lower()

            if rel == "governs":
                g.add((src_uri, HATH0R_NS.governs, target_uri))
            elif rel == "informs":
                g.add((src_uri, HATH0R_NS.informs, target_uri))
            elif rel == "defines_role":
                g.add((src_uri, HATH0R_NS.definesRole, target_uri))

        return g

    def export_ttl(self, output_format: str = "turtle") -> str:
        """Export RDF Graph to string in specified format (turtle or xml)."""
        g = self.build_rdf_graph()
        fmt = "turtle" if output_format == "turtle" else "xml"
        return g.serialize(format=fmt)

    def sync_to_file(self) -> Path:
        """Sync and save snapshot.ttl to .hath0r/agentgraph/snapshot.ttl."""
        self.snapshot_ttl.parent.mkdir(parents=True, exist_ok=True)
        ttl_content = self.export_ttl("turtle")
        with open(self.snapshot_ttl, "w", encoding="utf-8") as f:
            f.write(ttl_content)
        return self.snapshot_ttl


class AgentGraphOWLReasoner:
    """Description Logic Reasoner for detecting policy conflicts, cycles, and semantic contradictions."""

    def __init__(self, exporter: Optional[AgentGraphOWLExporter] = None) -> None:
        self.exporter = exporter or AgentGraphOWLExporter()

    def validate_ontology_consistency(self) -> Dict[str, Any]:
        """Execute automated Description Logic reasoning checks against active AgentGraph ontology."""
        g = self.exporter.build_rdf_graph()

        conflicts = []
        warnings = []

        # 1. Check cyclic governance (A governs B AND B governs A)
        cycle_query = """
            PREFIX hath0r: <http://hath0r.dev/ontology/v1#>
            SELECT ?a ?b WHERE {
                ?a hath0r:governs ?b .
                ?b hath0r:governs ?a .
            }
        """
        cycles = list(g.query(cycle_query))
        for row in cycles:
            conflicts.append({
                "type": "CyclicGovernanceContradiction",
                "source": str(row.a),
                "target": str(row.b),
                "message": f"Policy conflict: Cyclic governance detected between {row.a} and {row.b}.",
            })

        # 2. Check orphan rules (rules not governing or informing any entity)
        orphan_query = """
            PREFIX hath0r: <http://hath0r.dev/ontology/v1#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?r ?label WHERE {
                ?r a hath0r:Rule .
                ?r rdfs:label ?label .
                FILTER NOT EXISTS { ?r hath0r:governs ?x }
                FILTER NOT EXISTS { ?r hath0r:informs ?y }
            }
        """
        orphans = list(g.query(orphan_query))
        for row in orphans:
            warnings.append({
                "type": "OrphanPolicyWarning",
                "rule_uri": str(row.r),
                "label": str(row.label),
                "message": f"Rule '{row.label}' is unattached to any governance node.",
            })

        is_consistent = len(conflicts) == 0
        return {
            "status": "consistent" if is_consistent else "inconsistent",
            "is_valid": is_consistent,
            "total_triples": len(g),
            "conflicts_count": len(conflicts),
            "conflicts": conflicts,
            "warnings_count": len(warnings),
            "warnings": warnings,
            "reasoner_engine": "RDFLib-DL-SPARQL-Reasoner",
        }


agentgraph_owl_exporter = AgentGraphOWLExporter()
agentgraph_owl_reasoner = AgentGraphOWLReasoner(agentgraph_owl_exporter)
