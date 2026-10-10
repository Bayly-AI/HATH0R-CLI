"""SPARQL Query Engine & Ray-MCP Semantic Query Endpoint."""

from __future__ import annotations

from typing import Any, Dict

from .agentgraph_owl import agentgraph_owl_exporter


class SPARQLEngine:
    """SPARQL Graph Query Engine over AgentGraph OWL Ontology."""

    def __init__(self) -> None:
        """Initialize SPARQL Query Engine with default RDF graph context."""
        # Stateless SPARQL query executor over AgentGraph OWL exporter graph

    def query(self, sparql_query_str: str) -> Dict[str, Any]:
        """Execute SPARQL query string against AgentGraph RDF Graph."""
        try:
            g = agentgraph_owl_exporter.build_rdf_graph()
            qres = g.query(sparql_query_str)

            results = []
            vars_list = [str(v) for v in qres.vars] if hasattr(qres, "vars") and qres.vars else []

            for row in qres:
                if isinstance(row, bool):
                    return {
                        "status": "success",
                        "query_type": "ASK",
                        "boolean_result": row,
                    }

                row_dict: Dict[str, Any] = {}
                if vars_list:
                    for v in vars_list:
                        val = getattr(row, v, None)
                        row_dict[v] = str(val) if val is not None else ""
                else:
                    row_dict = {"result": [str(item) for item in row]}
                results.append(row_dict)

            return {
                "status": "success",
                "query_type": "SELECT",
                "vars": vars_list,
                "result_count": len(results),
                "results": results,
            }
        except Exception as err:
            return {
                "status": "error",
                "message": f"SPARQL query execution failed: {err}",
            }


sparql_engine = SPARQLEngine()
