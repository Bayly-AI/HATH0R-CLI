"""MemoryManagerBot: Manage canonical Local Memory Space and semantic memory graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class MemoryManagerBot:
    """Bot to manage the Canonical Local Memory Space and Semantic Memory Graphs."""

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self.memory_dir = self.cwd / ".hath0r" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def initialize_memory(self, dry_run: bool = False) -> Dict[str, Any]:
        """Initialize the core Hath0r memory spaces."""
        core_file = self.memory_dir / "core_rules.md"
        arch_file = self.memory_dir / "architecture.md"
        graph_file = self.memory_dir / "graph.json"

        core_content = (
            "# Core Hath0r Rules\n"
            "1. CLI-First (CR-CLI-ENTRY-001): Always start with the CLI capabilities before improvising.\n"
            "2. Bots not Daemons: Background tasks are bots/factories.\n"
            "3. Hyper-Context: Always traverse the defined context paths (playbooks, procedures).\n"
            "4. Promotion Path: local -> development -> testing -> staging -> master.\n"
        )

        arch_content = (
            "# Canonical Architecture\n"
            "The HATH0R-CLI repository acts as the OpenSource Control Tower.\n"
            "Agents orienting to any Hath0r app MUST read this Local Memory Space first "
            "to align with current objectives.\n"
        )

        initial_graph = {
            "schema_version": "1.0.0",
            "graph_id": "canonical-memory-space",
            "nodes": [
                {
                    "id": "rule:cr-cli-entry-001",
                    "type": "rule",
                    "label": "Start with CLI Rule",
                    "content": "Always start with hath0r operator CLI before inventing ad-hoc actions.",
                    "importance": 1.0,
                    "tags": ["rule", "governance", "cli"],
                },
                {
                    "id": "rule:cr-bai-001",
                    "type": "rule",
                    "label": "Promotion Path Policy",
                    "content": "Promotion order: local -> development -> testing -> staging -> master.",
                    "importance": 1.0,
                    "tags": ["rule", "governance", "ci"],
                },
                {
                    "id": "concept:tri-graph",
                    "type": "concept",
                    "label": "Tri-Graph Substrate",
                    "content": "Three-layer cognitive graph architecture: KnowledgeGraph, ContextGraph, MemoryGraph.",
                    "importance": 0.9,
                    "tags": ["architecture", "substrate", "tri-graph"],
                },
            ],
            "edges": [
                {
                    "source": "rule:cr-cli-entry-001",
                    "target": "concept:tri-graph",
                    "relation": "ENFORCES",
                    "weight": 1.0,
                }
            ],
        }

        if not dry_run:
            core_file.write_text(core_content, encoding="utf-8")
            arch_file.write_text(arch_content, encoding="utf-8")
            if not graph_file.exists():
                graph_file.write_text(json.dumps(initial_graph, indent=2), encoding="utf-8")

        return {
            "success": True,
            "message": "Initialized core memory spaces.",
            "files": [str(core_file), str(arch_file), str(graph_file)],
        }

    def init_memory(self, dry_run: bool = False) -> Dict[str, Any]:
        """Alias for initialize_memory."""
        return self.initialize_memory(dry_run=dry_run)

    def read_topic(self, topic: str) -> Optional[str]:
        """Read content of a topic directly."""
        res = self.read_memory(topic)
        if res.get("success"):
            return res.get("content")
        return None

    def update_topic(self, topic: str, content: str, dry_run: bool = False) -> Dict[str, Any]:
        """Alias for update_memory."""
        return self.update_memory(topic=topic, content=content, dry_run=dry_run)

    def read_memory(self, topic: str) -> Dict[str, Any]:
        """Read a specific memory topic."""
        actual_topic = "core_rules" if topic in ("rules", "core") else topic
        target_file = self.memory_dir / f"{actual_topic}.md"
        if not target_file.exists():
            target_file = self.memory_dir / f"{topic}.md"
            if not target_file.exists():
                return {"success": False, "error": f"Memory topic '{topic}' does not exist."}

        return {"success": True, "topic": topic, "content": target_file.read_text(encoding="utf-8")}

    def update_memory(self, topic: str, content: str, dry_run: bool = False) -> Dict[str, Any]:
        """Update or create a specific memory topic."""
        actual_topic = "core_rules" if topic in ("rules", "core") else topic
        target_file = self.memory_dir / f"{actual_topic}.md"
        if not dry_run:
            target_file.write_text(content, encoding="utf-8")

        return {"success": True, "message": f"Updated memory topic '{topic}'.", "file": str(target_file)}

    def search_memory(
        self,
        query: str = "",
        node_type: Optional[str] = None,
        tag: Optional[str] = None,
        depth: int = 1,
        relation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search memory nodes and traverse connected relations."""
        graph_file = self.memory_dir / "graph.json"

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        if graph_file.exists():
            try:
                gdata = json.loads(graph_file.read_text(encoding="utf-8"))
                nodes = list(gdata.get("nodes", []))
                edges = list(gdata.get("edges", []))
            except Exception:
                pass

        # Also ingest markdown topic files into virtual nodes if not present
        existing_ids: Set[str] = {str(n["id"]) for n in nodes if n.get("id")}
        for md_file in self.memory_dir.glob("*.md"):
            topic_id = f"topic:{md_file.stem}"
            if topic_id not in existing_ids:
                try:
                    text = md_file.read_text(encoding="utf-8")
                    first_line = text.splitlines()[0] if text.splitlines() else md_file.stem
                    nodes.append(
                        {
                            "id": topic_id,
                            "type": "topic",
                            "label": first_line.lstrip("# ").strip(),
                            "content": text,
                            "importance": 0.8,
                            "tags": ["topic", md_file.stem],
                        }
                    )
                except Exception:
                    pass

        # Filter nodes
        matched_nodes: List[Dict[str, Any]] = []
        q = (query or "").lower().strip()

        for node in nodes:
            ntype = str(node.get("type", ""))
            nlabel = str(node.get("label", ""))
            ncontent = str(node.get("content", ""))
            nid = str(node.get("id", ""))
            ntags = [str(t).lower() for t in node.get("tags", [])]

            if node_type and ntype.lower() != node_type.lower():
                continue

            if tag and tag.lower() not in ntags:
                continue

            if q:
                match = q in nid.lower() or q in nlabel.lower() or q in ncontent.lower() or any(q in t for t in ntags)
                if not match:
                    continue

            matched_nodes.append(node)

        # Traverse edges for matched nodes
        matched_ids: Set[str] = {str(n["id"]) for n in matched_nodes if n.get("id")}
        connected_edges: List[Dict[str, Any]] = []
        traversed_node_ids: Set[str] = set(matched_ids)

        if matched_ids and depth > 0:
            for _ in range(depth):
                new_ids: Set[str] = set()
                for edge in edges:
                    src = edge.get("source")
                    tgt = edge.get("target")
                    rel = edge.get("relation", "")

                    if relation and rel.upper() != relation.upper():
                        continue

                    if src in traversed_node_ids or tgt in traversed_node_ids:
                        if edge not in connected_edges:
                            connected_edges.append(edge)
                        if src:
                            new_ids.add(src)
                        if tgt:
                            new_ids.add(tgt)
                traversed_node_ids.update(new_ids)

        node_lookup = {n.get("id"): n for n in nodes if n.get("id")}
        subgraph_nodes = [node_lookup[nid] for nid in traversed_node_ids if nid in node_lookup]

        return {
            "success": True,
            "query": query,
            "total_matches": len(matched_nodes),
            "nodes": matched_nodes,
            "edges": connected_edges,
            "subgraph": {
                "nodes": subgraph_nodes,
                "edges": connected_edges,
            },
        }
