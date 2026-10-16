"""MemoryManagerBot: Manage canonical Local Memory Space and semantic memory graphs."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class MemoryManagerBot:
    """Bot to manage the Canonical Local Memory Space and Semantic Memory Graphs."""

    CANONICAL_SEED_NODE_IDS: Set[str] = {
        "rule:cr-cli-entry-001",
        "rule:cr-bai-001",
        "rule:cr-memory-compound-001",
        "concept:tri-graph",
    }

    GENERIC_CLUSTER_TAGS: Set[str] = {
        "compounded",
        "episode",
        "decision",
        "fact",
        "topic",
        "rule",
        "concept",
        "insight",
        "reflection",
        "synthesized",
    }

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = (cwd or Path.cwd()).resolve()
        self.memory_dir = self.cwd / ".hath0r" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_seed_graph() -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "schema_version": "1.0.0",
            "graph_id": "canonical-memory-space",
            "updated_at": now,
            "nodes": [
                {
                    "id": "rule:cr-cli-entry-001",
                    "type": "rule",
                    "label": "Start with CLI Rule",
                    "content": "Always start with hath0r operator CLI before inventing ad-hoc actions.",
                    "importance": 1.0,
                    "tags": ["rule", "governance", "cli"],
                    "is_current": True,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "rule:cr-bai-001",
                    "type": "rule",
                    "label": "Promotion Path Policy",
                    "content": "Promotion order: local -> development -> testing -> staging -> master.",
                    "importance": 1.0,
                    "tags": ["rule", "governance", "ci"],
                    "is_current": True,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "rule:cr-memory-compound-001",
                    "type": "rule",
                    "label": "Mandatory MemoryGraph Compounding Rule",
                    "content": (
                        "Every project repo must maintain .hath0r/memory/graph.json and every task must "
                        "compound knowledge prior to announcing complete."
                    ),
                    "importance": 1.0,
                    "tags": ["rule", "governance", "memorygraph", "cr-memory-compound-001"],
                    "is_current": True,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "concept:tri-graph",
                    "type": "concept",
                    "label": "Tri-Graph Substrate",
                    "content": "Three-layer cognitive graph architecture: KnowledgeGraph, ContextGraph, MemoryGraph.",
                    "importance": 0.9,
                    "tags": ["architecture", "substrate", "tri-graph"],
                    "is_current": True,
                    "created_at": now,
                    "updated_at": now,
                },
            ],
            "edges": [
                {
                    "source": "rule:cr-cli-entry-001",
                    "target": "concept:tri-graph",
                    "relation": "ENFORCES",
                    "weight": 1.0,
                    "is_current": True,
                },
                {
                    "source": "rule:cr-memory-compound-001",
                    "target": "concept:tri-graph",
                    "relation": "ENFORCES",
                    "weight": 1.0,
                    "is_current": True,
                },
            ],
        }

    def _load_or_seed_graph(self) -> Dict[str, Any]:
        graph_file = self.memory_dir / "graph.json"
        seed = self._default_seed_graph()
        if not graph_file.exists():
            return seed

        try:
            gdata = json.loads(graph_file.read_text(encoding="utf-8"))
            if not isinstance(gdata, dict):
                return seed
        except Exception:
            return seed

        nodes: List[Dict[str, Any]] = list(gdata.get("nodes", []))
        edges: List[Dict[str, Any]] = list(gdata.get("edges", []))
        existing_ids = {str(n.get("id")) for n in nodes if n.get("id")}

        for snode in seed["nodes"]:
            if snode["id"] not in existing_ids:
                nodes.append(snode)
                existing_ids.add(snode["id"])

        existing_edge_keys = {(e.get("source"), e.get("target"), e.get("relation")) for e in edges}
        for sedge in seed["edges"]:
            ekey = (sedge["source"], sedge["target"], sedge["relation"])
            if ekey not in existing_edge_keys:
                edges.append(sedge)
                existing_edge_keys.add(ekey)

        gdata["schema_version"] = gdata.get("schema_version", "1.0.0")
        gdata["graph_id"] = gdata.get("graph_id", "canonical-memory-space")
        gdata["nodes"] = nodes
        gdata["edges"] = edges
        return gdata

    def _save_graph(self, gdata: Dict[str, Any]) -> Path:
        graph_file = self.memory_dir / "graph.json"
        gdata["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        graph_file.write_text(json.dumps(gdata, indent=2), encoding="utf-8")
        return graph_file

    def initialize_memory(self, dry_run: bool = False) -> Dict[str, Any]:
        """Initialize the core Hath0r memory spaces."""
        core_file = self.memory_dir / "core_rules.md"
        arch_file = self.memory_dir / "architecture.md"
        graph_file = self.memory_dir / "graph.json"

        core_content = (
            "# Core Hath0r Rules\n"
            "1. CLI-First (CR-CLI-ENTRY-001): Always start with the CLI capabilities before improvising.\n"
            "2. Memory Compounding (CR-MEMORY-COMPOUND-001): Every task must compound knowledge into .hath0r/memory/graph.json prior to announcing complete.\n"
            "3. Bots not Daemons: Background tasks are bots/factories.\n"
            "4. Hyper-Context: Always traverse the defined context paths (playbooks, procedures).\n"
            "5. Promotion Path: local -> development -> testing -> staging -> master.\n"
        )

        arch_content = (
            "# Canonical Architecture\n"
            "The HATH0R-CLI repository acts as the OpenSource Control Tower.\n"
            "Agents orienting to any Hath0r app MUST read this Local Memory Space first "
            "and compound task learnings into `.hath0r/memory/graph.json` prior to completion.\n"
        )

        gdata = self._load_or_seed_graph()

        if not dry_run:
            if not core_file.exists():
                core_file.write_text(core_content, encoding="utf-8")
            if not arch_file.exists():
                arch_file.write_text(arch_content, encoding="utf-8")
            self._save_graph(gdata)

        return {
            "success": True,
            "message": "Initialized core memory spaces.",
            "files": [str(core_file), str(arch_file), str(graph_file)],
            "nodes_count": len(gdata.get("nodes", [])),
            "edges_count": len(gdata.get("edges", [])),
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
        """Update or create a specific memory topic and sync into graph.json."""
        actual_topic = "core_rules" if topic in ("rules", "core") else topic
        target_file = self.memory_dir / f"{actual_topic}.md"
        if not dry_run:
            target_file.write_text(content, encoding="utf-8")
            gdata = self._load_or_seed_graph()
            now = datetime.now(timezone.utc).isoformat()
            topic_id = f"topic:{actual_topic}"
            first_line = content.splitlines()[0].lstrip("# ").strip() if content.splitlines() else actual_topic
            topic_node = {
                "id": topic_id,
                "type": "topic",
                "label": first_line[:120] or actual_topic,
                "content": content,
                "importance": 0.8,
                "tags": ["topic", actual_topic, "compounded"],
                "is_current": True,
                "created_at": now,
                "updated_at": now,
            }
            nodes = [n for n in gdata.get("nodes", []) if n.get("id") != topic_id]
            nodes.append(topic_node)
            gdata["nodes"] = nodes
            edges = list(gdata.get("edges", []))
            if not any(e.get("source") == topic_id and e.get("target") == "concept:tri-graph" for e in edges):
                edges.append(
                    {
                        "source": topic_id,
                        "target": "concept:tri-graph",
                        "relation": "RELATES_TO",
                        "weight": 1.0,
                        "is_current": True,
                    }
                )
            gdata["edges"] = edges
            self._save_graph(gdata)

        return {"success": True, "message": f"Updated memory topic '{topic}'.", "file": str(target_file)}

    def compound_memory(
        self,
        label: str,
        content: str,
        node_type: str = "episode",
        node_id: Optional[str] = None,
        importance: float = 0.8,
        tags: Optional[List[str]] = None,
        relates_to: Optional[List[str]] = None,
        relation: str = "DERIVES_FROM",
        supersedes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        sync_agentgraph: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Compound a structured knowledge node and relational edges into .hath0r/memory/graph.json."""
        now = datetime.now(timezone.utc).isoformat()
        slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48] or "task"
        resolved_type = (node_type or "episode").lower()
        resolved_id = node_id or f"{resolved_type}:{slug}"
        clean_tags = [t.strip().lower() for t in (tags or []) if t and t.strip()]
        resolved_tags = list(dict.fromkeys(clean_tags + [resolved_type, "compounded"]))

        node_entry: Dict[str, Any] = {
            "id": resolved_id,
            "type": resolved_type,
            "label": label,
            "content": content,
            "importance": max(0.0, min(1.0, float(importance))),
            "tags": resolved_tags,
            "valid_from": now,
            "valid_to": None,
            "is_current": True,
            "created_at": now,
            "updated_at": now,
            "metadata": metadata or {},
        }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "message": f"[DRY-RUN] Would compound node '{resolved_id}' into .hath0r/memory/graph.json",
                "node": node_entry,
                "edges_added": [],
                "reflection": {"insights_generated": 0, "insights": []},
                "agentgraph_synced": False,
            }

        self.initialize_memory(dry_run=False)
        gdata = self._load_or_seed_graph()
        nodes: List[Dict[str, Any]] = list(gdata.get("nodes", []))
        edges: List[Dict[str, Any]] = list(gdata.get("edges", []))

        # Upsert node
        replaced = False
        for idx, existing in enumerate(nodes):
            if existing.get("id") == resolved_id:
                node_entry["created_at"] = existing.get("created_at", now)
                nodes[idx] = node_entry
                replaced = True
                break
        if not replaced:
            nodes.append(node_entry)

        existing_ids = {str(n.get("id")) for n in nodes if n.get("id")}
        edges_added: List[Dict[str, Any]] = []
        existing_edge_keys = {(e.get("source"), e.get("target"), e.get("relation")) for e in edges}

        # Handle superseding bitemporal invalidation
        if supersedes and supersedes in existing_ids and supersedes != resolved_id:
            for n in nodes:
                if n.get("id") == supersedes:
                    n["is_current"] = False
                    n["valid_to"] = now
            sup_edge = {
                "source": resolved_id,
                "target": supersedes,
                "relation": "SUPERSEDES",
                "weight": 1.0,
                "valid_from": now,
                "is_current": True,
            }
            if (resolved_id, supersedes, "SUPERSEDES") not in existing_edge_keys:
                edges.append(sup_edge)
                existing_edge_keys.add((resolved_id, supersedes, "SUPERSEDES"))
                edges_added.append(sup_edge)

        targets = [t.strip() for t in (relates_to or []) if t and t.strip()]
        if not targets and "concept:tri-graph" in existing_ids and resolved_id != "concept:tri-graph":
            targets.append("concept:tri-graph")

        rel_upper = (relation or "DERIVES_FROM").upper()
        for tgt in targets:
            if tgt in existing_ids and tgt != resolved_id:
                ekey = (resolved_id, tgt, rel_upper)
                if ekey not in existing_edge_keys:
                    rel_edge = {
                        "source": resolved_id,
                        "target": tgt,
                        "relation": rel_upper,
                        "weight": 1.0,
                        "valid_from": now,
                        "is_current": True,
                    }
                    edges.append(rel_edge)
                    existing_edge_keys.add(ekey)
                    edges_added.append(rel_edge)

        gdata["nodes"] = nodes
        gdata["edges"] = edges
        graph_file = self._save_graph(gdata)

        # Run autonomous reflection consolidation
        reflection_res = self.reflect_memory(dry_run=False)

        # Synchronize AgentGraph memory plane
        ag_synced = False
        if sync_agentgraph:
            try:
                from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

                ag_res = AgentGraphBot(cwd=self.cwd).sync(persist=True, dry_run=False)
                ag_synced = bool(ag_res.get("success", False))
            except Exception:
                ag_synced = False

        return {
            "success": True,
            "message": f"Compounded '{resolved_id}' into MemoryGraph ({graph_file}).",
            "graph_file": str(graph_file),
            "node": node_entry,
            "edges_added": edges_added,
            "reflection": reflection_res,
            "agentgraph_synced": ag_synced,
        }

    def reflect_memory(
        self,
        cluster_threshold: int = 2,
        max_insights: int = 5,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Synthesize higher-order insight nodes from episodic/decision clusters sharing semantic tags."""
        gdata = self._load_or_seed_graph()
        nodes: List[Dict[str, Any]] = list(gdata.get("nodes", []))
        edges: List[Dict[str, Any]] = list(gdata.get("edges", []))

        episodes = [
            n
            for n in nodes
            if n.get("type") in ("episode", "decision", "fact") and n.get("is_current", True)
        ]
        tag_clusters: Dict[str, List[Dict[str, Any]]] = {}
        for ep in episodes:
            for raw_tag in ep.get("tags", []):
                tag = str(raw_tag).lower().strip()
                if tag and tag not in self.GENERIC_CLUSTER_TAGS:
                    tag_clusters.setdefault(tag, []).append(ep)

        now = datetime.now(timezone.utc).isoformat()
        existing_ids = {str(n.get("id")) for n in nodes if n.get("id")}
        existing_edge_keys = {(e.get("source"), e.get("target"), e.get("relation")) for e in edges}
        new_insights: List[Dict[str, Any]] = []

        for tag, cluster in tag_clusters.items():
            if len(cluster) < cluster_threshold:
                continue
            insight_id = f"insight:{tag}"
            if insight_id in existing_ids:
                continue

            all_text = " ".join(f"{n.get('label', '')} {n.get('content', '')}" for n in cluster)
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", all_text)]
            top_terms = [w for w, _ in Counter(words).most_common(4)]
            avg_imp = sum(float(n.get("importance", 0.7)) for n in cluster) / len(cluster)

            insight_node: Dict[str, Any] = {
                "id": insight_id,
                "type": "insight",
                "label": f"Synthesized Insight on {tag}",
                "content": (
                    f"Consolidated from {len(cluster)} memory nodes tagged '{tag}'. "
                    f"Recurring themes: {', '.join(top_terms)}. "
                    f"Latest context: {str(cluster[-1].get('content', ''))[:160]}"
                ),
                "importance": min(1.0, round(avg_imp + 0.15, 2)),
                "tags": [tag, "insight", "reflection", "compounded"],
                "valid_from": now,
                "is_current": True,
                "created_at": now,
                "updated_at": now,
                "metadata": {"constituent_count": len(cluster), "source_tag": tag},
            }
            nodes.append(insight_node)
            existing_ids.add(insight_id)
            new_insights.append(insight_node)

            for src_node in cluster:
                src_id = str(src_node.get("id", ""))
                ekey = (insight_id, src_id, "DERIVES_FROM")
                if src_id and ekey not in existing_edge_keys:
                    edges.append(
                        {
                            "source": insight_id,
                            "target": src_id,
                            "relation": "DERIVES_FROM",
                            "weight": 1.0,
                            "valid_from": now,
                            "is_current": True,
                        }
                    )
                    existing_edge_keys.add(ekey)

            if len(new_insights) >= max_insights:
                break

        if not dry_run and new_insights:
            gdata["nodes"] = nodes
            gdata["edges"] = edges
            self._save_graph(gdata)

        return {
            "success": True,
            "dry_run": dry_run,
            "insights_generated": len(new_insights),
            "insights": new_insights,
        }

    def verify_compounded(
        self,
        since: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify that .hath0r/memory/graph.json exists and contains compounded task knowledge."""
        graph_file = self.memory_dir / "graph.json"
        if not graph_file.is_file():
            return {
                "success": False,
                "compounded": False,
                "graph_exists": False,
                "total_nodes": 0,
                "total_edges": 0,
                "compounded_nodes_count": 0,
                "latest_node": None,
                "error": f"Missing MemoryGraph file at {graph_file}. Run 'hath0r memory init' and 'hath0r memory compound'.",
            }

        try:
            gdata = json.loads(graph_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "success": False,
                "compounded": False,
                "graph_exists": True,
                "total_nodes": 0,
                "total_edges": 0,
                "compounded_nodes_count": 0,
                "latest_node": None,
                "error": f"Corrupt MemoryGraph JSON at {graph_file}: {exc}",
            }

        nodes = list(gdata.get("nodes", []))
        edges = list(gdata.get("edges", []))
        compounded_nodes: List[Dict[str, Any]] = []

        for n in nodes:
            nid = str(n.get("id", ""))
            if not nid or nid in self.CANONICAL_SEED_NODE_IDS:
                continue
            updated = str(n.get("updated_at") or n.get("created_at") or "")
            if since and updated and updated < since:
                continue
            if task_id:
                haystack = f"{nid} {n.get('label', '')} {n.get('content', '')} {' '.join(n.get('tags', []))}".lower()
                if task_id.lower() not in haystack:
                    continue
            compounded_nodes.append(n)

        compounded_nodes.sort(key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""), reverse=True)
        is_compounded = len(compounded_nodes) > 0
        latest = compounded_nodes[0] if compounded_nodes else None

        return {
            "success": is_compounded,
            "compounded": is_compounded,
            "graph_exists": True,
            "graph_file": str(graph_file),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "compounded_nodes_count": len(compounded_nodes),
            "latest_node": latest,
            "error": (
                None
                if is_compounded
                else "CR-MEMORY-COMPOUND-001: No task knowledge compounded in .hath0r/memory/graph.json beyond static seeds. Run 'hath0r memory compound' prior to announcing complete."
            ),
        }

    def ensure_all_repos(
        self,
        root_dir: Optional[Path | str] = None,
        sync_agentgraph: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Discover all active repositories under root_dir and ensure .hath0r/memory/graph.json is provisioned and compounded."""
        base = Path(root_dir).resolve() if root_dir else Path("/Users/raybayly/Development")
        if not base.is_dir():
            base = self.cwd.parent

        skip_parts = {"node_modules", ".venv", "ARCHIVE", "archive", ".terraform", "__pycache__"}
        repo_paths: List[Path] = []

        if (base / ".git").exists():
            repo_paths.append(base)
        else:
            for git_entry in sorted(base.rglob(".git")):
                if any(p in git_entry.parts for p in skip_parts):
                    continue
                repo_paths.append(git_entry.parent)

        results: List[Dict[str, Any]] = []
        for rpath in repo_paths:
            rbot = MemoryManagerBot(cwd=rpath)
            slug = re.sub(r"[^a-z0-9]+", "-", rpath.name.lower()).strip("-") or "repo"
            summary = f"Repository '{rpath.name}' initialized with canonical .hath0r/memory/graph.json under CR-MEMORY-COMPOUND-001."
            for doc_candidate in (rpath / "README.md", rpath / "AGENTS.md"):
                if doc_candidate.is_file():
                    try:
                        lines = [
                            ln.strip()
                            for ln in doc_candidate.read_text(encoding="utf-8", errors="ignore").splitlines()
                            if ln.strip() and not ln.strip().startswith("#")
                        ]
                        if lines:
                            summary = f"{rpath.name}: {' '.join(lines[:3])[:360]}"
                            break
                    except Exception:
                        pass

            comp_res = rbot.compound_memory(
                node_id=f"fact:repo-{slug}-orientation",
                node_type="fact",
                label=f"{rpath.name} Repository Memory Orientation",
                content=summary,
                importance=0.85,
                tags=["orientation", "repository", slug, "cr-memory-compound-001"],
                relates_to=["concept:tri-graph", "rule:cr-memory-compound-001"],
                relation="RELATES_TO",
                sync_agentgraph=sync_agentgraph,
                dry_run=dry_run,
            )
            ver = rbot.verify_compounded() if not dry_run else {"compounded": True, "total_nodes": 5, "total_edges": 4}
            results.append(
                {
                    "repo": str(rpath.relative_to(base)) if rpath != base else rpath.name,
                    "path": str(rpath),
                    "memory_dir": str(rpath / ".hath0r" / "memory"),
                    "graph_file": str(rpath / ".hath0r" / "memory" / "graph.json"),
                    "compounded": ver.get("compounded", False),
                    "total_nodes": ver.get("total_nodes", 0),
                    "total_edges": ver.get("total_edges", 0),
                    "agentgraph_synced": comp_res.get("agentgraph_synced", False),
                }
            )

        return {
            "success": True,
            "dry_run": dry_run,
            "root_dir": str(base),
            "repos_count": len(results),
            "repos": results,
        }

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
