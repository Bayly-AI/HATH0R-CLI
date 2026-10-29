"""MemoryManagerBot: Manage canonical Local Memory Space and semantic memory graphs."""

from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, TypeVar

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover - Windows
    _fcntl = None  # type: ignore[assignment]

try:
    import msvcrt as _msvcrt
except ImportError:
    _msvcrt = None  # type: ignore[assignment]

_F = TypeVar("_F", bound=Callable[..., Any])

# Per-memory-dir re-entrant locks so nested CAS writes (session -> graph -> hashes.json)
# within one process do not deadlock on the cross-process file lock.
_LOCK_REGISTRY_GUARD = threading.Lock()
_MEMORY_RLOCKS: Dict[str, threading.RLock] = {}
_MEMORY_LOCK_DEPTH: Dict[str, int] = {}
_MEMORY_LOCK_HANDLES: Dict[str, Any] = {}


class MemoryHashConflictError(RuntimeError):
    """Raised when an optimistic Compare-And-Swap (CAS) SHA-256 check fails with an unmergeable conflict."""

    def __init__(
        self,
        message: str,
        *,
        expected_hash: Optional[str] = None,
        actual_hash: Optional[str] = None,
        conflicting_ids: Optional[List[str]] = None,
    ) -> None:
        super().__init__(message)
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.conflicting_ids = conflicting_ids or []
        self.error_code = "HASH_CONFLICT"


def _with_memory_lock(fn: _F) -> _F:
    """Serialize a MemoryManagerBot mutation so its CAS check and os.replace happen atomically."""

    @functools.wraps(fn)
    def wrapper(self: "MemoryManagerBot", *args: Any, **kwargs: Any) -> Any:
        with self._memory_lock():
            return fn(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


class MemoryManagerBot:
    """Bot to manage the Canonical Local Memory Space and Semantic Memory Graphs."""

    MAX_SESSION_CAPSULE_BYTES: int = 2048
    MAX_SESSION_ENTRIES: int = 8
    MAX_SESSION_RECALLED: int = 5

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
        "session",
        "micro-session",
        "eval",
    }

    CANONICAL_GRAPH_PATHS: tuple[str, ...] = (
        ".hath0r/mcp.json",
        ".hath0r/memory/graph.json",
        ".hath0r/memory/hashes.json",
        ".hath0r/memory/sessions/current.json",
        ".hath0r/evals/latest.json",
        ".hath0r/agentgraph/snapshot.json",
        ".hath0r/graphs/default.json",
        ".hath0r/state/cache/knowledge.json",
        ".hath0r/state/context/session_init.json",
    )

    CANONICAL_GITIGNORE_NEGATIONS: tuple[str, ...] = (
        "!.hath0r/",
        "!.hath0r/mcp.json",
        "!.hath0r/memory/",
        "!.hath0r/memory/**",
        "!.hath0r/memory/sessions/",
        "!.hath0r/memory/sessions/**",
        "!.hath0r/evals/",
        "!.hath0r/evals/**",
        "!.hath0r/agentgraph/",
        "!.hath0r/agentgraph/**",
        "!.hath0r/graphs/",
        "!.hath0r/graphs/**",
        "!.hath0r/state/",
        "!.hath0r/state/cache/",
        "!.hath0r/state/cache/**",
        "!.hath0r/state/context/",
        "!.hath0r/state/context/**",
    )

    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = (cwd or Path.cwd()).resolve()
        self.memory_dir = self.cwd / ".hath0r" / "memory"
        self.sessions_dir = self.memory_dir / "sessions"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._last_read_graph_hash: Optional[str] = None
        self._last_read_node_digests: Dict[str, str] = {}
        self._last_read_session_hash: Optional[str] = None

    def _memory_lock_path(self) -> Path:
        """Return the cross-process lock file for this memory dir (kept outside the repo tree)."""
        digest = hashlib.sha256(str(self.memory_dir).encode("utf-8")).hexdigest()[:16]
        return Path(tempfile.gettempdir()) / f"hath0r-memory-{digest}.lock"

    @contextmanager
    def _memory_lock(self) -> Iterator[None]:
        """Hold an exclusive, re-entrant lock on .hath0r/memory/ across threads and processes."""
        key = str(self.memory_dir)
        with _LOCK_REGISTRY_GUARD:
            rlock = _MEMORY_RLOCKS.setdefault(key, threading.RLock())
        with rlock:
            depth = _MEMORY_LOCK_DEPTH.get(key, 0)
            if depth == 0:
                handle = open(self._memory_lock_path(), "a+b")
                if _fcntl is not None:
                    _fcntl.flock(handle.fileno(), _fcntl.LOCK_EX)
                elif _msvcrt is not None:  # pragma: no cover - Windows
                    handle.seek(0)
                    _msvcrt.locking(handle.fileno(), _msvcrt.LK_LOCK, 1)
                _MEMORY_LOCK_HANDLES[key] = handle
            _MEMORY_LOCK_DEPTH[key] = depth + 1
            try:
                yield
            finally:
                _MEMORY_LOCK_DEPTH[key] -= 1
                if _MEMORY_LOCK_DEPTH[key] == 0:
                    handle = _MEMORY_LOCK_HANDLES.pop(key)
                    try:
                        if _fcntl is not None:
                            _fcntl.flock(handle.fileno(), _fcntl.LOCK_UN)
                        elif _msvcrt is not None:  # pragma: no cover - Windows
                            handle.seek(0)
                            _msvcrt.locking(handle.fileno(), _msvcrt.LK_UNLCK, 1)
                    finally:
                        handle.close()

    @staticmethod
    def _compute_sha256_bytes(data: bytes) -> str:
        """Return canonical 'sha256:<64-hex>' digest for raw bytes."""
        return f"sha256:{hashlib.sha256(data).hexdigest()}"

    @classmethod
    def _compute_file_sha256(cls, path: Path) -> Optional[str]:
        """Return canonical 'sha256:<64-hex>' digest for a file on disk, or None if missing."""
        if not path.is_file():
            return None
        return cls._compute_sha256_bytes(path.read_bytes())

    @staticmethod
    def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
        """Write text to a temporary sibling file and atomically replace target path via os.replace."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f".{path.name}.tmp.{uuid.uuid4().hex[:8]}"
        try:
            tmp_path.write_text(text, encoding=encoding)
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    @classmethod
    def _node_digest(cls, node: Dict[str, Any]) -> str:
        """Compute deterministic SHA-256 digest of a node's semantic content."""
        payload = {
            "id": str(node.get("id", "")),
            "type": str(node.get("type", "")),
            "label": str(node.get("label", "")),
            "content": str(node.get("content", "")),
            "importance": round(float(node.get("importance", 0.5)), 4),
            "tags": sorted(str(t) for t in node.get("tags", [])),
            "is_current": bool(node.get("is_current", True)),
            "valid_to": node.get("valid_to"),
        }
        return cls._compute_sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    @classmethod
    def _compute_graph_content_hash(cls, gdata: Dict[str, Any]) -> str:
        """Compute canonical SHA-256 content hash over nodes and edges in graph.json."""
        canonical_nodes = sorted(
            [
                {
                    "id": str(n.get("id", "")),
                    "type": str(n.get("type", "")),
                    "label": str(n.get("label", "")),
                    "content": str(n.get("content", "")),
                    "importance": round(float(n.get("importance", 0.5)), 4),
                    "tags": sorted(str(t) for t in n.get("tags", [])),
                    "is_current": bool(n.get("is_current", True)),
                }
                for n in gdata.get("nodes", [])
            ],
            key=lambda x: str(x["id"]),
        )
        canonical_edges = sorted(
            [
                {
                    "source": str(e.get("source", "")),
                    "target": str(e.get("target", "")),
                    "relation": str(e.get("relation", "")),
                    "weight": round(float(e.get("weight", 1.0)), 4),
                    "is_current": bool(e.get("is_current", True)),
                }
                for e in gdata.get("edges", [])
            ],
            key=lambda x: (str(x["source"]), str(x["target"]), str(x["relation"])),
        )
        payload = {
            "graph_id": gdata.get("graph_id", "canonical-memory-space"),
            "nodes": canonical_nodes,
            "edges": canonical_edges,
        }
        return cls._compute_sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    @classmethod
    def _compute_session_content_hash(cls, session: Dict[str, Any]) -> str:
        """Compute canonical SHA-256 content hash for a MicroMemorySession capsule."""
        payload = {
            "session_id": session.get("session_id"),
            "prior_session_id": session.get("prior_session_id"),
            "status": session.get("status"),
            "read_count": int(session.get("read_count", 0)),
            "write_count": int(session.get("write_count", 0)),
            "active_focus": session.get("active_focus", ""),
            "prior_summary": session.get("prior_summary", ""),
            "micro_entries": session.get("micro_entries", []),
            "next_steps": session.get("next_steps", []),
            "compounded_node_ids": session.get("compounded_node_ids", []),
        }
        return cls._compute_sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))

    @classmethod
    def _default_seed_graph(cls) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        seed: Dict[str, Any] = {
            "schema_version": "1.0.0",
            "graph_id": "canonical-memory-space",
            "revision": 1,
            "content_hash": "",
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
        seed["content_hash"] = cls._compute_graph_content_hash(seed)
        return seed

    def _load_or_seed_graph(self, record_read: bool = True) -> Dict[str, Any]:
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
        gdata["revision"] = max(1, int(gdata.get("revision", 1)))
        gdata["nodes"] = nodes
        gdata["edges"] = edges
        gdata["content_hash"] = self._compute_graph_content_hash(gdata)
        if record_read:
            self._last_read_graph_hash = gdata["content_hash"]
            self._last_read_node_digests = {
                str(n.get("id")): self._node_digest(n) for n in nodes if n.get("id")
            }
        return gdata

    def _load_graph(self) -> Dict[str, Any]:
        return self._load_or_seed_graph(record_read=True)

    @_with_memory_lock
    def _save_graph(
        self,
        gdata: Dict[str, Any],
        *,
        expected_hash: Optional[str] = None,
        auto_merge: bool = True,
        sync_hashes: bool = True,
    ) -> Path:
        graph_file = self.memory_dir / "graph.json"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        if graph_file.is_file():
            try:
                disk_data = json.loads(graph_file.read_text(encoding="utf-8"))
            except Exception:
                disk_data = None
            if isinstance(disk_data, dict):
                disk_hash = disk_data.get("content_hash") or self._compute_graph_content_hash(disk_data)
                if expected_hash and expected_hash != disk_hash:
                    raise MemoryHashConflictError(
                        f"HASH_CONFLICT on {graph_file}: expected_hash={expected_hash}, actual_hash={disk_hash}",
                        expected_hash=expected_hash,
                        actual_hash=disk_hash,
                    )
                if self._last_read_graph_hash and self._last_read_graph_hash != disk_hash:
                    if not auto_merge:
                        raise MemoryHashConflictError(
                            f"HASH_CONFLICT on {graph_file}: base_hash={self._last_read_graph_hash}, actual_hash={disk_hash}",
                            expected_hash=self._last_read_graph_hash,
                            actual_hash=disk_hash,
                        )
                    # Deterministic set-union auto-merge + same-ID conflict detection
                    my_nodes_by_id = {str(n.get("id")): n for n in gdata.get("nodes", []) if n.get("id")}
                    disk_nodes_by_id = {str(n.get("id")): n for n in disk_data.get("nodes", []) if n.get("id")}
                    conflicting_ids: List[str] = []
                    for nid, disk_node in disk_nodes_by_id.items():
                        if nid not in my_nodes_by_id:
                            my_nodes_by_id[nid] = disk_node
                        else:
                            my_node = my_nodes_by_id[nid]
                            my_d = self._node_digest(my_node)
                            disk_d = self._node_digest(disk_node)
                            if my_d != disk_d:
                                base_d = self._last_read_node_digests.get(nid)
                                if nid.startswith("session:") or nid in self.CANONICAL_SEED_NODE_IDS:
                                    # Session & seed nodes take latest timestamp
                                    if str(disk_node.get("updated_at", "")) > str(my_node.get("updated_at", "")):
                                        my_nodes_by_id[nid] = disk_node
                                elif base_d is not None:
                                    if my_d != base_d and disk_d != base_d:
                                        conflicting_ids.append(nid)
                                    elif my_d == base_d and disk_d != base_d:
                                        my_nodes_by_id[nid] = disk_node
                                else:
                                    conflicting_ids.append(nid)
                    if conflicting_ids:
                        raise MemoryHashConflictError(
                            f"HASH_CONFLICT: Concurrent incompatible mutation on node(s) {conflicting_ids}",
                            expected_hash=self._last_read_graph_hash,
                            actual_hash=disk_hash,
                            conflicting_ids=conflicting_ids,
                        )
                    gdata["nodes"] = list(my_nodes_by_id.values())
                    edges = list(gdata.get("edges", []))
                    existing_ekeys = {(e.get("source"), e.get("target"), e.get("relation")) for e in edges}
                    for dedge in disk_data.get("edges", []):
                        ekey = (dedge.get("source"), dedge.get("target"), dedge.get("relation"))
                        if ekey not in existing_ekeys:
                            edges.append(dedge)
                            existing_ekeys.add(ekey)
                    gdata["edges"] = edges
                    gdata["revision"] = max(int(gdata.get("revision", 0)), int(disk_data.get("revision", 0)))

        gdata["revision"] = int(gdata.get("revision", 0)) + 1
        gdata["updated_at"] = datetime.now(timezone.utc).isoformat()
        from hath0r_cli.bots.secret_pii_sanitizer import secret_pii_sanitizer

        for n in gdata.get("nodes", []):
            if isinstance(n, dict) and isinstance(n.get("content"), str):
                n["content"] = secret_pii_sanitizer.redact_text(n["content"]).sanitized_text
            if isinstance(n, dict) and isinstance(n.get("label"), str):
                n["label"] = secret_pii_sanitizer.redact_text(n["label"]).sanitized_text
        gdata["content_hash"] = self._compute_graph_content_hash(gdata)
        self._atomic_write_text(graph_file, json.dumps(gdata, indent=2))
        self._last_read_graph_hash = gdata["content_hash"]
        self._last_read_node_digests = {
            str(n.get("id")): self._node_digest(n) for n in gdata.get("nodes", []) if n.get("id")
        }
        if sync_hashes:
            self.sync_file_hashes(dry_run=False)
        return graph_file

    def _recall_top_nodes_compact(self, query: str = "", top_k: int = 5) -> List[Dict[str, Any]]:
        """Recall compact summaries of top-ranked active memory nodes from graph.json."""
        gdata = self._load_or_seed_graph()
        nodes = [
            n
            for n in gdata.get("nodes", [])
            if n.get("is_current", True) and n.get("type") != "session"
        ]
        non_seed = [n for n in nodes if str(n.get("id")) not in self.CANONICAL_SEED_NODE_IDS]
        pool = non_seed if non_seed else nodes

        q_words = set(re.findall(r"\w+", (query or "").lower()))

        def _score(n: Dict[str, Any]) -> tuple[float, float, str]:
            imp = float(n.get("importance", 0.5))
            upd = str(n.get("updated_at") or n.get("created_at") or "")
            if not q_words:
                return (0.0, imp, upd)
            text = f"{n.get('id', '')} {n.get('label', '')} {n.get('content', '')} {' '.join(n.get('tags', []))}".lower()
            n_words = set(re.findall(r"\w+", text))
            overlap = len(q_words.intersection(n_words)) / max(1, len(q_words))
            return (overlap, imp, upd)

        pool.sort(key=_score, reverse=True)
        return [
            {
                "id": str(n.get("id", "")),
                "type": str(n.get("type", "fact")),
                "label": str(n.get("label", ""))[:60],
                "snippet": str(n.get("content", ""))[:90],
            }
            for n in pool[:top_k]
        ]

    def _enforce_session_budget(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Guarantee micro-session JSON stays strictly under MAX_SESSION_CAPSULE_BYTES (<2KB)."""
        session["revision"] = max(1, int(session.get("revision", 1)))
        session.setdefault("base_graph_hash", self._last_read_graph_hash)
        session["active_focus"] = str(session.get("active_focus", ""))[:160]
        session["prior_summary"] = str(session.get("prior_summary", ""))[:200]
        recalled = list(session.get("recalled_nodes", []))[: self.MAX_SESSION_RECALLED]
        for rnode in recalled:
            rnode["label"] = str(rnode.get("label", ""))[:60]
            rnode["snippet"] = str(rnode.get("snippet", ""))[:90]
        session["recalled_nodes"] = recalled
        session["next_steps"] = [str(s)[:100] for s in list(session.get("next_steps", []))[:4]]
        session["compounded_node_ids"] = list(dict.fromkeys(session.get("compounded_node_ids", [])))[-6:]

        entries = list(session.get("micro_entries", []))
        while len(entries) > self.MAX_SESSION_ENTRIES:
            evicted = entries.pop(0)
            ev_sum = str(evicted.get("summary", ""))[:60]
            if ev_sum:
                session["prior_summary"] = f"{session.get('prior_summary', '')}; {ev_sum}".strip("; ")[-200:]
        session["micro_entries"] = entries

        session["content_hash"] = self._compute_session_content_hash(session)
        session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))

        while session["capsule_bytes"] > self.MAX_SESSION_CAPSULE_BYTES:
            if len(session["recalled_nodes"]) > 1:
                session["recalled_nodes"].pop()
            elif len(session["micro_entries"]) > 1:
                evicted = session["micro_entries"].pop(0)
                ev_sum = str(evicted.get("summary", ""))[:40]
                if ev_sum:
                    session["prior_summary"] = f"{session.get('prior_summary', '')}; {ev_sum}".strip("; ")[-120:]
            elif len(session["prior_summary"]) > 40:
                session["prior_summary"] = session["prior_summary"][-40:]
            elif len(session["recalled_nodes"]) > 0:
                session["recalled_nodes"].pop()
            elif len(session["next_steps"]) > 0:
                session["next_steps"].pop()
            else:
                break
            session["content_hash"] = self._compute_session_content_hash(session)
            session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))
            session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))

        return session

    def _sync_session_into_graph(self, session: Dict[str, Any]) -> None:
        """Upsert session:<session_id> node and PRECEDES / DERIVES_FROM edges into graph.json."""
        now = datetime.now(timezone.utc).isoformat()
        sid = str(session.get("session_id", ""))
        if not sid:
            return
        snode_id = sid if sid.startswith("session:") else f"session:{sid}"
        entries = session.get("micro_entries", [])
        entry_summaries = "; ".join(str(e.get("summary", "")) for e in entries[-4:] if e.get("summary"))
        status = str(session.get("status", "active"))
        content = (
            f"Micro Session {sid} [{status}] | Focus: {session.get('active_focus') or 'General'} | "
            f"Reads: {session.get('read_count', 0)}, Writes: {session.get('write_count', 0)} | "
            f"Entries: {entry_summaries or session.get('prior_summary') or 'Initialized'}"
        )
        byte_size = len(json.dumps(session, indent=2).encode("utf-8"))
        snode: Dict[str, Any] = {
            "id": snode_id,
            "type": "session",
            "label": f"Micro Session {sid}",
            "content": content[:600],
            "importance": 0.75,
            "tags": ["session", "micro-session", status],
            "valid_from": session.get("started_at", now),
            "valid_to": session.get("ended_at"),
            "is_current": True,
            "created_at": session.get("started_at", now),
            "updated_at": session.get("updated_at", now),
            "metadata": {
                "session_id": sid,
                "prior_session_id": session.get("prior_session_id"),
                "parent_session_id": session.get("prior_session_id"),
                "read_count": session.get("read_count", 0),
                "write_count": session.get("write_count", 0),
                "status": status,
                "byte_size": byte_size,
            },
        }

        gdata = self._load_or_seed_graph()
        nodes = [n for n in gdata.get("nodes", []) if n.get("id") != snode_id]
        nodes.append(snode)
        edges = list(gdata.get("edges", []))
        existing_ids = {str(n.get("id")) for n in nodes if n.get("id")}
        existing_edge_keys = {(e.get("source"), e.get("target"), e.get("relation")) for e in edges}

        prior_sid = session.get("prior_session_id")
        if prior_sid and prior_sid != sid:
            prior_nid = str(prior_sid) if str(prior_sid).startswith("session:") else f"session:{prior_sid}"
            if prior_nid in existing_ids and (prior_nid, snode_id, "PRECEDES") not in existing_edge_keys:
                edges.append(
                    {
                        "source": prior_nid,
                        "target": snode_id,
                        "relation": "PRECEDES",
                        "weight": 1.0,
                        "valid_from": now,
                        "is_current": True,
                    }
                )
                existing_edge_keys.add((prior_nid, snode_id, "PRECEDES"))

        if "concept:tri-graph" in existing_ids and (snode_id, "concept:tri-graph", "RELATES_TO") not in existing_edge_keys:
            edges.append(
                {
                    "source": snode_id,
                    "target": "concept:tri-graph",
                    "relation": "RELATES_TO",
                    "weight": 0.8,
                    "valid_from": now,
                    "is_current": True,
                }
            )
            existing_edge_keys.add((snode_id, "concept:tri-graph", "RELATES_TO"))

        for cid in session.get("compounded_node_ids", []):
            if cid in existing_ids and cid != snode_id and (cid, snode_id, "DERIVES_FROM") not in existing_edge_keys:
                edges.append(
                    {
                        "source": cid,
                        "target": snode_id,
                        "relation": "DERIVES_FROM",
                        "weight": 1.0,
                        "valid_from": now,
                        "is_current": True,
                    }
                )
                existing_edge_keys.add((cid, snode_id, "DERIVES_FROM"))

        gdata["nodes"] = nodes
        gdata["edges"] = edges
        self._save_graph(gdata)

    @_with_memory_lock
    def _persist_session(
        self,
        session: Dict[str, Any],
        *,
        expected_hash: Optional[str] = None,
        auto_merge: bool = True,
    ) -> Dict[str, Any]:
        """Enforce <2KB budget, apply optimistic CAS + auto-merge, and atomically write session files and graph.json."""
        current_file = self.sessions_dir / "current.json"
        if current_file.is_file():
            try:
                disk_sess = json.loads(current_file.read_text(encoding="utf-8"))
            except Exception:
                disk_sess = None
            if isinstance(disk_sess, dict):
                disk_hash = disk_sess.get("content_hash") or self._compute_session_content_hash(disk_sess)
                if expected_hash and expected_hash != disk_hash:
                    raise MemoryHashConflictError(
                        f"HASH_CONFLICT on {current_file}: expected_hash={expected_hash}, actual_hash={disk_hash}",
                        expected_hash=expected_hash,
                        actual_hash=disk_hash,
                    )
                if (
                    self._last_read_session_hash
                    and self._last_read_session_hash != disk_hash
                    and disk_sess.get("session_id") == session.get("session_id")
                ):
                    if not auto_merge:
                        raise MemoryHashConflictError(
                            f"HASH_CONFLICT on {current_file}: base_hash={self._last_read_session_hash}, actual_hash={disk_hash}",
                            expected_hash=self._last_read_session_hash,
                            actual_hash=disk_hash,
                        )
                    # Deterministic set-union auto-merge of concurrent micro-entries
                    merged_entries: List[Dict[str, Any]] = []
                    seen_keys: Set[tuple[str, str, str, str]] = set()
                    for me in list(disk_sess.get("micro_entries", [])) + list(session.get("micro_entries", [])):
                        mkey = (
                            str(me.get("timestamp", "")),
                            str(me.get("kind", "")),
                            str(me.get("summary", "")),
                            str(me.get("node_id") or ""),
                        )
                        if mkey not in seen_keys:
                            seen_keys.add(mkey)
                            merged_entries.append(me)
                    session["micro_entries"] = merged_entries
                    session["compounded_node_ids"] = list(
                        dict.fromkeys(
                            list(disk_sess.get("compounded_node_ids", []))
                            + list(session.get("compounded_node_ids", []))
                        )
                    )
                    session["next_steps"] = list(
                        dict.fromkeys(
                            list(disk_sess.get("next_steps", [])) + list(session.get("next_steps", []))
                        )
                    )[:4]
                    session["read_count"] = max(
                        int(session.get("read_count", 0)), int(disk_sess.get("read_count", 0))
                    )
                    session["write_count"] = max(
                        int(session.get("write_count", 0)),
                        int(disk_sess.get("write_count", 0)),
                        len(merged_entries),
                    )
                    session["revision"] = max(
                        int(session.get("revision", 0)), int(disk_sess.get("revision", 0))
                    )

        session["parent_session_id"] = session.get("prior_session_id")
        session["revision"] = int(session.get("revision", 0)) + 1
        from hath0r_cli.bots.secret_pii_sanitizer import secret_pii_sanitizer

        if isinstance(session.get("focus"), str):
            session["focus"] = secret_pii_sanitizer.redact_text(session["focus"]).sanitized_text
        for me in session.get("micro_entries", []):
            if isinstance(me, dict) and isinstance(me.get("summary"), str):
                me["summary"] = secret_pii_sanitizer.redact_text(me["summary"]).sanitized_text
        if not session.get("base_graph_hash") and self._last_read_graph_hash:
            session["base_graph_hash"] = self._last_read_graph_hash
        session["capsule_bytes"] = 0
        session = self._enforce_session_budget(session)
        session["content_hash"] = self._compute_session_content_hash(session)
        session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))
        if session["capsule_bytes"] > self.MAX_SESSION_CAPSULE_BYTES:
            session = self._enforce_session_budget(session)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(session, indent=2)
        self._atomic_write_text(current_file, payload)
        self._atomic_write_text(self.sessions_dir / "latest.json", payload)
        sid = str(session.get("session_id", "")).replace(":", "_")
        if sid:
            self._atomic_write_text(self.sessions_dir / f"{sid}.json", payload)
        self._last_read_session_hash = session.get("content_hash")
        self._sync_session_into_graph(session)
        return session

    def session_start(
        self,
        focus: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        role: Optional[str] = None,
        force_new: bool = False,
        top_k: int = 5,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Start a new Micro Memory Session (.hath0r/memory/sessions/current.json), reading prior session & graph."""
        now = datetime.now(timezone.utc).isoformat()
        resolved_sid = session_id or f"sess-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        prior_sid: Optional[str] = None
        prior_summary = ""
        for cand in (self.sessions_dir / "latest.json", self.sessions_dir / "current.json"):
            if cand.is_file():
                try:
                    prev = json.loads(cand.read_text(encoding="utf-8"))
                    prior_sid = prev.get("session_id")
                    last_entries = [str(e.get("summary", "")) for e in prev.get("micro_entries", [])[-2:] if e.get("summary")]
                    prior_summary = "; ".join(last_entries) or str(prev.get("active_focus") or prev.get("prior_summary") or "")
                    break
                except Exception:
                    pass

        recalled = self._recall_top_nodes_compact(query=focus or "", top_k=top_k)
        micro_entries: List[Dict[str, Any]] = []
        write_count = 0
        last_write_at: Optional[str] = None
        if focus:
            micro_entries.append(
                {
                    "timestamp": now,
                    "kind": "observation",
                    "summary": f"Started session focus: {focus}"[:240],
                    "tags": ["session-start"],
                    "node_id": None,
                }
            )
            write_count = 1
            last_write_at = now

        resolved_parent = prior_sid if prior_sid != resolved_sid else None
        session: Dict[str, Any] = {
            "schema_version": "hath0r.micro_session/1",
            "session_id": resolved_sid,
            "prior_session_id": resolved_parent,
            "parent_session_id": resolved_parent,
            "revision": 0,
            "content_hash": "",
            "base_graph_hash": self._last_read_graph_hash,
            "task_id": task_id,
            "role": role,
            "repo_name": self.cwd.name,
            "status": "active",
            "started_at": now,
            "updated_at": now,
            "ended_at": None,
            "read_count": 1,
            "write_count": write_count,
            "last_read_at": now,
            "last_write_at": last_write_at,
            "active_focus": (focus or f"Active working session in {self.cwd.name}")[:160],
            "prior_summary": prior_summary[:200],
            "recalled_nodes": recalled,
            "micro_entries": micro_entries,
            "next_steps": [],
            "compounded_node_ids": [],
            "capsule_bytes": 0,
        }

        if not dry_run:
            self._last_read_session_hash = None
            session = self._persist_session(session)
        else:
            session["revision"] = 1
            session["content_hash"] = self._compute_session_content_hash(session)
            session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))

        byte_size = int(session.get("capsule_bytes") or len(json.dumps(session, indent=2).encode("utf-8")))
        return {
            "success": True,
            "dry_run": dry_run,
            "message": f"Started micro memory session '{resolved_sid}' ({byte_size} bytes).",
            "session_file": str(self.sessions_dir / "current.json"),
            "byte_size": byte_size,
            "session": session,
        }

    def session_read(
        self,
        focus: Optional[str] = None,
        note: Optional[str] = None,
        top_k: int = 5,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Read the active Micro Memory Session capsule, auto-starting if absent."""
        resolved_focus = focus or note
        current_file = self.sessions_dir / "current.json"
        if not current_file.is_file():
            return self.session_start(focus=resolved_focus, top_k=top_k, dry_run=dry_run)

        try:
            session = json.loads(current_file.read_text(encoding="utf-8"))
            if not isinstance(session, dict):
                return self.session_start(focus=resolved_focus, top_k=top_k, dry_run=dry_run)
        except Exception:
            return self.session_start(focus=resolved_focus, top_k=top_k, dry_run=dry_run)

        self._last_read_session_hash = session.get("content_hash") or self._compute_session_content_hash(session)
        now = datetime.now(timezone.utc).isoformat()
        if focus:
            session["active_focus"] = focus[:160]
        session["recalled_nodes"] = self._recall_top_nodes_compact(
            query=resolved_focus or str(session.get("active_focus", "")),
            top_k=top_k,
        )
        session["base_graph_hash"] = self._last_read_graph_hash
        session["read_count"] = int(session.get("read_count", 0)) + 1
        session["last_read_at"] = now
        session["updated_at"] = now

        if not dry_run:
            session = self._persist_session(session)
        else:
            session["content_hash"] = self._compute_session_content_hash(session)
            session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))

        byte_size = int(session.get("capsule_bytes") or len(json.dumps(session, indent=2).encode("utf-8")))
        return {
            "success": True,
            "dry_run": dry_run,
            "message": f"Read micro memory session '{session.get('session_id')}' (reads={session.get('read_count')}, writes={session.get('write_count')}, {byte_size} bytes).",
            "session_file": str(current_file),
            "byte_size": byte_size,
            "session": session,
        }

    def session_write(
        self,
        summary: str = "",
        kind: str = "observation",
        tags: Optional[List[str]] = None,
        focus: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        node_id: Optional[str] = None,
        ref_node_id: Optional[str] = None,
        expected_hash: Optional[str] = None,
        auto_merge: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Append a compact micro-memory entry to the active session and sync into graph.json."""
        resolved_node_id = node_id or ref_node_id
        current_file = self.sessions_dir / "current.json"
        if not current_file.is_file():
            start_res = self.session_start(focus=focus or summary[:120], dry_run=dry_run)
            session = dict(start_res["session"])
        else:
            try:
                session = json.loads(current_file.read_text(encoding="utf-8"))
                if not isinstance(session, dict):
                    session = dict(self.session_start(focus=focus or summary[:120], dry_run=dry_run)["session"])
            except Exception:
                session = dict(self.session_start(focus=focus or summary[:120], dry_run=dry_run)["session"])

        if self._last_read_session_hash is None:
            self._last_read_session_hash = session.get("content_hash") or self._compute_session_content_hash(session)

        now = datetime.now(timezone.utc).isoformat()
        if int(session.get("read_count", 0)) < 1:
            session["read_count"] = 1
            session["last_read_at"] = now

        clean_tags = [t.strip().lower() for t in (tags or []) if t and t.strip()]
        entry = {
            "timestamp": now,
            "kind": (kind or "observation").lower(),
            "summary": summary[:240],
            "tags": clean_tags,
            "node_id": resolved_node_id,
        }
        entries = list(session.get("micro_entries", []))
        entries.append(entry)
        session["micro_entries"] = entries
        session["write_count"] = int(session.get("write_count", 0)) + 1
        session["last_write_at"] = now
        session["updated_at"] = now
        if focus:
            session["active_focus"] = focus[:160]
        if next_steps is not None:
            session["next_steps"] = [str(s)[:100] for s in next_steps[:4]]
        if resolved_node_id:
            cids = list(session.get("compounded_node_ids", []))
            if resolved_node_id not in cids:
                cids.append(resolved_node_id)
            session["compounded_node_ids"] = cids

        if not dry_run:
            try:
                session = self._persist_session(
                    session, expected_hash=expected_hash, auto_merge=auto_merge
                )
            except MemoryHashConflictError as exc:
                return {
                    "success": False,
                    "error_code": "HASH_CONFLICT",
                    "error": str(exc),
                    "expected_hash": exc.expected_hash,
                    "actual_hash": exc.actual_hash,
                    "session_file": str(current_file),
                }
        else:
            session["content_hash"] = self._compute_session_content_hash(session)
            session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))

        byte_size = int(session.get("capsule_bytes") or len(json.dumps(session, indent=2).encode("utf-8")))
        return {
            "success": True,
            "dry_run": dry_run,
            "message": f"Wrote micro-entry to session '{session.get('session_id')}' (reads={session.get('read_count')}, writes={session.get('write_count')}, {byte_size} bytes).",
            "session_file": str(current_file),
            "byte_size": byte_size,
            "entry": entry,
            "session": session,
        }

    def session_end(
        self,
        summary: Optional[str] = None,
        next_steps: Optional[List[str]] = None,
        sync_agentgraph: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Flush and finalize the active Micro Memory Session into .hath0r/memory/sessions/ and graph.json."""
        current_file = self.sessions_dir / "current.json"
        if not current_file.is_file():
            session = dict(self.session_start(focus=summary or f"Session completed in {self.cwd.name}", dry_run=dry_run)["session"])
        else:
            try:
                session = json.loads(current_file.read_text(encoding="utf-8"))
                if not isinstance(session, dict):
                    session = dict(self.session_start(focus=summary or f"Session completed in {self.cwd.name}", dry_run=dry_run)["session"])
            except Exception:
                session = dict(self.session_start(focus=summary or f"Session completed in {self.cwd.name}", dry_run=dry_run)["session"])

        if self._last_read_session_hash is None:
            self._last_read_session_hash = session.get("content_hash") or self._compute_session_content_hash(session)

        now = datetime.now(timezone.utc).isoformat()
        if int(session.get("read_count", 0)) < 1:
            session["read_count"] = 1
            session["last_read_at"] = now

        entries = list(session.get("micro_entries", []))
        if summary:
            entries.append(
                {
                    "timestamp": now,
                    "kind": "milestone",
                    "summary": summary[:240],
                    "tags": ["session-end"],
                    "node_id": None,
                }
            )
            session["write_count"] = int(session.get("write_count", 0)) + 1
            session["last_write_at"] = now
        elif int(session.get("write_count", 0)) < 1:
            entries.append(
                {
                    "timestamp": now,
                    "kind": "milestone",
                    "summary": f"Completed micro memory session {session.get('session_id')}",
                    "tags": ["session-end"],
                    "node_id": None,
                }
            )
            session["write_count"] = 1
            session["last_write_at"] = now

        session["micro_entries"] = entries
        if next_steps is not None:
            session["next_steps"] = [str(s)[:100] for s in next_steps[:4]]
        session["status"] = "completed"
        session["ended_at"] = now
        session["updated_at"] = now

        ag_synced = False
        if not dry_run:
            session = self._persist_session(session)
            if sync_agentgraph:
                try:
                    from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

                    ag_res = AgentGraphBot(cwd=self.cwd).sync(persist=True, dry_run=False)
                    ag_synced = bool(ag_res.get("success", False))
                except Exception:
                    ag_synced = False
        else:
            session["content_hash"] = self._compute_session_content_hash(session)
            session["capsule_bytes"] = len(json.dumps(session, indent=2).encode("utf-8"))

        byte_size = int(session.get("capsule_bytes") or len(json.dumps(session, indent=2).encode("utf-8")))
        return {
            "success": True,
            "dry_run": dry_run,
            "message": f"Flushed micro memory session '{session.get('session_id')}' ({byte_size} bytes).",
            "session_file": str(current_file),
            "byte_size": byte_size,
            "agentgraph_synced": ag_synced,
            "session": session,
        }

    def session_status(self) -> Dict[str, Any]:
        """Inspect the active or latest Micro Memory Session read/write verification status."""
        current_file = self.sessions_dir / "current.json"
        latest_file = self.sessions_dir / "latest.json"
        target_file = current_file if current_file.is_file() else latest_file

        if not target_file.is_file():
            return {
                "success": True,
                "exists": False,
                "session_id": None,
                "prior_session_id": None,
                "revision": 0,
                "content_hash": None,
                "base_graph_hash": None,
                "status": "missing",
                "read_count": 0,
                "write_count": 0,
                "read_verified": False,
                "write_verified": False,
                "byte_size": 0,
                "max_bytes": self.MAX_SESSION_CAPSULE_BYTES,
                "within_budget": True,
                "file": str(current_file),
                "session": None,
            }

        try:
            raw = target_file.read_text(encoding="utf-8")
            session = json.loads(raw)
            read_count = int(session.get("read_count", 0))
            write_count = int(session.get("write_count", 0))
            byte_size = len(raw.encode("utf-8"))
            return {
                "success": True,
                "exists": True,
                "session_id": session.get("session_id"),
                "prior_session_id": session.get("prior_session_id"),
                "revision": int(session.get("revision", 1)),
                "content_hash": session.get("content_hash") or self._compute_session_content_hash(session),
                "base_graph_hash": session.get("base_graph_hash"),
                "status": session.get("status", "active"),
                "read_count": read_count,
                "write_count": write_count,
                "read_verified": read_count >= 1,
                "write_verified": write_count >= 1,
                "active_focus": session.get("active_focus", ""),
                "entries_count": len(session.get("micro_entries", [])),
                "recalled_nodes_count": len(session.get("recalled_nodes", [])),
                "byte_size": byte_size,
                "max_bytes": self.MAX_SESSION_CAPSULE_BYTES,
                "within_budget": byte_size <= self.MAX_SESSION_CAPSULE_BYTES,
                "file": str(target_file),
                "session": session,
            }
        except Exception as exc:
            return {
                "success": False,
                "exists": False,
                "session_id": None,
                "prior_session_id": None,
                "revision": 0,
                "content_hash": None,
                "base_graph_hash": None,
                "status": "corrupt",
                "read_count": 0,
                "write_count": 0,
                "read_verified": False,
                "write_verified": False,
                "byte_size": 0,
                "max_bytes": self.MAX_SESSION_CAPSULE_BYTES,
                "within_budget": False,
                "file": str(target_file),
                "error": str(exc),
                "session": None,
            }

    def ensure_gitignore_unignores_graphs(
        self,
        dry_run: bool = False,
        create_if_missing: bool = False,
    ) -> Dict[str, Any]:
        """Ensure .gitignore never ignores .hath0r/memory, .hath0r/agentgraph, .hath0r/graphs, .hath0r/state/cache, or .hath0r/state/context."""
        gitignore_file = self.cwd / ".gitignore"
        has_git = (self.cwd / ".git").exists()

        if not gitignore_file.is_file() and not create_if_missing and not has_git:
            return {
                "success": True,
                "updated": False,
                "gitignore_file": str(gitignore_file),
                "rewritten_rules": [],
                "removed_rules": [],
                "appended_negations": [],
            }

        raw_text = gitignore_file.read_text(encoding="utf-8", errors="ignore") if gitignore_file.is_file() else ""
        lines = raw_text.splitlines()

        forbidden_exact = {
            ".hath0r/memory",
            ".hath0r/memory/",
            ".hath0r/memory/*",
            ".hath0r/memory/**",
            ".hath0r/memory/sessions",
            ".hath0r/memory/sessions/",
            ".hath0r/memory/sessions/*",
            ".hath0r/memory/sessions/**",
            ".hath0r/memory/graph.json",
            ".hath0r/memory/hashes.json",
            ".hath0r/agentgraph",
            ".hath0r/agentgraph/",
            ".hath0r/agentgraph/*",
            ".hath0r/agentgraph/**",
            ".hath0r/agentgraph/snapshot.json",
            ".hath0r/graphs",
            ".hath0r/graphs/",
            ".hath0r/graphs/*",
            ".hath0r/graphs/**",
            ".hath0r/state/cache",
            ".hath0r/state/cache/",
            ".hath0r/state/cache/*",
            ".hath0r/state/cache/**",
            ".hath0r/state/context",
            ".hath0r/state/context/",
            ".hath0r/state/context/*",
            ".hath0r/state/context/**",
            ".agentguard/graph.db",
        }

        new_lines: List[str] = []
        rewritten_rules: List[str] = []
        removed_rules: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("!"):
                new_lines.append(line)
                continue

            normalized = stripped.lstrip("/")
            if normalized in (".hath0r", ".hath0r/"):
                new_lines.append(".hath0r/*")
                rewritten_rules.append(f"{stripped} -> .hath0r/*")
            elif normalized in (".hath0r/state", ".hath0r/state/"):
                new_lines.append(".hath0r/state/*")
                rewritten_rules.append(f"{stripped} -> .hath0r/state/*")
            elif normalized in forbidden_exact:
                removed_rules.append(stripped)
            else:
                new_lines.append(line)

        # Git applies the last matching pattern, so an ignore rule placed after the
        # canonical negations (e.g. a later "*.json") silently re-ignores graph files.
        # Move the negation block back to the end of the file when that happens.
        header = "# Canonical Hath0r Graph Folders (NEVER ignore — CR-MEMORY-COMPOUND-001 & CR-AGENTGRAPH-001)"
        canonical_negations = set(self.CANONICAL_GITIGNORE_NEGATIONS)
        negation_idx = [i for i, ln in enumerate(new_lines) if ln.strip() in canonical_negations]
        rule_idx = [
            i for i, ln in enumerate(new_lines) if ln.strip() and not ln.strip().startswith(("#", "!"))
        ]
        relocated = bool(negation_idx and rule_idx and max(rule_idx) > min(negation_idx))
        if relocated:
            new_lines = [ln for ln in new_lines if ln.strip() not in canonical_negations and ln.strip() != header]
            while new_lines and not new_lines[-1].strip():
                new_lines.pop()

        existing_stripped = {ln.strip() for ln in new_lines}
        missing_negations = [neg for neg in self.CANONICAL_GITIGNORE_NEGATIONS if neg not in existing_stripped]
        if missing_negations:
            if new_lines and new_lines[-1].strip() != "":
                new_lines.append("")
            if header not in existing_stripped:
                new_lines.append(header)
            for neg in missing_negations:
                new_lines.append(neg)

        updated_text = "\n".join(new_lines) + ("\n" if new_lines else "")
        changed = updated_text != raw_text
        if changed and not dry_run:
            self._atomic_write_text(gitignore_file, updated_text)

        return {
            "success": True,
            "updated": changed,
            "gitignore_file": str(gitignore_file),
            "rewritten_rules": rewritten_rules,
            "removed_rules": removed_rules,
            "appended_negations": missing_negations,
            "relocated_negations": relocated,
        }

    def verify_graphs_not_gitignored(self) -> Dict[str, Any]:
        """Verify that no canonical Hath0r cognitive graph folder or file is ignored by Git."""
        import subprocess

        gitignore_file = self.cwd / ".gitignore"
        forbidden_rules: List[str] = []
        ignored_paths: List[str] = []

        if gitignore_file.is_file():
            raw_lines = [
                ln.strip()
                for ln in gitignore_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            ]
            forbidden_exact = {
                ".hath0r",
                ".hath0r/",
                ".hath0r/state",
                ".hath0r/state/",
                ".hath0r/memory",
                ".hath0r/memory/",
                ".hath0r/memory/*",
                ".hath0r/memory/**",
                ".hath0r/memory/sessions",
                ".hath0r/memory/sessions/",
                ".hath0r/memory/sessions/*",
                ".hath0r/memory/sessions/**",
                ".hath0r/memory/graph.json",
                ".hath0r/memory/hashes.json",
                ".hath0r/agentgraph",
                ".hath0r/agentgraph/",
                ".hath0r/agentgraph/*",
                ".hath0r/agentgraph/**",
                ".hath0r/agentgraph/snapshot.json",
                ".hath0r/graphs",
                ".hath0r/graphs/",
                ".hath0r/graphs/*",
                ".hath0r/graphs/**",
                ".hath0r/state/cache",
                ".hath0r/state/cache/",
                ".hath0r/state/cache/*",
                ".hath0r/state/cache/**",
                ".hath0r/state/context",
                ".hath0r/state/context/",
                ".hath0r/state/context/*",
                ".hath0r/state/context/**",
                ".agentguard/graph.db",
            }
            for ln in raw_lines:
                if not ln.startswith("!") and ln.lstrip("/") in forbidden_exact:
                    forbidden_rules.append(ln)

            has_wildcard_hath0r = any(
                not ln.startswith("!")
                and ln.lstrip("/") in (".hath0r/*", ".hath0r/state/*", ".hath0r/*.json", "*.json")
                for ln in raw_lines
            )
            if has_wildcard_hath0r:
                line_set = set(raw_lines)
                for req_neg in (
                    "!.hath0r/memory/**",
                    "!.hath0r/agentgraph/**",
                    "!.hath0r/graphs/**",
                    "!.hath0r/state/cache/**",
                    "!.hath0r/state/context/**",
                ):
                    if req_neg not in line_set:
                        forbidden_rules.append(f"missing_negation:{req_neg}")

        if (self.cwd / ".git").exists():
            try:
                proc = subprocess.run(
                    ["git", "-C", str(self.cwd), "check-ignore", "--no-index", *self.CANONICAL_GRAPH_PATHS],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    for out_line in proc.stdout.strip().splitlines():
                        if out_line.strip():
                            ignored_paths.append(out_line.strip())
            except Exception:
                pass

        if forbidden_rules and not ignored_paths:
            ignored_paths.extend(forbidden_rules)

        graphs_not_ignored = len(ignored_paths) == 0 and len(forbidden_rules) == 0
        return {
            "graphs_not_ignored": graphs_not_ignored,
            "ignored_paths": ignored_paths,
            "forbidden_rules": forbidden_rules,
            "gitignore_file": str(gitignore_file),
        }

    @staticmethod
    def _next_file_revision(prev: Any, sha: Optional[str], floor: int = 1) -> int:
        """Return a monotonic per-file revision: bump when the digest changed, never go backwards."""
        if not isinstance(prev, dict):
            return max(1, floor)
        prev_rev = int(prev.get("revision", 0) or 0)
        if prev.get("sha256") == sha:
            return max(prev_rev, floor, 1)
        return max(prev_rev + 1, floor, 1)

    @_with_memory_lock
    def sync_file_hashes(
        self,
        track_files: Optional[List[str]] = None,
        refresh_source_files: bool = False,
        dry_run: bool = False,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute and persist SHA-256 digests for all .hath0r/memory/ files and referenced source_files.

        When ``expected_revision`` is given, the write is a Compare-And-Swap on hashes.json: it is
        refused with ``HASH_CONFLICT`` if another writer bumped the manifest revision in between.
        """
        hashes_file = self.memory_dir / "hashes.json"
        existing_manifest: Dict[str, Any] = {}
        if hashes_file.is_file():
            try:
                existing_manifest = json.loads(hashes_file.read_text(encoding="utf-8"))
            except Exception:
                existing_manifest = {}

        current_revision = int(existing_manifest.get("revision", 0) or 0)
        if expected_revision is not None and int(expected_revision) != current_revision:
            return {
                "success": False,
                "dry_run": dry_run,
                "error_code": "HASH_CONFLICT",
                "error": (
                    f"HASH_CONFLICT on {hashes_file}: expected_revision={expected_revision}, "
                    f"actual_revision={current_revision}"
                ),
                "hashes_file": str(hashes_file),
                "expected_revision": int(expected_revision),
                "actual_revision": current_revision,
            }

        self.ensure_gitignore_unignores_graphs(dry_run=dry_run)
        if not dry_run:
            agents_file = self.cwd / "AGENTS.md"
            claude_file = self.cwd / "CLAUDE.md"
            if agents_file.is_file():
                try:
                    a_bytes = agents_file.read_bytes()
                    if not claude_file.is_file() or claude_file.read_bytes() != a_bytes:
                        self._atomic_write_text(claude_file, a_bytes.decode("utf-8"))
                except OSError:
                    pass
        now = datetime.now(timezone.utc).isoformat()
        revision = current_revision + 1
        prev_files = existing_manifest.get("files", {})
        if not isinstance(prev_files, dict):
            prev_files = {}
        files_map: Dict[str, Dict[str, Any]] = {}

        if self.memory_dir.is_dir():
            for fpath in sorted(self.memory_dir.rglob("*")):
                if not fpath.is_file():
                    continue
                if fpath.name == "hashes.json" or ".tmp." in fpath.name:
                    continue
                try:
                    rel_path = fpath.relative_to(self.cwd).as_posix()
                except ValueError:
                    rel_path = fpath.name
                raw = fpath.read_bytes()
                f_hash = self._compute_sha256_bytes(raw)
                doc_rev = 1
                f_content_hash = f_hash
                if fpath.suffix == ".json":
                    try:
                        parsed = json.loads(raw.decode("utf-8"))
                        if isinstance(parsed, dict):
                            doc_rev = int(parsed.get("revision", 1))
                            f_content_hash = str(parsed.get("content_hash") or f_hash)
                    except Exception:
                        pass
                files_map[rel_path] = {
                    "sha256": f_hash,
                    "content_hash": f_content_hash,
                    "revision": self._next_file_revision(prev_files.get(rel_path), f_hash, doc_rev),
                    "byte_size": len(raw),
                    "updated_at": now,
                }

        # Collect source_files from graph.json nodes + existing manifest + track_files
        source_refs: Dict[str, List[str]] = {}
        recorded_source_hashes: Dict[str, str] = {}
        prev_sources = existing_manifest.get("source_files", {})
        if isinstance(prev_sources, dict):
            for s_rel, s_info in prev_sources.items():
                norm_rel = Path(s_rel).as_posix()
                source_refs.setdefault(norm_rel, [])
                if isinstance(s_info, dict) and s_info.get("sha256"):
                    recorded_source_hashes[norm_rel] = str(s_info["sha256"])

        graph_file = self.memory_dir / "graph.json"
        gdata: Optional[Dict[str, Any]] = None
        graph_modified = False
        if graph_file.is_file():
            try:
                gdata = json.loads(graph_file.read_text(encoding="utf-8"))
            except Exception:
                gdata = None

        if isinstance(gdata, dict):
            for n in gdata.get("nodes", []):
                if not n.get("is_current", True):
                    continue
                meta = n.get("metadata") or {}
                sfiles = meta.get("source_files")
                if isinstance(sfiles, dict):
                    for s_rel, s_hash in list(sfiles.items()):
                        norm_rel = Path(s_rel).as_posix()
                        source_refs.setdefault(norm_rel, []).append(str(n.get("id", "")))
                        if refresh_source_files:
                            curr_h = self._compute_file_sha256((self.cwd / norm_rel).resolve())
                            if curr_h and curr_h != s_hash:
                                sfiles[s_rel] = curr_h
                                recorded_source_hashes[norm_rel] = curr_h
                                graph_modified = True
                            elif s_hash:
                                recorded_source_hashes[norm_rel] = str(s_hash)
                        elif s_hash:
                            recorded_source_hashes[norm_rel] = str(s_hash)

        explicit_tracked = set()
        for tf in track_files or []:
            if not tf:
                continue
            tf_path = Path(tf)
            if tf_path.is_absolute():
                try:
                    norm_rel = tf_path.resolve().relative_to(self.cwd).as_posix()
                except ValueError:
                    norm_rel = tf_path.name
            else:
                norm_rel = tf_path.as_posix()
            source_refs.setdefault(norm_rel, [])
            explicit_tracked.add(norm_rel)

        if graph_modified and gdata is not None and not dry_run:
            gdata["revision"] = int(gdata.get("revision", 0)) + 1
            gdata["updated_at"] = now
            gdata["content_hash"] = self._compute_graph_content_hash(gdata)
            raw_g = json.dumps(gdata, indent=2)
            self._atomic_write_text(graph_file, raw_g)
            g_rel = graph_file.relative_to(self.cwd).as_posix()
            g_sha = self._compute_sha256_bytes(raw_g.encode("utf-8"))
            files_map[g_rel] = {
                "sha256": g_sha,
                "content_hash": gdata["content_hash"],
                "revision": self._next_file_revision(prev_files.get(g_rel), g_sha, int(gdata["revision"])),
                "byte_size": len(raw_g.encode("utf-8")),
                "updated_at": now,
            }

        source_files_map: Dict[str, Dict[str, Any]] = {}
        for rel_path in sorted(source_refs.keys()):
            abs_p = (self.cwd / rel_path).resolve()
            if not abs_p.is_file() and not source_refs[rel_path] and rel_path not in explicit_tracked:
                continue
            disk_sha = self._compute_file_sha256(abs_p)
            if rel_path in explicit_tracked or refresh_source_files or rel_path not in recorded_source_hashes:
                baseline_sha = disk_sha
            else:
                baseline_sha = recorded_source_hashes.get(rel_path) or disk_sha
            source_files_map[rel_path] = {
                "sha256": baseline_sha,
                "revision": self._next_file_revision(
                    prev_sources.get(rel_path) if isinstance(prev_sources, dict) else None, baseline_sha
                ),
                "byte_size": abs_p.stat().st_size if abs_p.is_file() else 0,
                "exists": abs_p.is_file(),
                "referenced_by": sorted(set(source_refs[rel_path])),
                "updated_at": now,
            }

        manifest = {
            "schema_version": "hath0r.memory_hashes/1",
            "repo_name": self.cwd.name,
            "revision": revision,
            "updated_at": now,
            "files": files_map,
            "source_files": source_files_map,
        }
        if not dry_run:
            self._atomic_write_text(hashes_file, json.dumps(manifest, indent=2))

        return {
            "success": True,
            "dry_run": dry_run,
            "hashes_file": str(hashes_file),
            "revision": revision,
            "tracked_files_count": len(files_map),
            "source_files_count": len(source_files_map),
            "manifest": manifest,
        }

    def verify_file_hashes(self) -> Dict[str, Any]:
        """Verify all .hath0r/memory/ file hashes, referenced source_files digests, and gitignore graph rules."""
        hashes_file = self.memory_dir / "hashes.json"
        gitignore_check = self.verify_graphs_not_gitignored()
        graphs_not_ignored = bool(gitignore_check.get("graphs_not_ignored", True))

        if not hashes_file.is_file():
            return {
                "success": False,
                "verified": False,
                "manifest_exists": False,
                "hashes_file": str(hashes_file),
                "graphs_not_ignored": graphs_not_ignored,
                "ignored_graph_paths": gitignore_check.get("ignored_paths", []),
                "mismatched_files": [],
                "missing_files": [str(hashes_file)],
                "stale_source_files": [],
                "error": f"Missing file hash manifest at {hashes_file}. Run 'hath0r memory hash --sync' or 'hath0r memory init'.",
            }

        try:
            manifest = json.loads(hashes_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "success": False,
                "verified": False,
                "manifest_exists": True,
                "hashes_file": str(hashes_file),
                "graphs_not_ignored": graphs_not_ignored,
                "ignored_graph_paths": gitignore_check.get("ignored_paths", []),
                "mismatched_files": [str(hashes_file)],
                "missing_files": [],
                "stale_source_files": [],
                "error": f"Corrupt hashes.json at {hashes_file}: {exc}",
            }

        mismatched_files: List[Dict[str, Any]] = []
        missing_files: List[str] = []
        stale_source_files: List[Dict[str, Any]] = []

        # 1. Verify internal content_hash of graph.json and sessions/current.json
        graph_file = self.memory_dir / "graph.json"
        graph_content_hash_valid = True
        if graph_file.is_file():
            try:
                gdata = json.loads(graph_file.read_text(encoding="utf-8"))
                expected_gh = gdata.get("content_hash")
                actual_gh = self._compute_graph_content_hash(gdata)
                if expected_gh and expected_gh != actual_gh:
                    graph_content_hash_valid = False
                    mismatched_files.append(
                        {
                            "file": ".hath0r/memory/graph.json#content_hash",
                            "expected": expected_gh,
                            "actual": actual_gh,
                        }
                    )
            except Exception:
                graph_content_hash_valid = False
                mismatched_files.append(
                    {
                        "file": ".hath0r/memory/graph.json",
                        "expected": "valid_json",
                        "actual": "corrupt_json",
                    }
                )

        current_sess_file = self.sessions_dir / "current.json"
        session_content_hash_valid = True
        if current_sess_file.is_file():
            try:
                sdata = json.loads(current_sess_file.read_text(encoding="utf-8"))
                expected_sh = sdata.get("content_hash")
                actual_sh = self._compute_session_content_hash(sdata)
                if expected_sh and expected_sh != actual_sh:
                    session_content_hash_valid = False
                    mismatched_files.append(
                        {
                            "file": ".hath0r/memory/sessions/current.json#content_hash",
                            "expected": expected_sh,
                            "actual": actual_sh,
                        }
                    )
            except Exception:
                session_content_hash_valid = False
                mismatched_files.append(
                    {
                        "file": ".hath0r/memory/sessions/current.json",
                        "expected": "valid_json",
                        "actual": "corrupt_json",
                    }
                )

        # 2. Verify all tracked .hath0r/memory/* files in manifest["files"]
        files_map = manifest.get("files", {})
        for rel_path, info in files_map.items():
            abs_p = (self.cwd / rel_path).resolve()
            if not abs_p.is_file():
                missing_files.append(rel_path)
                continue
            actual_sha = self._compute_file_sha256(abs_p)
            expected_sha = info.get("sha256")
            if expected_sha and actual_sha != expected_sha:
                mismatched_files.append(
                    {
                        "file": rel_path,
                        "expected": expected_sha,
                        "actual": actual_sha,
                    }
                )

        # 3. Verify source_files from both manifest["source_files"] and active nodes in graph.json
        checked_sources: Dict[str, tuple[Optional[str], List[str]]] = {}
        for rel_path, sinfo in manifest.get("source_files", {}).items():
            checked_sources[rel_path] = (sinfo.get("sha256"), list(sinfo.get("referenced_by", [])))

        if graph_file.is_file():
            try:
                gdata = json.loads(graph_file.read_text(encoding="utf-8"))
                for n in gdata.get("nodes", []):
                    if not n.get("is_current", True):
                        continue
                    sfiles = (n.get("metadata") or {}).get("source_files")
                    if isinstance(sfiles, dict):
                        for s_rel, s_sha in sfiles.items():
                            norm_rel = Path(s_rel).as_posix()
                            prev_sha, refs = checked_sources.get(norm_rel, (s_sha, []))
                            nid = str(n.get("id", ""))
                            if nid and nid not in refs:
                                refs.append(nid)
                            checked_sources[norm_rel] = (s_sha or prev_sha, refs)
            except Exception:
                pass

        for rel_path, (expected_sha, refs) in sorted(checked_sources.items()):
            abs_p = (self.cwd / rel_path).resolve()
            if not abs_p.is_file():
                stale_source_files.append(
                    {
                        "file": rel_path,
                        "expected": expected_sha,
                        "actual": None,
                        "reason": "missing_source_file",
                        "referenced_by": refs,
                    }
                )
                continue
            actual_sha = self._compute_file_sha256(abs_p)
            if expected_sha and actual_sha != expected_sha:
                stale_source_files.append(
                    {
                        "file": rel_path,
                        "expected": expected_sha,
                        "actual": actual_sha,
                        "reason": "source_file_modified",
                        "referenced_by": refs,
                    }
                )

        verified = (
            len(mismatched_files) == 0
            and len(missing_files) == 0
            and len(stale_source_files) == 0
            and graph_content_hash_valid
            and session_content_hash_valid
            and graphs_not_ignored
        )
        err: Optional[str] = None
        if not graphs_not_ignored:
            err = (
                f"CR-MEMORY-COMPOUND-001: Graph folders are ignored in .gitignore "
                f"({', '.join(gitignore_check.get('ignored_paths', []))}). "
                "Run 'hath0r memory init' or 'hath0r memory hash --sync' to un-ignore graph folders."
            )
        elif not verified:
            err = (
                f"CR-MEMORY-COMPOUND-001: Memory file hash verification failed "
                f"(mismatched={len(mismatched_files)}, missing={len(missing_files)}, "
                f"stale_source_files={len(stale_source_files)}). "
                "Run 'hath0r memory hash --sync' or re-compound stale knowledge nodes."
            )

        return {
            "success": verified,
            "verified": verified,
            "manifest_exists": True,
            "hashes_file": str(hashes_file),
            "revision": manifest.get("revision", 0),
            "tracked_files_count": len(files_map),
            "source_files_count": len(checked_sources),
            "graphs_not_ignored": graphs_not_ignored,
            "ignored_graph_paths": gitignore_check.get("ignored_paths", []),
            "mismatched_files": mismatched_files,
            "missing_files": missing_files,
            "stale_source_files": stale_source_files,
            "graph_content_hash_valid": graph_content_hash_valid,
            "session_content_hash_valid": session_content_hash_valid,
            "error": err,
        }


    def initialize_memory(self, dry_run: bool = False) -> Dict[str, Any]:
        """Initialize the core Hath0r memory spaces, micro session capsule, and SHA-256 hash manifest."""
        core_file = self.memory_dir / "core_rules.md"
        arch_file = self.memory_dir / "architecture.md"
        graph_file = self.memory_dir / "graph.json"
        current_session_file = self.sessions_dir / "current.json"
        hashes_file = self.memory_dir / "hashes.json"

        core_content = (
            "# Core Hath0r Rules\n"
            "1. CLI-First (CR-CLI-ENTRY-001): Always start with the CLI capabilities before improvising.\n"
            "2. Memory Compounding (CR-MEMORY-COMPOUND-001): Every session must read/write a micro memory session and every task must compound knowledge into .hath0r/memory/graph.json prior to announcing complete.\n"
            "3. Bots not Daemons: Background tasks are bots/factories.\n"
            "4. Hyper-Context: Always traverse the defined context paths (playbooks, procedures).\n"
            "5. Promotion Path: local -> development -> testing -> staging -> master.\n"
            "6. Automatic Task Evaluation (CR-TASK-EVAL-001): Every task must execute and pass the 4-tier automatic task evaluation gate (hath0r evals run / hath0r evals verify, R_task >= 0.80) prior to announcing complete.\n"
        )

        arch_content = (
            "# Canonical Architecture\n"
            "The HATH0R-CLI repository acts as the OpenSource Control Tower.\n"
            "Agents orienting to any Hath0r app MUST read/write `.hath0r/memory/sessions/current.json` first "
            "and compound task learnings into `.hath0r/memory/graph.json` prior to completion.\n"
        )

        gdata = self._load_or_seed_graph()

        if not dry_run:
            if not core_file.exists():
                self._atomic_write_text(core_file, core_content)
            if not arch_file.exists():
                self._atomic_write_text(arch_file, arch_content)
            self._save_graph(gdata, sync_hashes=False)
            if not current_session_file.is_file():
                self.session_start(focus=f"Initialized local memory space for {self.cwd.name}", dry_run=False)
            self.sync_file_hashes(dry_run=False)
            gdata = self._load_or_seed_graph()

        return {
            "success": True,
            "message": "Initialized core memory spaces, micro session store, and SHA-256 hash manifest.",
            "files": [
                str(core_file),
                str(arch_file),
                str(graph_file),
                str(current_session_file),
                str(hashes_file),
            ],
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

        return {
            "success": True,
            "topic": topic,
            "content": target_file.read_text(encoding="utf-8"),
            "sha256": self._compute_file_sha256(target_file),
        }

    @_with_memory_lock
    def update_memory(
        self,
        topic: str,
        content: str,
        dry_run: bool = False,
        expected_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update or create a specific memory topic and sync into graph.json.

        ``expected_hash`` is the topic file's current ``sha256:<hex>`` digest (or ``"absent"`` for a
        new topic); a mismatch is refused with ``HASH_CONFLICT`` instead of overwriting.
        """
        actual_topic = "core_rules" if topic in ("rules", "core") else topic
        target_file = self.memory_dir / f"{actual_topic}.md"
        if expected_hash:
            actual_hash = self._compute_file_sha256(target_file) or "absent"
            if expected_hash != actual_hash:
                return {
                    "success": False,
                    "error_code": "HASH_CONFLICT",
                    "error": f"HASH_CONFLICT on {target_file}: expected_hash={expected_hash}, actual_hash={actual_hash}",
                    "expected_hash": expected_hash,
                    "actual_hash": actual_hash,
                    "file": str(target_file),
                }
        if not dry_run:
            self._atomic_write_text(target_file, content)
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
            self.session_write(
                summary=f"Updated memory topic '{actual_topic}'",
                kind="observation",
                tags=["topic", actual_topic],
                node_id=topic_id,
                dry_run=False,
            )

        return {
            "success": True,
            "message": f"Updated memory topic '{topic}'.",
            "file": str(target_file),
            "sha256": None if dry_run else self._compute_file_sha256(target_file),
        }

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
        source_files: Optional[List[str]] = None,
        expected_hash: Optional[str] = None,
        auto_merge: bool = True,
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

        resolved_meta: Dict[str, Any] = dict(metadata or {})
        if source_files:
            sf_map: Dict[str, Optional[str]] = dict(resolved_meta.get("source_files") or {})
            for sf in source_files:
                if not sf:
                    continue
                sf_path = Path(sf)
                if sf_path.is_absolute():
                    abs_sf = sf_path.resolve()
                    try:
                        rel_sf = abs_sf.relative_to(self.cwd).as_posix()
                    except ValueError:
                        rel_sf = abs_sf.name
                else:
                    rel_sf = sf_path.as_posix()
                    abs_sf = (self.cwd / rel_sf).resolve()
                sf_map[rel_sf] = self._compute_file_sha256(abs_sf)
            resolved_meta["source_files"] = sf_map

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
            "metadata": resolved_meta,
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
        gdata = self._load_or_seed_graph(record_read=(self._last_read_graph_hash is None))
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
        try:
            graph_file = self._save_graph(
                gdata, expected_hash=expected_hash, auto_merge=auto_merge
            )
        except MemoryHashConflictError as exc:
            return {
                "success": False,
                "error_code": "HASH_CONFLICT",
                "error": str(exc),
                "expected_hash": exc.expected_hash,
                "actual_hash": exc.actual_hash,
                "conflicting_ids": exc.conflicting_ids,
                "graph_file": str(self.memory_dir / "graph.json"),
            }

        # Record a micro-session write and link compounded node to active session
        session_res = self.session_write(
            summary=f"Compounded {resolved_id}: {label}",
            kind="compound",
            tags=resolved_tags,
            node_id=resolved_id,
            dry_run=False,
        )

        # Run autonomous reflection consolidation
        reflection_res = self.reflect_memory(dry_run=False)

        # Ensure hashes.json reflects final post-reflection & post-session state
        hash_sync = self.sync_file_hashes(track_files=source_files, dry_run=False)

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
            "hashes_file": hash_sync.get("hashes_file"),
            "content_hash": self._last_read_graph_hash,
            "node": node_entry,
            "edges_added": edges_added,
            "reflection": reflection_res,
            "micro_session": session_res.get("session"),
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
        require_session: bool = True,
        require_hashes: bool = True,
    ) -> Dict[str, Any]:
        """Verify that .hath0r/memory/graph.json contains compounded task knowledge, micro session R/W, and SHA-256 hash integrity."""
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
                "session_read_verified": False,
                "session_write_verified": False,
                "hashes_verified": False,
                "hash_status": None,
                "session": None,
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
                "session_read_verified": False,
                "session_write_verified": False,
                "hashes_verified": False,
                "hash_status": None,
                "session": None,
                "error": f"Corrupt MemoryGraph JSON at {graph_file}: {exc}",
            }

        nodes = list(gdata.get("nodes", []))
        edges = list(gdata.get("edges", []))
        compounded_nodes: List[Dict[str, Any]] = []

        for n in nodes:
            nid = str(n.get("id", ""))
            if not nid or nid in self.CANONICAL_SEED_NODE_IDS:
                continue
            if n.get("type") == "session":
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
        has_compounded_nodes = len(compounded_nodes) > 0
        latest = compounded_nodes[0] if compounded_nodes else None

        s_status = self.session_status()
        read_ok = bool(s_status.get("read_verified"))
        write_ok = bool(s_status.get("write_verified"))
        session_ok = (read_ok and write_ok) if require_session else True

        hash_status = self.verify_file_hashes()
        hash_ok = bool(hash_status.get("verified")) if require_hashes else True
        graphs_not_ignored = bool(hash_status.get("graphs_not_ignored", True))

        is_compounded = has_compounded_nodes and session_ok and hash_ok and graphs_not_ignored
        err_msg: Optional[str] = None
        if not has_compounded_nodes:
            err_msg = (
                "CR-MEMORY-COMPOUND-001: No task knowledge compounded in .hath0r/memory/graph.json beyond static seeds. "
                "Run 'hath0r memory compound' prior to announcing complete."
            )
        elif not session_ok:
            err_msg = (
                f"CR-MEMORY-COMPOUND-001: Micro memory session read/write gate failed "
                f"(read_count={s_status.get('read_count', 0)}, write_count={s_status.get('write_count', 0)}). "
                "Run 'hath0r memory session read' and 'hath0r memory session write' prior to announcing complete."
            )
        elif not graphs_not_ignored or not hash_ok:
            err_msg = str(hash_status.get("error") or "CR-MEMORY-COMPOUND-001: Memory file hash verification failed.")

        return {
            "success": is_compounded,
            "compounded": is_compounded,
            "graph_exists": True,
            "graph_file": str(graph_file),
            "revision": int(gdata.get("revision", 1)),
            "content_hash": gdata.get("content_hash") or self._compute_graph_content_hash(gdata),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "compounded_nodes_count": len(compounded_nodes),
            "latest_node": latest,
            "session_read_verified": read_ok,
            "session_write_verified": write_ok,
            "hashes_verified": bool(hash_status.get("verified")),
            "graphs_not_ignored": graphs_not_ignored,
            "hash_status": hash_status,
            "session": s_status,
            "error": err_msg,
        }

    def ensure_all_repos(
        self,
        root_dir: Optional[Path | str] = None,
        sync_agentgraph: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Discover all active repositories under root_dir and ensure .hath0r/memory/graph.json, sessions/, hashes.json, and .gitignore graph rules are provisioned."""
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
        from hath0r_cli.mcp import ensure_repo_mcp_config

        for rpath in repo_paths:
            ensure_repo_mcp_config(rpath, sync_cfg=True, dry_run=dry_run)
            rbot = MemoryManagerBot(cwd=rpath)
            rbot.ensure_gitignore_unignores_graphs(dry_run=dry_run)
            slug = re.sub(r"[^a-z0-9]+", "-", rpath.name.lower()).strip("-") or "repo"
            summary = f"Repository '{rpath.name}' initialized with canonical .hath0r/memory/graph.json, micro sessions, and SHA-256 hashes under CR-MEMORY-COMPOUND-001."
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
            if not dry_run:
                from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

                ebot = TaskEvaluatorBot(cwd=rpath)
                ebot.ensure_repo_eval_setup(run_eval=True, sync_agents_md=True, dry_run=False)
                rbot.session_read(focus=f"Repository orientation verified for {rpath.name}", dry_run=False)
                rbot.sync_file_hashes(refresh_source_files=True, dry_run=False)
            ver = rbot.verify_compounded() if not dry_run else {
                "compounded": True,
                "total_nodes": 5,
                "total_edges": 4,
                "session_read_verified": True,
                "session_write_verified": True,
                "hashes_verified": True,
                "graphs_not_ignored": True,
            }
            results.append(
                {
                    "repo": str(rpath.relative_to(base)) if rpath != base else rpath.name,
                    "path": str(rpath),
                    "memory_dir": str(rpath / ".hath0r" / "memory"),
                    "graph_file": str(rpath / ".hath0r" / "memory" / "graph.json"),
                    "session_file": str(rpath / ".hath0r" / "memory" / "sessions" / "current.json"),
                    "hashes_file": str(rpath / ".hath0r" / "memory" / "hashes.json"),
                    "compounded": ver.get("compounded", False),
                    "session_read_verified": ver.get("session_read_verified", False),
                    "session_write_verified": ver.get("session_write_verified", False),
                    "hashes_verified": ver.get("hashes_verified", False),
                    "graphs_not_ignored": ver.get("graphs_not_ignored", False),
                    "total_nodes": ver.get("total_nodes", 0),
                    "total_edges": ver.get("total_edges", 0),
                    "agentgraph_synced": comp_res.get("agentgraph_synced", False),
                }
            )

        ignored_repos = [r["repo"] for r in results if not r["graphs_not_ignored"]]
        return {
            "success": True,
            "dry_run": dry_run,
            "root_dir": str(base),
            "repos_count": len(results),
            "repos": results,
            "graphs_not_ignored": not ignored_repos,
            "ignored_repos": ignored_repos,
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
