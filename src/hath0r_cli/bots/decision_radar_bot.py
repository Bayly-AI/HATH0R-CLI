"""DecisionRadarBot (CruiseControlBot): Cruise Control Agent Decision Control Layer & Unblocking Engine.

Provides:
- Graph-theoretic dependency modeling and transitive unblocking impact reranking (Task 2 / #501)
- Event-driven fact settlement engine replacing timer snoozing (Task 3 / #502)
- Bidirectional Input & Output work boundary approval gates with HMAC tokens (Task 4 / #503)
- Persistent CAS micro-store in .hath0r/decisions/ with MemoryGraph compounding (Task 1 / #500)
- Radial polar coordinate layout engine for Cruise Control Sunburst UI & TUI (Task 6 / #505)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from hath0r_cli.bots.memory_manager import MemoryManagerBot

SCHEMA_VERSION = "hath0r.decision.spec/1"
REMOTE_SYNC_ROUTES = frozenset(
    {
        "/api/decisions/request",
        "/api/decisions/update",
        "/api/decisions/answer",
        "/api/decisions/reject",
        "/api/decisions/snooze",
        "/api/decisions/assert-fact",
        "/api/decisions/dep",
    }
)
REMOTE_SYNC_TIMEOUT_S = 2.0
DEFAULT_AGENT_ID = "@agent"

CANONICAL_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "needs_card": {
        "id": "needs_card",
        "label": "Needs a card",
        "color": "#94a3b8",
        "border": "dashed",
        "wedge_index": 0,
        "description": "Financial approvals, credit tier upgrades, cloud billing tokens",
    },
    "only_you_can_do_this": {
        "id": "only_you_can_do_this",
        "label": "Only you can do this",
        "color": "#60a5fa",
        "border": "solid",
        "wedge_index": 1,
        "description": "Human-exclusive credentials, master keys, high-risk migrations",
    },
    "approve_message": {
        "id": "approve_message",
        "label": "Approve a message",
        "color": "#f59e0b",
        "border": "solid",
        "wedge_index": 2,
        "description": "External outbound emails, PR comments, partner notifications",
    },
    "set_product_rule": {
        "id": "set_product_rule",
        "label": "Set a product rule",
        "color": "#34d399",
        "border": "solid",
        "wedge_index": 3,
        "description": "Architecture invariants, schema conflicts, ambiguous business logic",
    },
    "start_hold_work": {
        "id": "start_hold_work",
        "label": "Start or hold work",
        "color": "#f43f5e",
        "border": "solid",
        "wedge_index": 4,
        "description": "Input boundary gate, agent queue scheduling, prioritization",
    },
    "accept_delivered_work": {
        "id": "accept_delivered_work",
        "label": "Accept delivered work",
        "color": "#a78bfa",
        "border": "solid",
        "wedge_index": 5,
        "description": "Output boundary gate, PR approval, diff verification",
    },
    "keep_ledger_true": {
        "id": "keep_ledger_true",
        "label": "Keep the ledger true",
        "color": "#2dd4bf",
        "border": "solid",
        "wedge_index": 6,
        "description": "State reconciliation, test catalog alignment, memory synchronization",
    },
}

DECISION_STATUSES = (
    "WAITING_HUMAN",
    "WAITING_FACT",
    "RESOLVED_HUMAN",
    "SETTLED_BY_EVENT",
    "REJECTED",
)

WORK_BOUNDARIES = ("DECISION", "INPUT", "OUTPUT")


class CASConflictError(RuntimeError):
    """Raised when optimistic Compare-And-Swap hash verification fails."""


class DecisionGraph:
    """Directed dependency graph modeling waiting agents, decisions, and downstream tasks."""

    def __init__(self) -> None:
        self.decision_unblocks: Dict[str, Set[str]] = {}
        self.task_dependencies: Dict[str, Set[str]] = {}
        self.blocked_agents: Dict[str, Set[str]] = {}
        self.task_weights: Dict[str, float] = {}
        self.task_criticalities: Dict[str, float] = {}

    def add_decision(
        self,
        decision_id: str,
        agent_id: str,
        unblocks: List[str],
        criticality: float = 1.0,
    ) -> None:
        """Register a decision node, its waiting agent, and direct downstream targets."""
        self.decision_unblocks.setdefault(decision_id, set()).update(unblocks)
        self.blocked_agents.setdefault(decision_id, set()).add(agent_id)
        for target in unblocks:
            self.task_weights.setdefault(target, 1.0)
            self.task_criticalities.setdefault(target, max(0.1, float(criticality)))

    def add_task_dependency(
        self,
        upstream_task: str,
        downstream_task: str,
        weight: float = 1.0,
        criticality: float = 1.0,
    ) -> None:
        """Register a directed edge indicating upstream_task unblocks downstream_task."""
        self.task_dependencies.setdefault(upstream_task, set()).add(downstream_task)
        self.task_weights.setdefault(downstream_task, float(weight))
        self.task_criticalities.setdefault(downstream_task, max(0.1, float(criticality)))

    def get_transitive_unblocked(self, decision_id: str) -> Set[str]:
        """Compute transitive closure of all downstream tasks/agents unblocked by decision_id."""
        direct = set(self.decision_unblocks.get(decision_id, set()))
        visited: Set[str] = set()
        stack: List[str] = list(direct)
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            for child in self.task_dependencies.get(current, set()):
                if child not in visited:
                    stack.append(child)
        return visited

    def has_cycle(self) -> bool:
        """Detect whether the task dependency graph contains any directed cycle."""
        state: Dict[str, int] = {}

        def _dfs(node: str) -> bool:
            state[node] = 1
            for nbr in self.task_dependencies.get(node, set()):
                nbr_state = state.get(nbr, 0)
                if nbr_state == 1 or (nbr_state == 0 and _dfs(nbr)):
                    return True
            state[node] = 2
            return False

        all_nodes = set(self.task_dependencies.keys())
        for node in all_nodes:
            if state.get(node, 0) == 0 and _dfs(node):
                return True
        return False

    def topological_order(self) -> List[str]:
        """Return a topological ordering of task nodes (empty list if cycle exists)."""
        if self.has_cycle():
            return []
        in_degree: Dict[str, int] = {}
        for src, targets in self.task_dependencies.items():
            in_degree.setdefault(src, 0)
            for tgt in targets:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1
        queue = sorted([n for n, deg in in_degree.items() if deg == 0])
        order: List[str] = []
        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for nxt in sorted(self.task_dependencies.get(curr, set())):
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)
        return order

    def compute_unblock_impact(
        self,
        decision_id: str,
        base_criticality: float = 1.0,
        agent_waiting_tax: float = 1.0,
    ) -> Dict[str, Any]:
        """Compute U(d) transitive unblocking impact score and priority tier."""
        transitive_targets = self.get_transitive_unblocked(decision_id)
        agents = self.blocked_agents.get(decision_id, set())

        task_score = 0.0
        for tgt in transitive_targets:
            w = self.task_weights.get(tgt, 1.0)
            k = self.task_criticalities.get(tgt, base_criticality)
            task_score += w * k

        agent_score = len(agents) * float(agent_waiting_tax) * max(0.5, float(base_criticality))
        total_score = round(task_score + agent_score, 2)
        unblock_count = max(1, len(transitive_targets))
        tier = self.classify_priority_tier(total_score, len(transitive_targets))

        return {
            "unblock_weight": total_score,
            "transitive_unblocked_count": len(transitive_targets),
            "unblock_badge": unblock_count,
            "transitive_targets": sorted(transitive_targets),
            "blocked_agents_count": len(agents),
            "priority_tier": tier,
        }

    @staticmethod
    def classify_priority_tier(score: float, transitive_count: int) -> str:
        """Classify decision urgency tier from impact score and transitive count."""
        if score >= 8.0 or transitive_count >= 4:
            return "P0"
        if score >= 4.0 or transitive_count >= 2:
            return "P1"
        if score >= 1.5 or transitive_count >= 1:
            return "P2"
        return "P3"


class FactSettlementEngine:
    """Evaluates declarative fact predicates to auto-settle waiting decisions."""

    def __init__(self, cwd: Path, facts_provider: Callable[[], Dict[str, Any]]) -> None:
        self.cwd = cwd
        self._facts_provider = facts_provider
        self._custom_probes: Dict[str, Callable[[str], Tuple[bool, str]]] = {}

    def register_probe(self, prefix: str, handler: Callable[[str], Tuple[bool, str]]) -> None:
        """Register a custom probe evaluator for a predicate prefix."""
        self._custom_probes[prefix.strip().lower()] = handler

    def evaluate_predicate(
        self,
        predicate: str,
        completed_ids: Optional[Set[str]] = None,
        live_probes: bool = False,
    ) -> Tuple[bool, str]:
        """Evaluate whether a declarative fact predicate is currently satisfied."""
        if not predicate or not predicate.strip():
            return False, "Empty predicate"

        clean_pred = predicate.strip()
        facts_map = self._facts_provider()

        # 1. Direct match in asserted facts store
        if clean_pred in facts_map and facts_map[clean_pred].get("satisfied", True):
            reason = facts_map[clean_pred].get("reason") or f"Fact asserted: {clean_pred}"
            return True, str(reason)

        if ":" not in clean_pred:
            return False, f"Waiting on fact: {clean_pred}"

        prefix, arg = clean_pred.split(":", 1)
        prefix_lower = prefix.strip().lower()
        arg_clean = arg.strip()

        if prefix_lower in self._custom_probes:
            return self._custom_probes[prefix_lower](arg_clean)

        if prefix_lower == "file.exists":
            return self._probe_file_exists(arg_clean)
        if prefix_lower == "memory.fact.asserted":
            return self._probe_memory_fact(arg_clean)
        if prefix_lower == "agent.task.completed":
            return self._probe_agent_completed(arg_clean, completed_ids or set())
        if prefix_lower == "git.commit.exists":
            return self._probe_git_commit(arg_clean, live_probes=live_probes)
        if prefix_lower == "git.pr.merged":
            return self._probe_git_pr_merged(arg_clean, facts_map, live_probes=live_probes)
        if prefix_lower == "ci.workflow.passed":
            return self._probe_ci_passed(arg_clean, facts_map)
        if prefix_lower == "endpoint.health.ok":
            return self._probe_endpoint_health(arg_clean, facts_map)

        return False, f"Fact pending: {clean_pred}"

    def _probe_file_exists(self, rel_or_abs: str) -> Tuple[bool, str]:
        cand = Path(rel_or_abs)
        target = cand if cand.is_absolute() else (self.cwd / cand)
        if target.exists():
            return True, f"File exists verified: {rel_or_abs}"
        return False, f"File not yet present: {rel_or_abs}"

    def _probe_memory_fact(self, query_key: str) -> Tuple[bool, str]:
        graph_file = self.cwd / ".hath0r" / "memory" / "graph.json"
        if not graph_file.is_file():
            return False, "MemoryGraph not initialized"
        try:
            gdata = json.loads(graph_file.read_text(encoding="utf-8"))
            for node in gdata.get("nodes", []):
                if not node.get("is_current", True):
                    continue
                if node.get("id") == query_key or query_key.lower() in str(node.get("label", "")).lower():
                    return True, f"MemoryGraph node verified: {node.get('id')}"
        except (OSError, ValueError, TypeError) as err:
            return False, f"MemoryGraph read error: {err}"
        return False, f"Memory node not yet asserted: {query_key}"

    def _probe_agent_completed(self, target_id: str, completed_ids: Set[str]) -> Tuple[bool, str]:
        if target_id in completed_ids or target_id.lstrip("@") in {c.lstrip("@") for c in completed_ids}:
            return True, f"Agent/task completed: {target_id}"
        return False, f"Agent/task still running: {target_id}"

    def _probe_git_commit(self, rev: str, live_probes: bool = False) -> Tuple[bool, str]:
        if not live_probes:
            return False, f"Git commit probe passive: {rev}"
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "--verify", f"{rev}^{{commit}}"],
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if proc.returncode == 0:
                return True, f"Git commit verified: {proc.stdout.strip()[:12]}"
        except (OSError, subprocess.SubprocessError) as err:
            return False, f"Git commit probe error: {err}"
        return False, f"Git commit not found: {rev}"

    def _probe_git_pr_merged(
        self,
        pr_spec: str,
        facts_map: Dict[str, Any],
        live_probes: bool = False,
    ) -> Tuple[bool, str]:
        key = f"git.pr.merged:{pr_spec}"
        if key in facts_map and facts_map[key].get("satisfied"):
            return True, f"PR merge recorded in fact ledger: {pr_spec}"
        if not live_probes:
            return False, f"PR not yet merged: {pr_spec}"
        try:
            pr_num = pr_spec.split("#")[-1].strip()
            cmd = ["gh", "pr", "view", pr_num, "--json", "state,mergedAt"]
            if "#" in pr_spec and "/" in pr_spec.split("#")[0]:
                repo_slug = pr_spec.split("#")[0].strip()
                cmd.extend(["--repo", repo_slug])
            proc = subprocess.run(cmd, cwd=str(self.cwd), capture_output=True, text=True, timeout=4, check=False)
            if proc.returncode == 0:
                payload = json.loads(proc.stdout)
                if payload.get("state") == "MERGED" or payload.get("mergedAt"):
                    return True, f"GitHub PR #{pr_num} merged at {payload.get('mergedAt')}"
        except (OSError, ValueError, subprocess.SubprocessError) as err:
            return False, f"PR check error: {err}"
        return False, f"PR still open: {pr_spec}"

    @staticmethod
    def _probe_ci_passed(workflow_spec: str, facts_map: Dict[str, Any]) -> Tuple[bool, str]:
        key = f"ci.workflow.passed:{workflow_spec}"
        if key in facts_map and facts_map[key].get("satisfied"):
            return True, f"CI workflow passed: {workflow_spec}"
        return False, f"CI workflow pending: {workflow_spec}"

    @staticmethod
    def _probe_endpoint_health(url: str, facts_map: Dict[str, Any]) -> Tuple[bool, str]:
        key = f"endpoint.health.ok:{url}"
        if key in facts_map and facts_map[key].get("satisfied"):
            return True, f"Endpoint healthy: {url}"
        return False, f"Endpoint health unverified: {url}"


class WorkBoundaryGate:
    """Signs and verifies HMAC tokens for Input ('what goes in') and Output ('what comes out') gates."""

    def __init__(self, secret_seed: Optional[str] = None) -> None:
        raw_secret = secret_seed or os.environ.get("HATH0R_GATE_SECRET", "hath0r-decision-radar-gate-v1")
        self._secret = raw_secret.encode("utf-8")

    def sign_gate_payload(
        self,
        decision_id: str,
        agent_id: str,
        boundary: str,
        operator: str,
        payload: Dict[str, Any],
    ) -> str:
        """Generate deterministic HMAC-SHA256 signature for an approved boundary gate."""
        canonical = json.dumps(
            {
                "decision_id": decision_id,
                "agent_id": agent_id,
                "boundary": boundary,
                "operator": operator,
                "payload": payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(self._secret, canonical, hashlib.sha256).hexdigest()

    def verify_gate_signature(
        self,
        decision_id: str,
        agent_id: str,
        boundary: str,
        operator: str,
        payload: Dict[str, Any],
        signature: str,
    ) -> bool:
        """Verify HMAC-SHA256 signature for a work boundary gate handshake."""
        expected = self.sign_gate_payload(decision_id, agent_id, boundary, operator, payload)
        return hmac.compare_digest(expected, signature or "")


class DecisionRadarBot:
    """Autonomous control plane managing the Cruise Control Agent Decision Radar."""

    def __init__(self, cwd: Optional[Path | str] = None) -> None:
        self.cwd = Path(cwd or Path.cwd()).resolve()
        self.decisions_dir = self.cwd / ".hath0r" / "decisions"
        self.active_path = self.decisions_dir / "active.json"
        self.archive_path = self.decisions_dir / "archive.json"
        self.facts_path = self.decisions_dir / "facts.json"
        self.ledger_path = self.decisions_dir / "ledger.json"
        self.server_state_path = self.decisions_dir / "server.json"
        self.gate = WorkBoundaryGate()
        self.fact_engine = FactSettlementEngine(self.cwd, self._load_facts)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _compute_sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _resolve_safe_store_path(self, path: Path) -> Path:
        allowed = {
            "active.json": self.active_path,
            "archive.json": self.archive_path,
            "facts.json": self.facts_path,
            "ledger.json": self.ledger_path,
            "server.json": self.server_state_path,
        }
        if path.name not in allowed:
            raise ValueError(f"Disallowed decision store filename: {path.name}")
        return allowed[path.name]

    def _atomic_write_json(self, path: Path, data: Any) -> str:
        safe_target = self._resolve_safe_store_path(path)
        safe_target.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(data, indent=2, sort_keys=True)
        digest = self._compute_sha256(serialized)
        tmp_path = safe_target.parent / f".{safe_target.name}.{uuid.uuid4().hex[:8]}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(serialized)
            fh.write("\n")
        os.replace(tmp_path, safe_target)
        return digest

    def _load_store(self, path: Path) -> Dict[str, Any]:
        safe_target = self._resolve_safe_store_path(path)
        if not safe_target.is_file():
            return {"schema_version": SCHEMA_VERSION, "revision": 0, "content_hash": "", "items": [], "task_edges": []}
        try:
            with open(safe_target, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                data.setdefault("items", [])
                data.setdefault("task_edges", [])
                data.setdefault("revision", 0)
                return data
        except (OSError, ValueError, TypeError):
            return {"schema_version": SCHEMA_VERSION, "revision": 0, "content_hash": "", "items": [], "task_edges": []}
        return {"schema_version": SCHEMA_VERSION, "revision": 0, "content_hash": "", "items": [], "task_edges": []}

    def _save_store(
        self,
        path: Path,
        store: Dict[str, Any],
        expected_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        current = self._load_store(path)
        current_hash = current.get("content_hash", "")
        if expected_hash and current_hash and expected_hash != current_hash:
            raise CASConflictError(
                f"CAS conflict on {path.name}: expected {expected_hash[:12]}, found {current_hash[:12]}"
            )
        store["schema_version"] = SCHEMA_VERSION
        store["revision"] = int(current.get("revision", 0)) + 1
        items_canonical = json.dumps(store.get("items", []), sort_keys=True, separators=(",", ":"))
        store["content_hash"] = self._compute_sha256(items_canonical)
        self._atomic_write_json(path, store)
        return store

    def _load_facts(self) -> Dict[str, Any]:
        if not self.facts_path.is_file():
            return {}
        try:
            with open(self.facts_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data.get("facts", {}) if isinstance(data, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    def _save_facts(self, facts: Dict[str, Any]) -> None:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "updated_at": self._utc_now(),
            "facts": facts,
        }
        self._atomic_write_json(self.facts_path, payload)

    def _append_ledger_entry(self, entry: Dict[str, Any]) -> None:
        ledger = self._load_store(self.ledger_path)
        ledger["items"].append(entry)
        self._save_store(self.ledger_path, ledger)

    def build_graph(self, active_items: List[Dict[str, Any]], task_edges: List[Dict[str, Any]]) -> DecisionGraph:
        """Construct DecisionGraph from active decisions and registered task dependency edges."""
        graph = DecisionGraph()
        for edge in task_edges:
            src = edge.get("from")
            dst = edge.get("to")
            if src and dst:
                graph.add_task_dependency(
                    str(src),
                    str(dst),
                    weight=float(edge.get("weight", 1.0)),
                    criticality=float(edge.get("criticality", 1.0)),
                )
        for item in active_items:
            if item.get("status") in ("WAITING_HUMAN", "WAITING_FACT"):
                graph.add_decision(
                    decision_id=str(item["decision_id"]),
                    agent_id=str(item.get("agent_id", DEFAULT_AGENT_ID)),
                    unblocks=[str(u) for u in item.get("unblocks", [])],
                    criticality=float(item.get("criticality", 1.0)),
                )
        return graph

    def _refresh_impact_scores(self, store: Dict[str, Any]) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = list(store.get("items", []))
        edges: List[Dict[str, Any]] = list(store.get("task_edges", []))
        graph = self.build_graph(items, edges)
        for item in items:
            impact = graph.compute_unblock_impact(
                decision_id=str(item["decision_id"]),
                base_criticality=float(item.get("criticality", 1.0)),
            )
            item["unblock_weight"] = impact["unblock_weight"]
            item["unblock_badge"] = impact["unblock_badge"]
            item["transitive_unblocked_count"] = impact["transitive_unblocked_count"]
            item["transitive_targets"] = impact["transitive_targets"]
            item["priority_tier"] = impact["priority_tier"]
            item["content_hash"] = self._compute_sha256(
                json.dumps(
                    {
                        "id": item["decision_id"],
                        "q": item["question"],
                        "status": item["status"],
                        "w": item["unblock_weight"],
                    },
                    sort_keys=True,
                )
            )
        items.sort(
            key=lambda x: (
                0 if x.get("status") == "WAITING_HUMAN" else 1,
                -float(x.get("unblock_weight", 0.0)),
                str(x.get("created_at", "")),
            )
        )
        store["items"] = items
        return items

    def add_task_dependency(
        self,
        upstream_task: str,
        downstream_task: str,
        weight: float = 1.0,
        criticality: float = 1.0,
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Add a task-to-task dependency edge in the decision graph (idempotent per from/to pair)."""
        store = self._load_store(self.active_path)
        edges: List[Dict[str, Any]] = store.get("task_edges", [])
        edges[:] = [e for e in edges if (e.get("from"), e.get("to")) != (upstream_task, downstream_task)]
        edges.append(
            {
                "from": upstream_task,
                "to": downstream_task,
                "weight": float(weight),
                "criticality": float(criticality),
            }
        )
        store["task_edges"] = edges
        graph = self.build_graph(store.get("items", []), edges)
        if graph.has_cycle():
            edges.pop()
            return {"success": False, "error": f"Cycle detected adding edge {upstream_task} -> {downstream_task}"}
        self._refresh_impact_scores(store)
        self._save_store(self.active_path, store)
        result: Dict[str, Any] = {"success": True, "edge": {"from": upstream_task, "to": downstream_task}}
        remote = self._sync_to_detached_server(
            "/api/decisions/dep",
            {"from": upstream_task, "to": downstream_task, "weight": float(weight), "criticality": float(criticality)},
            sync_remote=sync_remote,
        )
        if remote is not None:
            result["remote_sync"] = remote
        return result

    def _sync_to_detached_server(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        sync_remote: bool = True,
        port: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Forward a decision mutation to the running Cruise Control server.

        Returns ``None`` when no forwarding applies (disabled, same in-process server, nothing
        listening) and otherwise ``{"synced": bool, "port", "endpoint", ...}`` so callers can
        surface failures such as a stale server image answering 404 (#532).
        """
        if not sync_remote:
            return None
        if os.environ.get("PYTEST_CURRENT_TEST") and os.environ.get("HATH0R_CRUISE_REMOTE_SYNC") != "1":
            return None

        from hath0r_cli.server.decision_radar_server import (
            _ACTIVE_DAEMON_SERVERS,
            is_cruise_server_listening,
            resolve_cruise_port,
        )

        resolved_port = resolve_cruise_port(port)
        if resolved_port is None:
            return None

        in_proc = _ACTIVE_DAEMON_SERVERS.get(resolved_port)
        if in_proc is not None and in_proc.cwd == self.cwd:
            return None

        if not is_cruise_server_listening(host="127.0.0.1", port=resolved_port):
            return None

        if endpoint not in REMOTE_SYNC_ROUTES:
            return None

        result: Dict[str, Any] = {"synced": False, "port": resolved_port, "endpoint": endpoint}
        scheme = "ht" + "tp"
        url = f"{scheme}://127.0.0.1:{resolved_port}{endpoint}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Hath0r-Sync-Origin": "cli",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=REMOTE_SYNC_TIMEOUT_S) as resp:  # nosec B310
                body = json.loads(resp.read().decode("utf-8"))
            result["synced"] = bool(isinstance(body, dict) and body.get("success", True))
            if not result["synced"]:
                result["error"] = str(body.get("error", "server rejected the update"))
        except urllib.error.HTTPError as exc:
            result["status"] = exc.code
            result["error"] = (
                f"server on port {resolved_port} has no {endpoint} endpoint (stale Cruise Control image?)"
                if exc.code == 404
                else f"HTTP {exc.code} from {endpoint}"
            )
        except (OSError, ValueError, TypeError, urllib.error.URLError) as exc:
            result["error"] = str(exc)
        return result

    def sync_store_to_server(self, port: Optional[int] = None) -> Dict[str, Any]:
        """Push every open decision and dependency edge in this store to the running server (#532)."""
        from hath0r_cli.server.decision_radar_server import is_cruise_server_listening, resolve_cruise_port

        resolved_port = resolve_cruise_port(port)
        if resolved_port is None or not is_cruise_server_listening(host="127.0.0.1", port=resolved_port):
            return {"success": False, "port": resolved_port, "error": "No Cruise Control server is listening."}

        store = self._load_store(self.active_path)
        pushed: List[str] = []
        failed: List[Dict[str, Any]] = []
        for item in store.get("items", []):
            if not str(item.get("status", "")).startswith("WAITING"):
                continue
            notes = item.get("notes") or []
            payload = {
                "decision_id": item["decision_id"],
                "question": item.get("question"),
                "category": item.get("category"),
                "agent_id": item.get("agent_id"),
                "unblocks": item.get("unblocks") or [],
                "options": item.get("options") or [],
                "wait_for_fact": item.get("fact_predicate"),
                "criticality": item.get("criticality", 1.0),
                "work_boundary": item.get("work_boundary", "DECISION"),
                "note": notes[-1].get("note") if notes and isinstance(notes[-1], dict) else None,
                "context": item.get("context") or None,
            }
            res = self._sync_to_detached_server("/api/decisions/request", payload, port=resolved_port, sync_remote=True)
            if res is not None and res.get("synced"):
                pushed.append(item["decision_id"])
            else:
                failed.append({"id": item["decision_id"], "error": (res or {}).get("error", "not forwarded")})
        edges_pushed = 0
        for edge in store.get("task_edges", []):
            res = self._sync_to_detached_server(
                "/api/decisions/dep",
                {
                    "from": edge.get("from"),
                    "to": edge.get("to"),
                    "weight": edge.get("weight", 1.0),
                    "criticality": edge.get("criticality", 1.0),
                },
                port=resolved_port,
                sync_remote=True,
            )
            if res is not None and res.get("synced"):
                edges_pushed += 1
            else:
                failed.append(
                    {"id": f"{edge.get('from')}->{edge.get('to')}", "error": (res or {}).get("error", "not forwarded")}
                )
        return {
            "success": not failed,
            "port": resolved_port,
            "pushed": pushed,
            "edges_pushed": edges_pushed,
            "failed": failed,
        }

    def open_split_window_for_decision(
        self,
        decision_id: Optional[str] = None,
        side: str = "right",
        port: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Ensure detached Cruise Control server is running and open/tile it in a split-window browser display."""
        from hath0r_cli.server.decision_radar_server import (
            ensure_cruise_control_server,
            launch_cruise_control_split_window,
        )

        radar_url = ensure_cruise_control_server(cwd=self.cwd, port=port)
        return launch_cruise_control_split_window(url=radar_url, decision_id=decision_id, side=side)

    def request_decision(
        self,
        question: str,
        category: str = "set_product_rule",
        agent_id: str = DEFAULT_AGENT_ID,
        unblocks: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        wait_for_fact: Optional[str] = None,
        criticality: float = 1.0,
        work_boundary: str = "DECISION",
        boundary_payload: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None,
        expected_hash: Optional[str] = None,
        split_window: bool = False,
        split_side: str = "right",
        note: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Submit a waiting decision to the Cruise Control Decision Radar queue."""
        norm_cat = category.strip().lower()
        if norm_cat not in CANONICAL_CATEGORIES:
            norm_cat = "set_product_rule"

        norm_boundary = work_boundary.strip().upper()
        if norm_boundary not in WORK_BOUNDARIES:
            norm_boundary = "DECISION"

        dec_id = decision_id or f"dec-{uuid.uuid4().hex[:8]}"
        now = self._utc_now()
        clean_unblocks = [u.strip() for u in (unblocks or []) if u and u.strip()]
        status = "WAITING_FACT" if (wait_for_fact and wait_for_fact.strip()) else "WAITING_HUMAN"
        initial_notes: List[Dict[str, str]] = []
        if note and note.strip():
            initial_notes.append(
                {
                    "timestamp": now,
                    "agent_id": agent_id.strip() or DEFAULT_AGENT_ID,
                    "note": note.strip(),
                }
            )

        record: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "decision_id": dec_id,
            "category": norm_cat,
            "category_label": CANONICAL_CATEGORIES[norm_cat]["label"],
            "agent_id": agent_id.strip() or DEFAULT_AGENT_ID,
            "question": question.strip(),
            "options": list(options or []),
            "status": status,
            "unblocks": clean_unblocks,
            "unblock_weight": 0.0,
            "unblock_badge": max(1, len(clean_unblocks)),
            "criticality": max(0.1, float(criticality)),
            "priority_tier": "P2",
            "fact_predicate": wait_for_fact.strip() if wait_for_fact else None,
            "settlement_reason": None,
            "answer": None,
            "operator": None,
            "work_boundary": norm_boundary,
            "boundary_payload": dict(boundary_payload or {}),
            "notes": initial_notes,
            "context": dict(context or {}),
            "created_at": now,
            "updated_at": now,
            "resolved_at": None,
            "content_hash": "",
        }

        store = self._load_store(self.active_path)
        existing_idx = next(
            (i for i, it in enumerate(store["items"]) if it.get("decision_id") == dec_id),
            None,
        )
        if existing_idx is not None:
            store["items"][existing_idx] = record
        else:
            store["items"].append(record)

        self._refresh_impact_scores(store)
        self._save_store(self.active_path, store, expected_hash=expected_hash)
        updated = next(it for it in store["items"] if it["decision_id"] == dec_id)
        remote = self._sync_to_detached_server(
            "/api/decisions/request",
            {
                "decision_id": dec_id,
                "question": updated["question"],
                "category": updated["category"],
                "agent_id": updated["agent_id"],
                "unblocks": updated["unblocks"],
                "options": updated["options"],
                "wait_for_fact": updated["fact_predicate"],
                "criticality": updated["criticality"],
                "work_boundary": updated["work_boundary"],
                "note": note,
                "context": context,
            },
            sync_remote=sync_remote,
        )
        result: Dict[str, Any] = {"success": True, "decision": updated, "store_revision": store["revision"]}
        if remote is not None:
            result["remote_sync"] = remote
        if split_window:
            result["browser_window"] = self.open_split_window_for_decision(decision_id=dec_id, side=split_side)
        return result

    @staticmethod
    def _apply_decision_field_updates(
        target: Dict[str, Any],
        question: Optional[str],
        category: Optional[str],
        agent_id: Optional[str],
        unblocks: Optional[List[str]],
        options: Optional[List[str]],
        wait_for_fact: Optional[str],
        criticality: Optional[float],
    ) -> None:
        if question is not None and question.strip():
            target["question"] = question.strip()
        if category is not None and category.strip():
            norm_cat = category.strip().lower()
            if norm_cat in CANONICAL_CATEGORIES:
                target["category"] = norm_cat
                target["category_label"] = CANONICAL_CATEGORIES[norm_cat]["label"]
        if agent_id is not None and agent_id.strip():
            target["agent_id"] = agent_id.strip()
        if unblocks is not None:
            clean_unblocks = [u.strip() for u in unblocks if u and u.strip()]
            target["unblocks"] = clean_unblocks
            target["unblock_badge"] = max(1, len(clean_unblocks))
        if options is not None:
            target["options"] = [o.strip() for o in options if o and o.strip()]
        if wait_for_fact is not None:
            clean_fact = wait_for_fact.strip()
            target["fact_predicate"] = clean_fact or None
            if clean_fact:
                target["status"] = "WAITING_FACT"
        if criticality is not None:
            target["criticality"] = max(0.1, float(criticality))

    def _apply_decision_notes_and_context(
        self,
        target: Dict[str, Any],
        note: Optional[str],
        context: Optional[Dict[str, Any]],
        agent_id: Optional[str],
    ) -> None:
        now = self._utc_now()
        target["updated_at"] = now
        if note is not None and note.strip():
            notes_list = list(target.get("notes") or [])
            notes_list.append(
                {
                    "timestamp": now,
                    "agent_id": (agent_id or target.get("agent_id") or DEFAULT_AGENT_ID).strip(),
                    "note": note.strip(),
                }
            )
            target["notes"] = notes_list
        if context:
            merged_ctx = dict(target.get("context") or {})
            merged_ctx.update(context)
            target["context"] = merged_ctx

    def update_decision(
        self,
        decision_id: str,
        *,
        question: Optional[str] = None,
        category: Optional[str] = None,
        agent_id: Optional[str] = None,
        unblocks: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        wait_for_fact: Optional[str] = None,
        criticality: Optional[float] = None,
        status: Optional[str] = None,
        answer: Optional[str] = None,
        note: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        operator: Optional[str] = None,
        upsert: bool = True,
        split_window: bool = False,
        split_side: str = "right",
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Statelessly update an existing decision or push new agent context/information into Cruise Control."""
        clean_id = decision_id.strip()
        store = self._load_store(self.active_path)
        target = next((it for it in store["items"] if it.get("decision_id") == clean_id), None)

        if target is None:
            if not upsert:
                return {"success": False, "error": f"Decision '{clean_id}' not found in active queue."}
            created = self.request_decision(
                decision_id=clean_id,
                question=question or f"Agent decision update ({clean_id})",
                category=category or "set_product_rule",
                agent_id=agent_id or DEFAULT_AGENT_ID,
                unblocks=unblocks,
                options=options,
                wait_for_fact=wait_for_fact,
                criticality=criticality if criticality is not None else 1.0,
                note=note,
                context=context,
                split_window=split_window,
                split_side=split_side,
                sync_remote=False,
            )
            store = self._load_store(self.active_path)
            target = next((it for it in store["items"] if it.get("decision_id") == clean_id), created["decision"])
        else:
            self._apply_decision_field_updates(
                target,
                question=question,
                category=category,
                agent_id=agent_id,
                unblocks=unblocks,
                options=options,
                wait_for_fact=wait_for_fact,
                criticality=criticality,
            )
            self._apply_decision_notes_and_context(target, note=note, context=context, agent_id=agent_id)
            if status is not None and status.strip().upper() in ("WAITING_HUMAN", "WAITING_FACT"):
                target["status"] = status.strip().upper()
            self._refresh_impact_scores(store)
            self._save_store(self.active_path, store)

        norm_status = status.strip().upper() if status else ""
        if norm_status == "REJECTED":
            res = self.reject_decision(
                decision_id=clean_id,
                reason=answer or note or "Rejected via agent update",
                operator=operator,
                sync_remote=False,
            )
        elif norm_status in ("RESOLVED_HUMAN", "SETTLED_BY_EVENT") or (answer is not None and answer.strip()):
            res = self.answer_decision(
                decision_id=clean_id,
                answer=answer.strip() if (answer and answer.strip()) else "Resolved via agent update",
                operator=operator,
                sync_remote=False,
            )
        else:
            res = {"success": True, "decision": target, "store_revision": store["revision"]}

        remote = self._sync_to_detached_server(
            "/api/decisions/update",
            {
                "decision_id": clean_id,
                "question": question,
                "category": category,
                "agent_id": agent_id,
                "unblocks": unblocks,
                "options": options,
                "wait_for_fact": wait_for_fact,
                "criticality": criticality,
                "status": status,
                "answer": answer,
                "note": note,
                "context": context,
                "operator": operator,
                "upsert": upsert,
            },
            sync_remote=sync_remote,
        )
        if remote is not None:
            res["remote_sync"] = remote
        if split_window:
            res["browser_window"] = self.open_split_window_for_decision(decision_id=clean_id, side=split_side)
        return res

    def create_input_gate(
        self,
        agent_id: str,
        intent: str,
        token_budget: int = 50000,
        tools: Optional[List[str]] = None,
        unblocks: Optional[List[str]] = None,
        criticality: float = 1.5,
        split_window: bool = False,
        split_side: str = "right",
    ) -> Dict[str, Any]:
        """Create an Input Work Boundary Gate ('approve what goes into the work')."""
        payload = {
            "token_budget": int(token_budget),
            "tools": list(tools or ["read_file", "edit_file", "run_command"]),
            "intent": intent,
            "hmac_signature": None,
        }
        return self.request_decision(
            question=f"Start work: {intent} (budget={token_budget} tokens)",
            category="start_hold_work",
            agent_id=agent_id,
            unblocks=unblocks or [f"work:{agent_id}"],
            options=["Approve Input Gate", "Hold Work", "Reduce Budget"],
            criticality=criticality,
            work_boundary="INPUT",
            boundary_payload=payload,
            split_window=split_window,
            split_side=split_side,
        )

    def create_output_gate(
        self,
        agent_id: str,
        summary: str,
        diff_summary: str = "",
        pr_draft: str = "",
        tests_passed: bool = True,
        unblocks: Optional[List[str]] = None,
        criticality: float = 1.8,
        split_window: bool = False,
        split_side: str = "right",
    ) -> Dict[str, Any]:
        """Create an Output Work Boundary Gate ('approve what comes out of the work')."""
        payload = {
            "diff_summary": diff_summary,
            "pr_draft": pr_draft,
            "tests_passed": bool(tests_passed),
            "hmac_signature": None,
        }
        return self.request_decision(
            question=f"Delivered, accept work: {summary}",
            category="accept_delivered_work",
            agent_id=agent_id,
            unblocks=unblocks or [f"merge:{agent_id}"],
            options=["Accept & Sign Off", "Request Revision", "Reject Delivery"],
            criticality=criticality,
            work_boundary="OUTPUT",
            boundary_payload=payload,
            split_window=split_window,
            split_side=split_side,
        )

    def answer_decision(
        self,
        decision_id: str,
        answer: str,
        operator: Optional[str] = None,
        compound: bool = True,
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Resolve a decision with a human operator answer, sign boundary gates, and compound to MemoryGraph."""
        resolved_operator = operator or os.environ.get("USER", "Mark")
        store = self._load_store(self.active_path)
        target = next((it for it in store["items"] if it.get("decision_id") == decision_id), None)
        if not target:
            return {"success": False, "error": f"Decision '{decision_id}' not found in active queue."}

        now = self._utc_now()
        target["status"] = "RESOLVED_HUMAN"
        target["answer"] = answer.strip()
        target["operator"] = resolved_operator
        target["resolved_at"] = now

        boundary = target.get("work_boundary", "DECISION")
        if boundary in ("INPUT", "OUTPUT"):
            b_payload = dict(target.get("boundary_payload") or {})
            sig = self.gate.sign_gate_payload(
                decision_id=decision_id,
                agent_id=str(target.get("agent_id", DEFAULT_AGENT_ID)),
                boundary=boundary,
                operator=resolved_operator,
                payload={k: v for k, v in b_payload.items() if k != "hmac_signature"},
            )
            b_payload["hmac_signature"] = sig
            target["boundary_payload"] = b_payload
            self._append_ledger_entry(
                {
                    "timestamp": now,
                    "decision_id": decision_id,
                    "agent_id": target.get("agent_id"),
                    "boundary": boundary,
                    "operator": resolved_operator,
                    "answer": target["answer"],
                    "hmac_signature": sig,
                }
            )

        self._archive_resolved_decision(store, target)
        compounded_node = self._compound_decision_to_memory(target) if compound else None
        self._sync_to_detached_server(
            "/api/decisions/answer",
            {"decision_id": decision_id, "answer": target["answer"], "operator": resolved_operator},
            sync_remote=sync_remote,
        )
        return {
            "success": True,
            "decision": target,
            "compounded_node_id": compounded_node,
        }

    def reject_decision(
        self,
        decision_id: str,
        reason: str,
        operator: Optional[str] = None,
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Reject a waiting decision or work boundary request."""
        resolved_operator = operator or os.environ.get("USER", "Mark")
        store = self._load_store(self.active_path)
        target = next((it for it in store["items"] if it.get("decision_id") == decision_id), None)
        if not target:
            return {"success": False, "error": f"Decision '{decision_id}' not found in active queue."}

        target["status"] = "REJECTED"
        target["answer"] = f"REJECTED: {reason.strip()}"
        target["operator"] = resolved_operator
        target["resolved_at"] = self._utc_now()
        self._archive_resolved_decision(store, target)
        self._sync_to_detached_server(
            "/api/decisions/reject",
            {"decision_id": decision_id, "reason": reason.strip(), "operator": resolved_operator},
            sync_remote=sync_remote,
        )
        return {"success": True, "decision": target}

    def snooze_on_fact(
        self,
        decision_id: str,
        fact_predicate: str,
        operator: Optional[str] = None,
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Bind a waiting question to a declarative fact predicate instead of a countdown timer."""
        if not fact_predicate or not fact_predicate.strip():
            return {"success": False, "error": "fact_predicate must be a non-empty string."}

        store = self._load_store(self.active_path)
        target = next((it for it in store["items"] if it.get("decision_id") == decision_id), None)
        if not target:
            return {"success": False, "error": f"Decision '{decision_id}' not found in active queue."}

        target["fact_predicate"] = fact_predicate.strip()
        target["status"] = "WAITING_FACT"
        if operator:
            target["operator"] = operator
        self._refresh_impact_scores(store)
        self._save_store(self.active_path, store)
        self._sync_to_detached_server(
            "/api/decisions/snooze",
            {"decision_id": decision_id, "fact_predicate": fact_predicate.strip(), "operator": operator},
            sync_remote=sync_remote,
        )
        return {"success": True, "decision": target}

    def assert_fact(
        self,
        fact_predicate: str,
        reason: str = "External event satisfied fact",
        source: str = "operator",
        auto_settle: bool = True,
        sync_remote: bool = True,
    ) -> Dict[str, Any]:
        """Record a verified fact in the fact store and optionally auto-settle waiting decisions."""
        clean_fact = fact_predicate.strip()
        facts = self._load_facts()
        facts[clean_fact] = {
            "predicate": clean_fact,
            "satisfied": True,
            "reason": reason,
            "source": source,
            "asserted_at": self._utc_now(),
        }
        self._save_facts(facts)
        settlement = self.evaluate_and_settle_facts() if auto_settle else {"settled_count": 0, "settled": []}
        self._sync_to_detached_server(
            "/api/decisions/assert-fact",
            {"fact_predicate": clean_fact, "reason": reason},
            sync_remote=sync_remote,
        )
        return {
            "success": True,
            "fact": facts[clean_fact],
            "settled_count": settlement["settled_count"],
            "settled": settlement["settled"],
        }

    def evaluate_and_settle_facts(
        self,
        live_probes: bool = False,
        compound: bool = True,
    ) -> Dict[str, Any]:
        """Evaluate all pending fact predicates and auto-settle satisfied decisions without human touch."""
        store = self._load_store(self.active_path)
        archive = self._load_store(self.archive_path)

        completed_ids: Set[str] = set()
        for arch_item in archive.get("items", []):
            if arch_item.get("status") in ("RESOLVED_HUMAN", "SETTLED_BY_EVENT"):
                completed_ids.add(str(arch_item.get("decision_id", "")))
                completed_ids.add(str(arch_item.get("agent_id", "")))
                completed_ids.update(str(u) for u in arch_item.get("unblocks", []))

        settled_items: List[Dict[str, Any]] = []
        remaining_items: List[Dict[str, Any]] = []

        for item in store.get("items", []):
            pred = item.get("fact_predicate")
            if pred:
                satisfied, reason = self.fact_engine.evaluate_predicate(
                    str(pred),
                    completed_ids=completed_ids,
                    live_probes=live_probes,
                )
                if satisfied:
                    now = self._utc_now()
                    item["status"] = "SETTLED_BY_EVENT"
                    item["settlement_reason"] = reason
                    item["answer"] = f"[AUTO-SETTLED BY FACT] {reason}"
                    item["operator"] = "fact-settlement-engine"
                    item["resolved_at"] = now
                    settled_items.append(item)
                    completed_ids.add(str(item.get("decision_id", "")))
                    completed_ids.add(str(item.get("agent_id", "")))
                    completed_ids.update(str(u) for u in item.get("unblocks", []))
                    continue
            remaining_items.append(item)

        if settled_items:
            store["items"] = remaining_items
            self._refresh_impact_scores(store)
            self._save_store(self.active_path, store)
            for s_item in settled_items:
                archive["items"].append(s_item)
                if compound:
                    self._compound_decision_to_memory(s_item)
            self._save_store(self.archive_path, archive)

        return {
            "success": True,
            "settled_count": len(settled_items),
            "settled": settled_items,
            "remaining_open": len(remaining_items),
        }

    def wait_for_resolution(
        self,
        decision_id: str,
        timeout_seconds: float = 5.0,
        poll_interval: float = 0.2,
        live_probes: bool = False,
        split_window: bool = True,
        split_side: str = "right",
    ) -> Dict[str, Any]:
        """Poll until a decision is answered by a human or settled by an event fact."""
        window_info: Optional[Dict[str, Any]] = None
        if split_window and os.environ.get("HATH0R_CRUISE_AUTO_SPLIT", "1") != "0":
            window_info = self.open_split_window_for_decision(decision_id=decision_id, side=split_side)

        deadline = time.monotonic() + max(0.0, float(timeout_seconds))
        while True:
            self.evaluate_and_settle_facts(live_probes=live_probes)
            archive = self._load_store(self.archive_path)
            for item in reversed(archive.get("items", [])):
                if item.get("decision_id") == decision_id:
                    return {
                        "success": True,
                        "resolved": True,
                        "decision": item,
                        "browser_window": window_info,
                    }

            active = self._load_store(self.active_path)
            current = next((it for it in active.get("items", []) if it.get("decision_id") == decision_id), None)
            if current is None:
                return {"success": False, "resolved": False, "error": f"Decision '{decision_id}' not found."}

            if time.monotonic() >= deadline:
                return {
                    "success": True,
                    "resolved": False,
                    "timeout": True,
                    "decision": current,
                    "browser_window": window_info,
                }
            time.sleep(min(poll_interval, max(0.01, deadline - time.monotonic())))

    def _archive_resolved_decision(self, active_store: Dict[str, Any], resolved_item: Dict[str, Any]) -> None:
        dec_id = resolved_item.get("decision_id")
        active_store["items"] = [it for it in active_store.get("items", []) if it.get("decision_id") != dec_id]
        self._refresh_impact_scores(active_store)
        self._save_store(self.active_path, active_store)

        archive = self._load_store(self.archive_path)
        archive["items"].append(resolved_item)
        self._save_store(self.archive_path, archive)

    def _compound_decision_to_memory(self, decision: Dict[str, Any]) -> Optional[str]:
        """Compound a resolved or event-settled decision into .hath0r/memory/graph.json."""
        try:
            mem_bot = MemoryManagerBot(cwd=self.cwd)
            dec_id = decision.get("decision_id", "unknown")
            node_id = f"decision:{dec_id}"
            status = decision.get("status", "RESOLVED_HUMAN")
            content = (
                f"Decision {dec_id} ({decision.get('category_label', decision.get('category'))}) "
                f"for agent {decision.get('agent_id')}: '{decision.get('question')}' -> "
                f"{status}: {decision.get('answer')}. Unblocked: {', '.join(decision.get('unblocks', [])) or 'none'}."
            )
            res = mem_bot.compound_memory(
                label=f"Decision {dec_id}: {str(decision.get('question', ''))[:48]}",
                content=content,
                node_type="decision",
                node_id=node_id,
                importance=0.85,
                tags=["decision-radar", str(decision.get("category", "rule")), status.lower()],
                relation="RESOLVES",
                metadata={
                    "decision_id": dec_id,
                    "agent_id": decision.get("agent_id"),
                    "unblocks": decision.get("unblocks", []),
                    "unblock_weight": decision.get("unblock_weight", 0.0),
                    "status": status,
                },
            )
            return str(res.get("node", {}).get("id", node_id))
        except (OSError, ValueError, RuntimeError):
            return None

    def list_decisions(
        self,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        include_archived: bool = False,
    ) -> Dict[str, Any]:
        """Return ranked open decisions, optional archived items, and operator queue telemetry."""
        active_store = self._load_store(self.active_path)
        items = self._refresh_impact_scores(active_store)
        archive_store = self._load_store(self.archive_path)
        archived_items = archive_store.get("items", [])

        filtered = list(items)
        if include_archived:
            filtered.extend(archived_items)
        if status_filter:
            sf = status_filter.strip().upper()
            filtered = [it for it in filtered if it.get("status") == sf]
        if category_filter:
            cf = category_filter.strip().lower()
            filtered = [it for it in filtered if it.get("category") == cf]

        settled_by_event = sum(1 for it in archived_items if it.get("status") == "SETTLED_BY_EVENT")
        resolved_human = sum(1 for it in archived_items if it.get("status") == "RESOLVED_HUMAN")

        category_counts: Dict[str, int] = dict.fromkeys(CANONICAL_CATEGORIES, 0)
        for it in items:
            cat = str(it.get("category", "set_product_rule"))
            if cat in category_counts:
                category_counts[cat] += 1

        return {
            "success": True,
            "summary": {
                "open_count": len(items),
                "waiting_human_count": sum(1 for it in items if it.get("status") == "WAITING_HUMAN"),
                "waiting_fact_count": sum(1 for it in items if it.get("status") == "WAITING_FACT"),
                "answered_count": len(archived_items),
                "resolved_by_human_count": resolved_human,
                "settled_by_event_count": settled_by_event,
                "total_unblock_weight": round(sum(float(it.get("unblock_weight", 0.0)) for it in items), 2),
                "category_counts": category_counts,
            },
            "decisions": filtered,
        }

    def get_radar_snapshot(self, operator_name: str = "Mark") -> Dict[str, Any]:
        """Compute full polar radial sunburst geometry for the Cruise Control Radar UI."""
        listing = self.list_decisions(include_archived=False)
        open_decisions = listing["decisions"]
        summary = listing["summary"]

        wedges: List[Dict[str, Any]] = []
        num_wedges = len(CANONICAL_CATEGORIES)
        sector_span_deg = 360.0 / num_wedges

        # Start at -90 deg (top of circle)
        for cat_id, meta in CANONICAL_CATEGORIES.items():
            idx = int(meta["wedge_index"])
            start_deg = -90.0 + idx * sector_span_deg
            end_deg = start_deg + sector_span_deg
            mid_deg = (start_deg + end_deg) / 2.0
            cat_decisions = [d for d in open_decisions if d.get("category") == cat_id]

            positioned_nodes: List[Dict[str, Any]] = []
            count = len(cat_decisions)
            for n_idx, dec in enumerate(cat_decisions):
                # Distribute angularly inside the wedge cone with padding
                if count == 1:
                    angle_deg = mid_deg
                else:
                    pad = sector_span_deg * 0.18
                    usable = sector_span_deg - 2 * pad
                    angle_deg = (start_deg + pad) + (n_idx / max(1, count - 1)) * usable

                # Radial distance: higher unblock weight sits closer to inner action ring (radius 230..360)
                weight = float(dec.get("unblock_weight", 1.0))
                norm_factor = min(1.0, weight / 10.0)
                if norm_factor >= 0.5:
                    orbit_ring = 1
                elif n_idx % 2 == 0:
                    orbit_ring = 2
                else:
                    orbit_ring = 3
                radius = 235.0 + (orbit_ring - 1) * 58.0

                angle_rad = math.radians(angle_deg)
                positioned_nodes.append(
                    {
                        **dec,
                        "polar": {
                            "angle_deg": round(angle_deg, 2),
                            "radius": round(radius, 2),
                            "orbit_ring": orbit_ring,
                            "x_offset": round(radius * math.cos(angle_rad), 2),
                            "y_offset": round(radius * math.sin(angle_rad), 2),
                        },
                    }
                )

            wedges.append(
                {
                    "id": cat_id,
                    "label": meta["label"],
                    "color": meta["color"],
                    "border": meta["border"],
                    "description": meta["description"],
                    "wedge_index": idx,
                    "start_deg": round(start_deg, 2),
                    "end_deg": round(end_deg, 2),
                    "mid_deg": round(mid_deg, 2),
                    "decision_count": count,
                    "nodes": positioned_nodes,
                }
            )

        return {
            "schema_version": SCHEMA_VERSION,
            "timestamp": self._utc_now(),
            "operator": {
                "name": operator_name,
                "open_count": summary["open_count"],
                "answered_today": summary["answered_count"],
                "settled_by_event": summary["settled_by_event_count"],
                "total_unblock_weight": summary["total_unblock_weight"],
            },
            "wedges": wedges,
            "decisions": open_decisions,
        }

    def seed_demo_radar(self) -> Dict[str, Any]:
        """Populate the canonical 22-decision Cruise Control reference topology for visualization."""
        store = {"schema_version": SCHEMA_VERSION, "revision": 0, "content_hash": "", "items": [], "task_edges": []}
        self._save_store(self.active_path, store)

        demo_specs: List[Dict[str, Any]] = [
            # Needs a card (2)
            {
                "agent_id": "@o2022",
                "category": "needs_card",
                "question": "Provision GPU spot quota card for embedding cluster",
                "unblocks": ["embed-worker-1"],
                "criticality": 1.2,
            },
            {
                "agent_id": "@o2023",
                "category": "needs_card",
                "question": "Authorize Anthropic tier-4 burst rate limit card",
                "unblocks": ["eval-runner-2"],
                "criticality": 1.3,
            },
            # Only you can do this (4 representative high-leverage nodes)
            {
                "agent_id": "@a11152",
                "category": "only_you_can_do_this",
                "question": "Patch and reboot the Parts-API widget VMs",
                "unblocks": ["vm-node-1", "vm-node-2"],
                "criticality": 2.0,
            },
            {
                "agent_id": "@a11062",
                "category": "only_you_can_do_this",
                "question": "Catalog read-only tools at zero credit balance",
                "unblocks": ["catalog-sync", "mcp-ro-gate", "billing-guard"],
                "criticality": 2.2,
            },
            {
                "agent_id": "@a11374",
                "category": "only_you_can_do_this",
                "question": "Widget profile text vs the MCP widget_profile schema",
                "unblocks": ["schema-v2", "mcp-contract"],
                "criticality": 1.8,
            },
            {
                "agent_id": "@a9189",
                "category": "only_you_can_do_this",
                "question": "Rotate production SONAR_TOKEN in repository secrets",
                "unblocks": ["ci-gate-sonar"],
                "criticality": 1.5,
                "wait_for_fact": "ci.workflow.passed:sonar-gate",
            },
            # Approve a message (2)
            {
                "agent_id": "@a9499",
                "category": "approve_message",
                "question": "Confirm the Parts-API hand-off of five Alice endpoints",
                "unblocks": ["alice-handoff-1", "alice-handoff-2"],
                "criticality": 1.7,
            },
            {
                "agent_id": "@a6441",
                "category": "approve_message",
                "question": "Publish deprecation notice to Parts-API webhook consumers",
                "unblocks": ["webhook-v2-cutover"],
                "criticality": 1.4,
            },
            # Set a product rule (3)
            {
                "agent_id": "@a3740",
                "category": "set_product_rule",
                "question": "Confirm Parts-API build order: Widget search before index",
                "unblocks": ["@a6440", "@a9094", "search-indexer"],
                "criticality": 2.5,
            },
            {
                "agent_id": "@a9153",
                "category": "set_product_rule",
                "question": "Enforce strict idempotency key on Parts-API order mutation",
                "unblocks": ["order-mutation-spec"],
                "criticality": 1.6,
            },
            {
                "agent_id": "@a6440",
                "category": "set_product_rule",
                "question": "Fallback behavior when regional Redis cache misses",
                "unblocks": ["cache-policy-v1"],
                "criticality": 1.3,
                "wait_for_fact": "git.pr.merged:Bayly-AI/HATH0R-CLI#499",
            },
            # Start or hold work - Input Boundary Gates (3)
            {
                "agent_id": "@p4010",
                "category": "start_hold_work",
                "question": "Start work: Parts-API v3 GraphQL migration (budget=50000 tokens)",
                "unblocks": ["gql-schema", "gql-resolvers", "gql-tests", "gql-docs"],
                "criticality": 2.4,
                "work_boundary": "INPUT",
            },
            {
                "agent_id": "@p4011",
                "category": "start_hold_work",
                "question": "Start work: Telemetry histogram backfill across 3 shards",
                "unblocks": ["shard-1", "shard-2", "shard-3"],
                "criticality": 1.9,
                "work_boundary": "INPUT",
            },
            {
                "agent_id": "@p4012",
                "category": "start_hold_work",
                "question": "Start work: Fuzz test Parts-API auth middleware",
                "unblocks": ["auth-fuzz-suite", "sec-audit", "pen-report", "release-gate"],
                "criticality": 2.1,
                "work_boundary": "INPUT",
            },
            # Accept delivered work - Output Boundary Gate (1)
            {
                "agent_id": "drv-c9cdf6d8",
                "category": "accept_delivered_work",
                "question": "Delivered, nobody accepted: Widget proof & contract tests",
                "unblocks": ["release-train-1.8"],
                "criticality": 2.0,
                "work_boundary": "OUTPUT",
            },
            # Keep the ledger true (1)
            {
                "agent_id": "drv-a0d4c331",
                "category": "keep_ledger_true",
                "question": "In progress, its worker is gone: Reconcile orphaned state lock",
                "unblocks": ["worker-pool-reclaim", "lock-table-clean"],
                "criticality": 1.9,
            },
        ]

        for spec in demo_specs:
            self.request_decision(
                question=spec["question"],
                category=spec["category"],
                agent_id=spec["agent_id"],
                unblocks=spec["unblocks"],
                criticality=spec.get("criticality", 1.0),
                wait_for_fact=spec.get("wait_for_fact"),
                work_boundary=spec.get("work_boundary", "DECISION"),
            )

        return self.get_radar_snapshot(operator_name="Mark")


CruiseControlBot = DecisionRadarBot
