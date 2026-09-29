"""ContextManagerBot: Query and inspect dynamic ContextGraph runtime session state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class ContextManagerBot:
    """Bot to query, filter, and inspect ContextGraph runtime state."""

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self.context_dirs = [
            self.cwd / ".hath0r" / "context",
            self.cwd / ".hath0r" / "state" / "context",
        ]

    def _find_context_file(self, session_id: Optional[str] = None, file_path: Optional[str] = None) -> Optional[Path]:
        if file_path:
            p = Path(file_path).expanduser().resolve()
            return p if p.is_file() else None

        for cdir in self.context_dirs:
            if not cdir.is_dir():
                continue
            if session_id:
                cand = cdir / f"{session_id}.json"
                if cand.is_file():
                    return cand
            # Check standard names
            for name in ("session.json", "latest.json", "session_init.json"):
                cand = cdir / name
                if cand.is_file():
                    return cand
            # Check any json
            json_files = sorted(cdir.glob("*.json"))
            if json_files:
                return json_files[0]
        return None

    def query_context(
        self,
        session_id: Optional[str] = None,
        node_type: Optional[str] = None,
        filter_query: Optional[str] = None,
        file_path: Optional[str] = None,
        depth: int = 1,
    ) -> Dict[str, Any]:
        """Query and filter runtime context graph."""
        target_file = self._find_context_file(session_id=session_id, file_path=file_path)

        if not target_file or not target_file.is_file():
            return {
                "success": True,
                "session_id": session_id or "none",
                "active_subagent_id": None,
                "file": None,
                "nodes": [],
                "edges": [],
                "summary": {
                    "total_nodes": 0,
                    "subagents": 0,
                    "tool_invocations": 0,
                    "jev_guards": 0,
                },
                "message": "No active context graph session file found.",
            }

        try:
            raw_data = json.loads(target_file.read_text(encoding="utf-8"))
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to parse context graph file {target_file}: {e}",
            }

        all_nodes: List[Dict[str, Any]] = raw_data.get("nodes", [])
        all_edges: List[Dict[str, Any]] = raw_data.get("edges", [])
        active_subagent_id = raw_data.get("active_subagent_id")
        actual_session_id = raw_data.get("session_id", session_id or "unknown")

        # Filter nodes
        matched_nodes: List[Dict[str, Any]] = []
        for n in all_nodes:
            ntype = n.get("type", "")
            nlabel = n.get("label", "")
            nid = n.get("id", "")

            if node_type and ntype != node_type:
                continue

            if filter_query:
                q = filter_query.lower()
                matches_q = (
                    q in nid.lower()
                    or q in nlabel.lower()
                    or q in ntype.lower()
                    or any(q in str(v).lower() for v in n.get("properties", {}).values())
                )
                if not matches_q:
                    continue

            matched_nodes.append(n)

        # Neighborhood / Connected Edge Traversal if requested
        matched_ids: Set[str] = {n.get("id") for n in matched_nodes if n.get("id")}
        connected_edges: List[Dict[str, Any]] = []
        traversed_node_ids: Set[str] = set(matched_ids)

        if matched_ids:
            for _ in range(depth):
                new_ids: Set[str] = set()
                for edge in all_edges:
                    src = edge.get("source")
                    tgt = edge.get("target")
                    if src in traversed_node_ids or tgt in traversed_node_ids:
                        if edge not in connected_edges:
                            connected_edges.append(edge)
                        if src:
                            new_ids.add(src)
                        if tgt:
                            new_ids.add(tgt)
                traversed_node_ids.update(new_ids)

        # Final node list includes matched nodes and immediate traversed neighbors
        node_lookup = {n.get("id"): n for n in all_nodes if n.get("id")}
        final_nodes = [node_lookup[nid] for nid in traversed_node_ids if nid in node_lookup]

        subagents_count = sum(1 for n in final_nodes if n.get("type") in ("agent", "subagent"))
        tools_count = sum(1 for n in final_nodes if n.get("type") == "tool_invocation")
        jev_count = sum(1 for n in final_nodes if n.get("type") == "jev_guard")

        return {
            "success": True,
            "session_id": actual_session_id,
            "active_subagent_id": active_subagent_id,
            "file": str(target_file),
            "nodes": final_nodes,
            "edges": connected_edges,
            "summary": {
                "total_nodes": len(final_nodes),
                "subagents": subagents_count,
                "tool_invocations": tools_count,
                "jev_guards": jev_count,
            },
        }
