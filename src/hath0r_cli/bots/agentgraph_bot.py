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
            if not e.get("is_current", True):
                continue
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
            if not e.get("is_current", True):
                continue
            rel = e.get("relation", e.get("type", ""))
            if rel in ("INHERITS_FROM", "SUPERSEDES"):
                adj_inheritance[e["source"]].append(e["target"])

        def has_cycle(start_node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(start_node)
            rec_stack.add(start_node)
            for neighbor in adj_inheritance.get(start_node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(start_node)
            return False

        visited_nodes: Set[str] = set()
        for node_id in list(adj_inheritance.keys()):
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

    def heal(self, path: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Perform autonomous healing: prune orphan edges, break cycles, and reconcile graph."""
        graph = self.load_graph(path)
        nodes = {n.get("id"): n for n in graph.get("nodes", [])}
        edges = graph.get("edges", [])

        orphan_edges: List[Dict[str, Any]] = []
        valid_edges: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Prune / invalidate orphan edges
        for e in edges:
            src = e.get("source")
            tgt = e.get("target")
            rel = e.get("relation", e.get("type", "unknown"))
            if src not in nodes or (tgt not in nodes and rel not in ("AUTHORIZES_TOOL", "RESTRICTED_BY")):
                orphan_edges.append(e)
            else:
                valid_edges.append(e)

        # 2. Break cycles in inheritance / superseding
        adj: Dict[str, List[int]] = defaultdict(list)
        for idx, e in enumerate(valid_edges):
            if e.get("is_current", True) and e.get("relation") in ("INHERITS_FROM", "SUPERSEDES"):
                adj[e["source"]].append(idx)

        cycle_edges_indices: Set[int] = set()

        def detect_and_mark_cycle(curr: str, visited: Set[str], stack: List[str]) -> bool:
            visited.add(curr)
            stack.append(curr)
            for edge_idx in adj.get(curr, []):
                e = valid_edges[edge_idx]
                neighbor = e["target"]
                if neighbor not in visited:
                    if detect_and_mark_cycle(neighbor, visited, stack):
                        return True
                elif neighbor in stack:
                    cycle_edges_indices.add(edge_idx)
                    return True
            stack.pop()
            return False

        visited_nodes: Set[str] = set()
        for nid in list(adj.keys()):
            if nid not in visited_nodes:
                detect_and_mark_cycle(nid, visited_nodes, [])

        cycles_broken = len(cycle_edges_indices)
        for c_idx in cycle_edges_indices:
            valid_edges[c_idx]["is_current"] = False
            valid_edges[c_idx]["valid_to"] = now_iso
            valid_edges[c_idx]["cycle_broken"] = True

        healed_count = len(orphan_edges) + cycles_broken
        if not dry_run and healed_count > 0:
            graph["edges"] = valid_edges
            self.save_graph(graph, path)

        return {
            "success": True,
            "subcommand": "heal",
            "dry_run": dry_run,
            "orphans_pruned": len(orphan_edges),
            "cycles_broken": cycles_broken,
            "total_healed": healed_count,
            "remaining_edges": len(valid_edges),
        }

    def audit_cross_repo(self, base_dir: Optional[str] = None) -> Dict[str, Any]:
        """Perform cross-repository rule alignment and compliance audit."""
        search_root = Path(base_dir).resolve() if base_dir else self.cwd.parent
        repos_found: List[str] = []
        rule_matrix: Dict[str, List[str]] = defaultdict(list)
        missing_by_repo: Dict[str, List[str]] = defaultdict(list)

        canonical_rules = [
            "CR-CLI-ENTRY-001",
            "CR-BRANCH-GOV-001",
            "CR-DOCKER-HATH0R-GROUP-001",
            "CR-HATH0R-ROOT-001",
        ]

        if search_root.is_dir():
            for child in sorted(search_root.iterdir()):
                if child.is_dir() and (child / "AGENTS.md").is_file():
                    repo_name = child.name
                    repos_found.append(repo_name)
                    # Scan for canonical rules in AGENTS.md and rules.md
                    content = (child / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")
                    rm = child / "rules.md"
                    if rm.is_file():
                        content += "\n" + rm.read_text(encoding="utf-8", errors="ignore")

                    for crule in canonical_rules:
                        if re.search(rf"\b{re.escape(crule)}\b", content, re.IGNORECASE):
                            rule_matrix[crule].append(repo_name)
                        else:
                            missing_by_repo[repo_name].append(crule)

        # Calculate alignment score
        total_checks = len(repos_found) * len(canonical_rules) if repos_found else 1
        passed_checks = sum(len(repos) for repos in rule_matrix.values())
        alignment_score = round((passed_checks / max(1, total_checks)) * 100, 1)

        recommendations = []
        for repo_name, missing in missing_by_repo.items():
            if missing:
                recommendations.append(f"Repository '{repo_name}' is missing canonical rules: {', '.join(missing)}")

        return {
            "success": True,
            "subcommand": "cross_repo",
            "search_root": str(search_root),
            "repos_scanned": repos_found,
            "canonical_rules": canonical_rules,
            "rule_matrix": dict(rule_matrix),
            "missing_by_repo": dict(missing_by_repo),
            "alignment_score": alignment_score,
            "recommendations": recommendations,
        }

    def invalidate_bitemporal(
        self,
        target_id: str,
        superseding_id: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invalidate an entity or edge bitemporally by setting valid_to and linking SUPERSEDES."""
        graph = self.load_graph(path)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        now_iso = datetime.now(timezone.utc).isoformat()

        found_node = False
        for n in nodes:
            if n.get("id") == target_id:
                n["is_current"] = False
                n["valid_to"] = now_iso
                found_node = True

        found_edge = False
        for e in edges:
            if e.get("id") == target_id or f"{e.get('source')}->{e.get('target')}" == target_id:
                e["is_current"] = False
                e["valid_to"] = now_iso
                found_edge = True

        if superseding_id and (found_node or found_edge):
            edges.append(
                {
                    "source": superseding_id,
                    "target": target_id,
                    "relation": "SUPERSEDES",
                    "valid_from": now_iso,
                    "valid_to": None,
                    "is_current": True,
                }
            )

        self.save_graph(graph, path)
        return {
            "success": found_node or found_edge,
            "target_id": target_id,
            "superseding_id": superseding_id,
            "found_node": found_node,
            "found_edge": found_edge,
            "invalidated_at": now_iso,
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

    def migrate_repo(self, repo_path: Path | str, update_agents_md: bool = True) -> Dict[str, Any]:
        """Migrate a repository's rules, roles, and docs to the structured AgentGraph format."""
        target = Path(repo_path).resolve()
        if not target.is_dir():
            return {"success": False, "repo": str(target), "error": "Target directory does not exist"}

        # 1. Run sync to build graph
        self.sync(path=str(target), persist=True)

        # 2. Extract CR-* rules from AGENTS.md / rules.md if not already extracted
        graph = self.load_graph(str(target))
        nodes_dict = {n["id"]: n for n in graph.get("nodes", [])}
        edges = graph.get("edges", [])

        # Look in AGENTS.md and rules.md
        text_sources = []
        agents_file = target / "AGENTS.md"
        if agents_file.is_file():
            text_sources.append(agents_file.read_text(encoding="utf-8", errors="ignore"))
        rules_file = target / "rules.md"
        if rules_file.is_file():
            text_sources.append(rules_file.read_text(encoding="utf-8", errors="ignore"))
        for rf in target.glob("docs/rules/*.md"):
            text_sources.append(rf.read_text(encoding="utf-8", errors="ignore"))

        combined_text = "\n".join(text_sources)
        cr_matches = set(re.findall(r"\b(CR-[A-Z0-9-]+)\b", combined_text, re.IGNORECASE))

        known_rules = {
            "CR-CLI-ENTRY-001": (
                "CLI-First Rule",
                "CLI-First & Missing Capability Offer: invoke hath0r first, never ad-hoc workarounds.",
                "workflow",
            ),
            "CR-BRANCH-GOV-001": (
                "Branch Governance",
                "Branch & Promotion Governance: work PRs target development only, canonical promotion path.",
                "governance",
            ),
            "CR-DOCKER-HATH0R-GROUP-001": (
                "Docker Group Membership",
                "Docker group hath0r and network hath0r-net membership mandatory.",
                "architecture",
            ),
            "CR-HATH0R-ROOT-001": (
                "Hidden Root Rule",
                "Use only .hath0r/ as hidden project root. Never create legacy .ai/ or .infraOS/.",
                "governance",
            ),
            "CR-HATH0R-INIT-001": (
                "Hath0r Repo Init Gate",
                "Follow canonical playbook and runbook before repo initialization.",
                "workflow",
            ),
            "CR-BAI-001": (
                "BAI Promotion Gate",
                "Canonical promotion development -> testing -> staging -> master.",
                "governance",
            ),
        }

        rules_added = 0
        roles = [n["id"] for n in nodes_dict.values() if n.get("type") == "agent_role"]
        default_role = roles[0] if roles else "role:developer"
        if default_role not in nodes_dict:
            nodes_dict[default_role] = {
                "id": default_role,
                "plane": "rules",
                "type": "agent_role",
                "label": "Developer Agent",
                "content": f"Default developer role for {target.name}",
                "properties": {
                    "role_name": "developer",
                    "permitted_tools": ["read_file", "search_code", "run_command", "replace_file_content", "write_to_file"],
                    "forbidden_tools": [],
                },
                "is_current": True,
            }

        now_iso = datetime.now(timezone.utc).isoformat()
        for cr in sorted(cr_matches):
            cr_upper = cr.upper()
            rule_id = f"rule:{cr_upper.lower()}"
            if rule_id not in nodes_dict:
                meta = known_rules.get(
                    cr_upper,
                    (f"Rule {cr_upper}", f"Governance policy rule {cr_upper}", "governance"),
                )
                nodes_dict[rule_id] = {
                    "id": rule_id,
                    "plane": "rules",
                    "type": "rule_policy",
                    "label": meta[0],
                    "content": meta[1],
                    "policy_type": meta[2],
                    "enforcement_level": "hard_stop",
                    "is_current": True,
                    "valid_from": now_iso,
                    "valid_to": None,
                    "properties": {"rule_code": cr_upper},
                }
                rules_added += 1

                # Link default role to rule via RESTRICTED_BY
                edges.append(
                    {
                        "source": default_role,
                        "target": rule_id,
                        "relation": "RESTRICTED_BY",
                        "valid_from": now_iso,
                        "valid_to": None,
                        "is_current": True,
                    }
                )

        graph["nodes"] = list(nodes_dict.values())
        graph["edges"] = edges
        self.save_graph(graph, str(target))

        # 3. Heal any lingering cycles or orphan edges
        self.heal(str(target))

        # 4. Update AGENTS.md reference if requested and file exists
        agents_updated = False
        if update_agents_md and agents_file.is_file():
            content = agents_file.read_text(encoding="utf-8")
            if "agentgraph" not in content.lower():
                pointer_text = (
                    "\n## AgentGraph Substrate\n\n"
                    "This repository is governed by the Hath0r AgentGraph substrate. "
                    "Dynamic rule retrieval, role RBAC, and policy graphs are stored under `.hath0r/agentgraph/`.\n"
                    "- Query status: `hath0r agentgraph status`\n"
                    "- Validate rules: `hath0r agentgraph validate`\n"
                )
                agents_file.write_text(content + pointer_text, encoding="utf-8")
                agents_updated = True

        val = self.validate(str(target))
        stat = self.get_status(str(target))

        return {
            "success": val["validation"]["valid"],
            "repo": target.name,
            "path": str(target),
            "rules_migrated": rules_added,
            "total_nodes": stat["status"]["total_nodes"],
            "total_edges": stat["status"]["total_edges"],
            "validation": val["validation"],
            "agents_md_updated": agents_updated,
        }

    def migrate_all(self, base_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Batch migrate all recognized repositories in ~/Development workspaces."""
        if not base_dirs:
            dev_root = Path.home() / "Development"
            candidate_dirs = [
                dev_root / "OpenSource" / "hath0r-framework",
                dev_root / "OpenSource" / "hathor-cli",
                dev_root / "OpenSource" / "hath0r-poc",
                dev_root / "OpenSource" / "hath0r-mcp",
                dev_root / "OpenSource" / "hath0r-atc",
                dev_root / "BAI" / "ATC",
                dev_root / "BAI" / "MCP",
                dev_root / "BAI" / "UXP",
                dev_root / "1-Nation" / "C-MCP",
                dev_root / "1-Nation" / "ATC",
                dev_root / "1-Nation" / "MCP",
                dev_root / "1-Nation" / "UXP",
                dev_root / "Ray" / "workshop",
                dev_root / "Ray" / "mcp",
                dev_root / "Websites" / "Ray Bayly",
            ]
        else:
            candidate_dirs = [Path(d).resolve() for d in base_dirs]

        results = []
        all_valid = True

        for cdir in candidate_dirs:
            if cdir.is_dir() and ((cdir / "AGENTS.md").is_file() or (cdir / ".git").is_dir()):
                m_res = self.migrate_repo(cdir)
                if not m_res.get("success"):
                    all_valid = False
                results.append(m_res)

        return {
            "success": all_valid,
            "subcommand": "migrate_all",
            "migrated_count": len(results),
            "all_valid": all_valid,
            "results": results,
        }

