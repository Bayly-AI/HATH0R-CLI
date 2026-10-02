"""AgentGraphBot: Unified management, synchronization, validation, and routing for AgentGraph."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class AgentGraphBot:
    """Autonomous bot and control engine for the Hath0r AgentGraph cognitive substrate."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()
        self.snapshot_dir = self.cwd / ".hath0r" / "agentgraph"
        self.snapshot_file = self.snapshot_dir / "snapshot.json"

    def _get_snapshot_path(self, target_path: Optional[str] = None) -> Path:
        if target_path:
            p = Path(target_path).resolve()
            if p.is_file():
                return p
            cand = p / ".hath0r" / "agentgraph" / "snapshot.json"
            if cand.is_file():
                return cand
            return cand
        return self.snapshot_file

    def load_graph(self, target_path: Optional[str] = None) -> Dict[str, Any]:
        """Load graph snapshot from disk or return default empty graph."""
        path = self._get_snapshot_path(target_path)
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "nodes" in data and "edges" in data:
                        return data
            except Exception:
                pass

        # Return default initialized graph structure
        return {
            "schema_version": "hath0r.agentgraph/1",
            "graph_id": f"agentgraph-{self.cwd.name}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nodes": [],
            "edges": [],
            "metadata": {"repo_root": str(self.cwd)},
        }

    def save_graph(self, graph_data: Dict[str, Any], target_path: Optional[str] = None) -> Path:
        """Save graph snapshot to disk."""
        path = self._get_snapshot_path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        graph_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        return path

    def get_status(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Inspect active Knowledge, Context, Memory, and Rules node/edge statistics."""
        graph = self.load_graph(path)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        planes_count: Dict[str, int] = defaultdict(int)
        node_types_count: Dict[str, int] = defaultdict(int)
        active_nodes = 0

        for n in nodes:
            plane = n.get("plane", "unknown")
            ntype = n.get("type", "unknown")
            planes_count[plane] += 1
            node_types_count[ntype] += 1
            if n.get("is_current", True):
                active_nodes += 1

        edge_types_count: Dict[str, int] = defaultdict(int)
        active_edges = 0
        for e in edges:
            etype = e.get("relation", e.get("type", "relates_to"))
            edge_types_count[etype] += 1
            if e.get("is_current", True):
                active_edges += 1

        snapshot_p = self._get_snapshot_path(path)
        exists = snapshot_p.is_file()

        return {
            "success": True,
            "subcommand": "status",
            "graph_id": graph.get("graph_id", "default"),
            "snapshot_path": str(snapshot_p) if exists else None,
            "exists_on_disk": exists,
            "status": {
                "total_nodes": len(nodes),
                "active_nodes": active_nodes,
                "total_edges": len(edges),
                "active_edges": active_edges,
                "planes": dict(planes_count),
                "node_types": dict(node_types_count),
                "edge_types": dict(edge_types_count),
            },
        }

    def query(
        self,
        query_str: str,
        top_k: int = 5,
        plane: Optional[str] = None,
        active_only: bool = True,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Hybrid search across the unified AgentGraph planes."""
        graph = self.load_graph(path)
        nodes = graph.get("nodes", [])

        # Filter by plane and temporal activity
        candidates = []
        for n in nodes:
            if plane and n.get("plane", "").lower() != plane.lower():
                continue
            if active_only and not n.get("is_current", True):
                continue
            candidates.append(n)

        if not candidates or not query_str.strip():
            return {
                "success": True,
                "subcommand": "query",
                "query": {
                    "query": query_str,
                    "plane_filter": plane,
                    "active_only": active_only,
                    "results_count": 0,
                    "results": [],
                },
            }

        # BM25-style keyword matching
        query_terms = [t.lower() for t in re.findall(r"\w+", query_str)]
        scored_results: List[Tuple[float, Dict[str, Any]]] = []

        doc_count = len(candidates)
        # Calculate Term frequencies
        doc_terms_list = []
        df: Dict[str, int] = defaultdict(int)

        for n in candidates:
            text = f"{n.get('id', '')} {n.get('label', '')} {n.get('content', '')} {' '.join(n.get('tags', []))}"
            words = [w.lower() for w in re.findall(r"\w+", text)]
            doc_terms_list.append(words)
            for word in set(words):
                df[word] += 1

        avgdl = sum(len(d) for d in doc_terms_list) / max(1, doc_count)
        k1 = 1.5
        b = 0.75

        for idx, n in enumerate(candidates):
            words = doc_terms_list[idx]
            doc_len = len(words)
            tf = Counter(words)
            score = 0.0

            for q in query_terms:
                if q in tf:
                    n_q = df[q]
                    idf = math.log(1.0 + (doc_count - n_q + 0.5) / (n_q + 0.5))
                    term_score = idf * (tf[q] * (k1 + 1.0)) / (tf[q] + k1 * (1.0 - b + b * (doc_len / avgdl)))
                    score += term_score

            if score > 0.0 or not query_terms:
                scored_results.append((round(score, 4), n))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_results = []
        for s, n in scored_results[:top_k]:
            content = n.get("content", "")
            snippet = content[:150] + "..." if len(content) > 150 else content
            top_results.append(
                {
                    "score": s,
                    "id": n.get("id"),
                    "plane": n.get("plane"),
                    "type": n.get("type"),
                    "label": n.get("label"),
                    "snippet": snippet,
                    "is_current": n.get("is_current", True),
                }
            )

        return {
            "success": True,
            "subcommand": "query",
            "query": {
                "query": query_str,
                "plane_filter": plane,
                "active_only": active_only,
                "results_count": len(top_results),
                "results": top_results,
            },
        }

    def validate(self, path: Optional[str] = None, strict: bool = False) -> Dict[str, Any]:
        """Perform deterministic rule constraint, cycle, and contradiction validation."""
        graph = self.load_graph(path)
        nodes = {n.get("id"): n for n in graph.get("nodes", [])}
        edges = graph.get("edges", [])

        errors: List[str] = []
        warnings: List[str] = []
        cycles_detected = 0
        contradictions_detected = 0

        # 1. Orphan edge detection
        for e in edges:
            src = e.get("source")
            tgt = e.get("target")
            rel = e.get("relation", e.get("type", "unknown"))
            if src not in nodes:
                errors.append(f"Orphan edge [{rel}]: Source node '{src}' does not exist in graph.")
            if tgt not in nodes:
                # Tools might not be explicit nodes if external
                if rel not in ("AUTHORIZES_TOOL", "RESTRICTED_BY"):
                    warnings.append(f"Edge [{rel}] target '{tgt}' is not declared as a graph node.")

        # 2. Cycle detection on INHERITS_FROM & SUPERSEDES
        adj_inheritance: Dict[str, List[str]] = defaultdict(list)
        for e in edges:
            rel = e.get("relation", e.get("type", ""))
            if rel in ("INHERITS_FROM", "SUPERSEDES"):
                adj_inheritance[e["source"]].append(e["target"])

        def has_cycle(start_node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(start_node)
            rec_stack.add(start_node)
            for neighbor in adj_inheritance[start_node]:
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(start_node)
            return False

        visited_nodes: Set[str] = set()
        for node_id in adj_inheritance:
            if node_id not in visited_nodes:
                rec_stack: Set[str] = set()
                if has_cycle(node_id, visited_nodes, rec_stack):
                    cycles_detected += 1
                    errors.append(f"Cyclic inheritance/superseding dependency detected involving role/rule '{node_id}'.")

        # 3. Contradiction & Constraint Verification
        # For each agent role, check if any restricted action clashes with allowed tools
        for node_id, n in nodes.items():
            if n.get("type") == "agent_role":
                permitted = set(n.get("properties", {}).get("permitted_tools", []))
                forbidden = set(n.get("properties", {}).get("forbidden_tools", []))
                collision = permitted.intersection(forbidden)
                if collision:
                    contradictions_detected += 1
                    errors.append(
                        f"Role '{node_id}' contains contradictory tools in both permitted and forbidden sets: {sorted(collision)}"
                    )

        # 4. Mandatory attribute check
        for node_id, n in nodes.items():
            if not n.get("label"):
                warnings.append(f"Node '{node_id}' is missing display label.")
            if not n.get("plane"):
                errors.append(f"Node '{node_id}' is missing required 'plane' attribute.")

        is_valid = len(errors) == 0 and (not strict or len(warnings) == 0)

        return {
            "success": is_valid,
            "subcommand": "validate",
            "validation": {
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
                "cycles_detected": cycles_detected,
                "contradictions_detected": contradictions_detected,
                "nodes_validated": len(nodes),
                "edges_validated": len(edges),
            },
        }

    def sync(
        self,
        path: Optional[str] = None,
        persist: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Ingest local repository rules, docs, and contracts into the AgentGraph."""
        root = Path(path).resolve() if path else self.cwd
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        sources_scanned = 0

        # 1. Ingest AGENTS.md (Root and Subsystems)
        agents_files = list(root.glob("**/AGENTS.md"))
        for af in agents_files:
            if ".git" in af.parts or ".venv" in af.parts:
                continue
            sources_scanned += 1
            try:
                content = af.read_text(encoding="utf-8")
                # Parse title / subsystem
                subsystem = af.parent.name if af.parent != root else "root"
                node_id = f"doc:agents-{subsystem}"
                nodes.append(
                    {
                        "id": node_id,
                        "plane": "knowledge",
                        "type": "knowledge_doc",
                        "label": f"AGENTS.md ({subsystem})",
                        "content": content[:1000],
                        "properties": {"path": str(af.relative_to(root)), "subsystem": subsystem},
                        "is_current": True,
                    }
                )

                # Extract roles if defined in markdown
                # Look for patterns like `Role | ...` or `### Role: <name>`
                role_matches = re.findall(r"(?:### Role:\s*([^\n]+)|\|\s*Role\s*\|\s*([^\|]+)\|)", content)
                for rm in role_matches:
                    rname = (rm[0] or rm[1]).strip()
                    if rname and len(rname) < 50:
                        rid = f"role:{rname.lower().replace(' ', '_')}"
                        nodes.append(
                            {
                                "id": rid,
                                "plane": "rules",
                                "type": "agent_role",
                                "label": rname,
                                "content": f"Agent role {rname} defined in {af.name}",
                                "properties": {
                                    "role_name": rname,
                                    "subsystem": subsystem,
                                    "permitted_tools": ["read_file", "search_code"],
                                    "forbidden_tools": [],
                                },
                                "is_current": True,
                            }
                        )
                        edges.append(
                            {
                                "source": node_id,
                                "target": rid,
                                "relation": "defines_role",
                                "is_current": True,
                            }
                        )
            except Exception:
                pass

        # 2. Ingest Rules & Invariants (rules.md, docs/rules/)
        rule_files = list(root.glob("**/rules.md")) + list(root.glob("docs/rules/*.md")) + list(root.glob("docs/governance/rules/*.md"))
        for rf in rule_files:
            if ".git" in rf.parts or ".venv" in rf.parts:
                continue
            sources_scanned += 1
            try:
                content = rf.read_text(encoding="utf-8")
                rid = f"rule:{rf.stem}"
                nodes.append(
                    {
                        "id": rid,
                        "plane": "rules",
                        "type": "rule_policy",
                        "label": f"Rule {rf.stem}",
                        "content": content[:1500],
                        "properties": {
                            "path": str(rf.relative_to(root)),
                            "priority": 4 if "cr-" in rf.name.lower() else 3,
                            "restricted_actions": [],
                        },
                        "is_current": True,
                    }
                )
            except Exception:
                pass

        # 3. Ingest Contracts (*.schema.json)
        contracts_dir = root / "contracts"
        if contracts_dir.is_dir():
            for cf in contracts_dir.glob("*.schema.json"):
                sources_scanned += 1
                try:
                    c_data = json.loads(cf.read_text(encoding="utf-8"))
                    cid = f"contract:{cf.name}"
                    nodes.append(
                        {
                            "id": cid,
                            "plane": "knowledge",
                            "type": "contract",
                            "label": c_data.get("title", cf.name),
                            "content": c_data.get("description", ""),
                            "properties": {
                                "schema_id": c_data.get("$id"),
                                "path": str(cf.relative_to(root)),
                            },
                            "is_current": True,
                        }
                    )
                except Exception:
                    pass

        # 4. Standard canonical base roles if none found
        role_ids = {n["id"] for n in nodes if n["plane"] == "rules" and n["type"] == "agent_role"}
        if "role:developer" not in role_ids:
            nodes.append(
                {
                    "id": "role:developer",
                    "plane": "rules",
                    "type": "agent_role",
                    "label": "Developer Agent",
                    "content": "Full access software engineer role permitted to run commands, edit files, and build.",
                    "properties": {
                        "role_name": "developer",
                        "permitted_tools": ["read_file", "write_file", "run_command", "search_code"],
                        "forbidden_tools": ["direct_push_master"],
                    },
                    "is_current": True,
                }
            )
        if "role:reader" not in role_ids:
            nodes.append(
                {
                    "id": "role:reader",
                    "plane": "rules",
                    "type": "agent_role",
                    "label": "Read-Only Agent",
                    "content": "Read-only inspection role strictly prohibited from modifying code or executing commands.",
                    "properties": {
                        "role_name": "reader",
                        "permitted_tools": ["read_file", "search_code"],
                        "forbidden_tools": ["run_command", "write_file", "git_push"],
                    },
                    "is_current": True,
                }
            )

        # Connect default rule governance edges
        for n in nodes:
            if n["type"] == "rule_policy":
                edges.append(
                    {
                        "source": n["id"],
                        "target": "role:developer",
                        "relation": "GOVERNS",
                        "is_current": True,
                    }
                )

        new_graph = {
            "schema_version": "hath0r.agentgraph/1",
            "graph_id": f"agentgraph-{root.name}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nodes": nodes,
            "edges": edges,
            "metadata": {"repo_root": str(root), "synced_sources": sources_scanned},
        }

        saved_path = None
        if persist and not dry_run:
            saved_path = self.save_graph(new_graph, path)

        return {
            "success": True,
            "subcommand": "sync",
            "dry_run": dry_run,
            "snapshot_file": str(saved_path) if saved_path else None,
            "sync": {
                "synced": True,
                "nodes_indexed": len(nodes),
                "edges_indexed": len(edges),
                "sources_scanned": sources_scanned,
            },
        }

    def route(
        self,
        role: str,
        task: Optional[str] = None,
        tool: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve active rule constraints, tool authorization, and RBAC for an agent role."""
        graph = self.load_graph(path)
        nodes = {n.get("id"): n for n in graph.get("nodes", [])}
        edges = graph.get("edges", [])

        # Match role id (e.g. 'role:developer' or 'developer')
        role_node_id = role if role.startswith("role:") else f"role:{role}"
        target_role_node = nodes.get(role_node_id)

        if not target_role_node:
            # Check by label
            for nid, n in nodes.items():
                if n.get("type") == "agent_role" and n.get("label", "").lower() == role.lower():
                    role_node_id = nid
                    target_role_node = n
                    break

        permitted: Set[str] = set()
        forbidden: Set[str] = set()
        inherited_roles: List[str] = []
        restricted_actions: Set[str] = set()

        if target_role_node:
            props = target_role_node.get("properties", {})
            permitted.update(props.get("permitted_tools", []))
            forbidden.update(props.get("forbidden_tools", []))

            # Find parent roles via INHERITS_FROM
            queue = [role_node_id]
            visited = {role_node_id}
            while queue:
                curr = queue.pop(0)
                for e in edges:
                    if e.get("source") == curr and e.get("relation") == "INHERITS_FROM":
                        parent = e.get("target")
                        if parent and parent not in visited:
                            visited.add(parent)
                            inherited_roles.append(parent)
                            queue.append(parent)
                            if parent in nodes:
                                p_props = nodes[parent].get("properties", {})
                                permitted.update(p_props.get("permitted_tools", []))
                                forbidden.update(p_props.get("forbidden_tools", []))

            # Find governing rules
            for e in edges:
                if e.get("relation") == "GOVERNS" and (
                    e.get("target") == role_node_id or e.get("target") in inherited_roles
                ):
                    rule_node = nodes.get(e.get("source"))
                    if rule_node:
                        r_props = rule_node.get("properties", {})
                        restricted_actions.update(r_props.get("restricted_actions", []))

        # Effective authorized tools = permitted - forbidden
        authorized_tools = sorted(permitted - forbidden)

        tool_authorized = None
        if tool:
            tool_clean = tool.strip()
            tool_authorized = (tool_clean in authorized_tools) and (tool_clean not in forbidden)

        return {
            "success": True,
            "subcommand": "route",
            "routing": {
                "role": role_node_id,
                "role_found": target_role_node is not None,
                "authorized_tools": authorized_tools,
                "forbidden_tools": sorted(forbidden),
                "restricted_actions": sorted(restricted_actions),
                "inherited_roles": inherited_roles,
                "task": task,
                "tool_checked": tool,
                "tool_authorized": tool_authorized,
            },
        }

    def run_bot_audit(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Perform autonomous health audit and reconciliation."""
        val = self.validate(path)
        stat = self.get_status(path)
        return {
            "success": val["validation"]["valid"],
            "subcommand": "bot",
            "action": "audit",
            "validation": val["validation"],
            "status": stat["status"],
            "health": "healthy" if val["validation"]["valid"] else "degraded",
        }
