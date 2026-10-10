"""Unit & Integration Tests for Phase 2: OWL/RDF Exporter, OWL Reasoner, SPARQL Engine, CAG, and Hybrid Router."""

from __future__ import annotations

from click.testing import CliRunner

from hath0r_cli.bots.agentgraph_owl import AgentGraphOWLExporter, AgentGraphOWLReasoner
from hath0r_cli.bots.cag_engine import CAGEngine
from hath0r_cli.bots.cag_rag_router import HybridCAGRAGRouter
from hath0r_cli.bots.sparql_engine import SPARQLEngine
from hath0r_cli.cli import main


def test_agentgraph_owl_exporter():
    exporter = AgentGraphOWLExporter()
    g = exporter.build_rdf_graph()
    assert len(g) > 0

    ttl = exporter.export_ttl("turtle")
    assert "@prefix hath0r:" in ttl or "http://hath0r.dev/ontology/v1#" in ttl

    ttl_file = exporter.sync_to_file()
    assert ttl_file.exists()


def test_agentgraph_owl_reasoner():
    exporter = AgentGraphOWLExporter()
    reasoner = AgentGraphOWLReasoner(exporter)
    res = reasoner.validate_ontology_consistency()
    assert res["status"] in ["consistent", "inconsistent"]
    assert "total_triples" in res


def test_sparql_engine():
    engine = SPARQLEngine()
    query_str = """
        PREFIX hath0r: <http://hath0r.dev/ontology/v1#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?s ?label WHERE {
            ?s rdfs:label ?label .
        }
        LIMIT 5
    """
    res = engine.query(query_str)
    assert res["status"] == "success"
    assert res["query_type"] == "SELECT"
    assert len(res["results"]) > 0


def test_cag_engine(tmp_path):
    # Create sample files in tmp_path
    (tmp_path / "AGENTS.md").write_text("# Test Agents", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    cag = CAGEngine()
    res = cag.pack_context(workspace_root=tmp_path)
    assert res["status"] == "packed"
    assert res["total_files"] >= 2
    assert res["prompt_caching"]["type"] == "ephemeral"
    assert res["context_hash"] != ""


def test_hybrid_cag_rag_router(tmp_path):
    router = HybridCAGRAGRouter()

    # Query 1: Active workspace / code -> CAG
    cag_route = router.route_query("Where is main.py implemented in the codebase?", workspace_root=tmp_path)
    assert cag_route["route"] == "CAG"

    # Query 2: Historical archival PDF -> RAG
    rag_route = router.route_query("Search old career PDF documents in OneDrive", workspace_root=tmp_path)
    assert rag_route["route"] == "RAG"


def test_phase2_cli_commands():
    runner = CliRunner()

    res_export = runner.invoke(main, ["--output", "json", "agentgraph", "export", "--format", "turtle"])
    assert res_export.exit_code == 0

    res_val_owl = runner.invoke(main, ["--output", "json", "agentgraph", "validate", "--owl"])
    assert res_val_owl.exit_code == 0

    res_sparql = runner.invoke(main, ["--output", "json", "kb", "sparql", "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 3"])
    assert res_sparql.exit_code == 0

    res_smart = runner.invoke(main, ["--output", "json", "kb", "smart-query", "What rules govern CLI commands?"])
    assert res_smart.exit_code == 0

    res_cag_pack = runner.invoke(main, ["--output", "json", "context", "pack", "--cag"])
    assert res_cag_pack.exit_code == 0
