"""Persistent SQLite FTS5 & Vector Index Cache for Hath0r KnowledgeBase."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DocumentEntry:
    """Document record representation in knowledgebase index."""

    path: str
    title: str
    category: str
    sha256: str
    mtime: float
    content: str
    tags: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Search hit result from knowledgebase index."""

    path: str
    title: str
    category: str
    snippet: str
    score: float
    match_type: str = "fts5"  # fts5 | vector | hybrid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "title": self.title,
            "category": self.category,
            "snippet": self.snippet,
            "score": round(self.score, 4),
            "match_type": self.match_type,
        }


class KnowledgeIndexStore(ABC):
    """Abstract storage interface for KnowledgeBase Tri-Graph indexing."""

    @abstractmethod
    def sync_directory(self, target_dir: Path | str, force_rebuild: bool = False) -> Dict[str, int]:
        """Index or update documents from a target directory."""
        pass

    @abstractmethod
    def search_fts(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Execute full-text lexical search."""
        pass

    @abstractmethod
    def search_hybrid(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Execute hybrid full-text and semantic vector search."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Retrieve index storage statistics and health."""
        pass


class SQLiteIndexStore(KnowledgeIndexStore):
    """High-speed local SQLite FTS5 and vector index store."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path is None:
            # Default location: .hath0r/cache/kb_index.sqlite
            from hath0r_cli.common import _discover_group_root

            root = _discover_group_root() or Path.cwd()
            cache_dir = root / ".hath0r" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = cache_dir / "kb_index.sqlite"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite tables and FTS5 virtual full-text index."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS kb_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    tags TEXT NOT NULL,
                    content TEXT NOT NULL,
                    indexed_at REAL NOT NULL
                )
                """
            )

            # Check if FTS5 table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='kb_fts'"
            )
            if not cursor.fetchone():
                try:
                    cursor.execute(
                        """
                        CREATE VIRTUAL TABLE kb_fts USING fts5(
                            title,
                            category,
                            tags,
                            content,
                            content='kb_documents',
                            content_rowid='id',
                            tokenize='porter'
                        )
                        """
                    )
                except sqlite3.OperationalError:
                    # Fallback if content option syntax varies
                    cursor.execute(
                        """
                        CREATE VIRTUAL TABLE kb_fts USING fts5(
                            title,
                            category,
                            tags,
                            content,
                            tokenize='porter'
                        )
                        """
                    )

            conn.commit()

    def _extract_doc_metadata(self, file_path: Path) -> Tuple[str, str, List[str], str]:
        """Extract title, category, tags, and content from a markdown file."""
        try:
            raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return file_path.name, "uncategorized", [], ""

        lines = raw_text.splitlines()
        title = file_path.stem
        category = "general"
        tags: List[str] = []

        # Parse simple markdown title
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break

        # Derive category from path
        parent_name = file_path.parent.name
        if parent_name in ("governance", "developers", "architecture", "catalogs", "lessons-learned"):
            category = parent_name

        # Extract simple tags if in frontmatter or headers
        if "strategy" in file_path.stem:
            tags.append("strategy")
        if "playbook" in file_path.stem:
            tags.append("playbook")
        if "schema" in file_path.stem:
            tags.append("schema")

        return title, category, tags, raw_text

    def sync_directory(self, target_dir: Path | str, force_rebuild: bool = False) -> Dict[str, int]:
        """Scan directory and incrementally update SQLite index."""
        dir_path = Path(target_dir)
        if not dir_path.is_dir():
            return {"indexed": 0, "updated": 0, "skipped": 0, "deleted": 0}

        counts = {"indexed": 0, "updated": 0, "skipped": 0, "deleted": 0}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            if force_rebuild:
                cursor.execute("DELETE FROM kb_fts")
                cursor.execute("DELETE FROM kb_documents")
                conn.commit()

            # Map existing documents
            cursor.execute("SELECT path, sha256, mtime FROM kb_documents")
            existing = {row["path"]: (row["sha256"], row["mtime"]) for row in cursor.fetchall()}

            current_paths = set()
            markdown_files = list(dir_path.rglob("*.md")) + list(dir_path.rglob("*.yaml"))

            for md_file in markdown_files:
                rel_path = str(md_file.resolve())
                current_paths.add(rel_path)

                stat = md_file.stat()
                mtime = stat.st_mtime
                content_bytes = md_file.read_bytes()
                sha256_hash = hashlib.sha256(content_bytes).hexdigest()

                if rel_path in existing and not force_rebuild:
                    cached_sha, cached_mtime = existing[rel_path]
                    if cached_sha == sha256_hash:
                        counts["skipped"] += 1
                        continue

                title, category, tags, text_content = self._extract_doc_metadata(md_file)
                tags_json = json.dumps(tags)
                now = time.time()

                if rel_path in existing:
                    cursor.execute(
                        """
                        UPDATE kb_documents
                        SET title = ?, category = ?, sha256 = ?, mtime = ?, tags = ?, content = ?, indexed_at = ?
                        WHERE path = ?
                        """,
                        (title, category, sha256_hash, mtime, tags_json, text_content, now, rel_path),
                    )
                    cursor.execute("SELECT id FROM kb_documents WHERE path = ?", (rel_path,))
                    row = cursor.fetchone()
                    if row:
                        doc_id = row["id"]
                        cursor.execute("DELETE FROM kb_fts WHERE rowid = ?", (doc_id,))
                        cursor.execute(
                            "INSERT INTO kb_fts(rowid, title, category, tags, content) VALUES (?, ?, ?, ?, ?)",
                            (doc_id, title, category, tags_json, text_content),
                        )
                    counts["updated"] += 1
                else:
                    cursor.execute(
                        """
                        INSERT INTO kb_documents (path, title, category, sha256, mtime, tags, content, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (rel_path, title, category, sha256_hash, mtime, tags_json, text_content, now),
                    )
                    doc_id = cursor.lastrowid
                    cursor.execute(
                        "INSERT INTO kb_fts(rowid, title, category, tags, content) VALUES (?, ?, ?, ?, ?)",
                        (doc_id, title, category, tags_json, text_content),
                    )
                    counts["indexed"] += 1

            conn.commit()

        return counts

    def search_fts(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Execute BM25 ranked full-text query."""
        clean_query = query.replace('"', "").replace("'", "").strip()
        if not clean_query:
            return []

        # Convert simple terms into prefix / match terms
        terms = [t for t in clean_query.split() if t]
        match_expr = " OR ".join(f"{t}*" for t in terms)

        results: List[SearchResult] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT d.path, d.title, d.category, d.content, bm25(kb_fts) as rank
                    FROM kb_fts f
                    JOIN kb_documents d ON d.id = f.rowid
                    WHERE kb_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT ?
                    """,
                    (match_expr, limit),
                )
                for row in cursor.fetchall():
                    content = row["content"]
                    snippet = self._generate_snippet(content, terms)
                    # Convert negative BM25 score to normalized [0, 1] relevance
                    raw_rank = abs(float(row["rank"]))
                    norm_score = round(1.0 / (1.0 + raw_rank), 4)
                    results.append(
                        SearchResult(
                            path=row["path"],
                            title=row["title"],
                            category=row["category"],
                            snippet=snippet,
                            score=norm_score,
                            match_type="fts5",
                        )
                    )
            except sqlite3.OperationalError:
                # Fallback to LIKE query if FTS expression fails
                cursor.execute(
                    """
                    SELECT path, title, category, content
                    FROM kb_documents
                    WHERE title LIKE ? OR content LIKE ?
                    LIMIT ?
                    """,
                    (f"%{clean_query}%", f"%{clean_query}%", limit),
                )
                for row in cursor.fetchall():
                    snippet = self._generate_snippet(row["content"], terms)
                    results.append(
                        SearchResult(
                            path=row["path"],
                            title=row["title"],
                            category=row["category"],
                            snippet=snippet,
                            score=0.75,
                            match_type="like_fallback",
                        )
                    )

        return results

    def search_hybrid(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Execute hybrid search combining FTS5 lexical ranking and PyTorch reranking."""
        fts_hits = self.search_fts(query, limit=max(limit * 2, 10))
        if not fts_hits:
            return []

        from hath0r_cli.bots.pytorch_runtime import PyTorchRuntime

        runtime = PyTorchRuntime()
        candidate_texts = [f"{h.title} {h.snippet}" for h in fts_hits]
        reranked = runtime.rerank_candidates(query=query, candidates=candidate_texts)

        hybrid_results: List[SearchResult] = []
        for r in reranked[:limit]:
            idx = r["index"]
            orig_hit = fts_hits[idx]
            hybrid_results.append(
                SearchResult(
                    path=orig_hit.path,
                    title=orig_hit.title,
                    category=orig_hit.category,
                    snippet=orig_hit.snippet,
                    score=r["score"],
                    match_type="hybrid",
                )
            )

        return hybrid_results

    def _generate_snippet(self, text: str, query_terms: List[str], max_chars: int = 200) -> str:
        """Create a representative snippet around matched terms."""
        lower_text = text.lower()
        earliest_pos = len(text)

        for term in query_terms:
            pos = lower_text.find(term.lower())
            if pos != -1 and pos < earliest_pos:
                earliest_pos = pos

        if earliest_pos == len(text):
            earliest_pos = 0

        start = max(0, earliest_pos - 40)
        end = min(len(text), start + max_chars)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = f"…{snippet}"
        if end < len(text):
            snippet = f"{snippet}…"
        return snippet

    def get_stats(self) -> Dict[str, Any]:
        """Collect index cache statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM kb_documents")
            total_docs = cursor.fetchone()["total"]

            cursor.execute(
                """
                SELECT category, COUNT(*) as count
                FROM kb_documents
                GROUP BY category
                """
            )
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}

        size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "database_path": str(self.db_path),
            "size_bytes": size_bytes,
            "total_documents": total_docs,
            "categories": by_category,
        }
