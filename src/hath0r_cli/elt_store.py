"""Persistent SQLite Raw Staging Store for Hath0r Embedded ELT Subsystem."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RawRecord:
    """Raw staged record with cryptographic hash and provenance."""

    id: int
    source_uri: str
    source_type: str
    content_sha256: str
    raw_payload: str
    content_length: int
    metadata: Dict[str, Any]
    ingested_at: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_uri": self.source_uri,
            "source_type": self.source_type,
            "content_sha256": self.content_sha256,
            "raw_payload": self.raw_payload,
            "content_length": self.content_length,
            "metadata": self.metadata,
            "ingested_at": self.ingested_at,
            "status": self.status,
        }


class RawStagingStore:
    """High-speed local SQLite raw staging store for Embedded ELT."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        if db_path is None:
            from hath0r_cli.common import _discover_group_root

            root = _discover_group_root()
            self.db_path = root / ".hath0r" / "cache" / "ingest" / "raw_staging.sqlite"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema for raw records and projection tracking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS raw_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_uri TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL UNIQUE,
                    raw_payload TEXT NOT NULL,
                    content_length INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    ingested_at REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'staged'
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_source_type ON raw_records(source_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_source_uri ON raw_records(source_uri)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_status ON raw_records(status)")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projection_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER NOT NULL REFERENCES raw_records(id) ON DELETE CASCADE,
                    projection_name TEXT NOT NULL,
                    projected_at REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'synced',
                    error_message TEXT,
                    UNIQUE(record_id, projection_name)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_proj_status ON projection_states(projection_name, status)")
            conn.commit()

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Calculate SHA-256 hash of raw content string."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def stage_record(
        self,
        source_uri: str,
        source_type: str,
        raw_payload: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Stage a raw record into the store with deduplication check."""
        meta = metadata or {}
        sha256 = self.compute_sha256(raw_payload)
        now = time.time()
        content_len = len(raw_payload)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, source_uri, ingested_at FROM raw_records WHERE content_sha256 = ?", (sha256,))
            row = cursor.fetchone()

            if row:
                return {
                    "record_id": row["id"],
                    "source_uri": source_uri,
                    "content_sha256": sha256,
                    "is_duplicate": True,
                    "status": "existing",
                    "ingested_at": row["ingested_at"],
                }

            cursor.execute(
                """
                INSERT INTO raw_records (
                    source_uri, source_type, content_sha256, raw_payload,
                    content_length, metadata_json, ingested_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'staged')
                """,
                (
                    source_uri,
                    source_type,
                    sha256,
                    raw_payload,
                    content_len,
                    json.dumps(meta),
                    now,
                ),
            )
            rec_id = cursor.lastrowid
            conn.commit()

            return {
                "record_id": rec_id,
                "source_uri": source_uri,
                "content_sha256": sha256,
                "is_duplicate": False,
                "status": "staged",
                "ingested_at": now,
            }

    def get_record(self, record_id: int) -> Optional[RawRecord]:
        """Fetch raw record by primary ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source_uri, source_type, content_sha256, raw_payload,
                       content_length, metadata_json, ingested_at, status
                FROM raw_records WHERE id = ?
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            try:
                meta = json.loads(row["metadata_json"])
            except Exception:
                meta = {}

            return RawRecord(
                id=row["id"],
                source_uri=row["source_uri"],
                source_type=row["source_type"],
                content_sha256=row["content_sha256"],
                raw_payload=row["raw_payload"],
                content_length=row["content_length"],
                metadata=meta,
                ingested_at=row["ingested_at"],
                status=row["status"],
            )

    def get_record_by_hash(self, sha256: str) -> Optional[RawRecord]:
        """Fetch raw record by SHA-256 hash."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, source_uri, source_type, content_sha256, raw_payload,
                       content_length, metadata_json, ingested_at, status
                FROM raw_records WHERE content_sha256 = ?
                """,
                (sha256,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            try:
                meta = json.loads(row["metadata_json"])
            except Exception:
                meta = {}

            return RawRecord(
                id=row["id"],
                source_uri=row["source_uri"],
                source_type=row["source_type"],
                content_sha256=row["content_sha256"],
                raw_payload=row["raw_payload"],
                content_length=row["content_length"],
                metadata=meta,
                ingested_at=row["ingested_at"],
                status=row["status"],
            )

    def list_records(
        self,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[RawRecord]:
        """List raw staged records with optional filters."""
        query = "SELECT id, source_uri, source_type, content_sha256, raw_payload, content_length, metadata_json, ingested_at, status FROM raw_records"
        params: List[Any] = []
        conditions: List[str] = []

        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        records: List[RawRecord] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            for row in cursor.fetchall():
                try:
                    meta = json.loads(row["metadata_json"])
                except Exception:
                    meta = {}
                records.append(
                    RawRecord(
                        id=row["id"],
                        source_uri=row["source_uri"],
                        source_type=row["source_type"],
                        content_sha256=row["content_sha256"],
                        raw_payload=row["raw_payload"],
                        content_length=row["content_length"],
                        metadata=meta,
                        ingested_at=row["ingested_at"],
                        status=row["status"],
                    )
                )
        return records

    def mark_projected(
        self,
        record_id: int,
        projection_name: str,
        status: str = "synced",
        error_message: Optional[str] = None,
    ) -> None:
        """Record or update projection status for a staged record."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO projection_states (record_id, projection_name, projected_at, status, error_message)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(record_id, projection_name) DO UPDATE SET
                    projected_at = excluded.projected_at,
                    status = excluded.status,
                    error_message = excluded.error_message
                """,
                (record_id, projection_name, now, status, error_message),
            )
            conn.commit()

    def get_unprojected_records(self, projection_name: str, limit: int = 100) -> List[RawRecord]:
        """Fetch records that have never been projected or are marked dirty."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.id, r.source_uri, r.source_type, r.content_sha256, r.raw_payload,
                       r.content_length, r.metadata_json, r.ingested_at, r.status
                FROM raw_records r
                LEFT JOIN projection_states p ON r.id = p.record_id AND p.projection_name = ?
                WHERE p.id IS NULL OR p.status = 'dirty'
                ORDER BY r.id ASC
                LIMIT ?
                """,
                (projection_name, limit),
            )
            records: List[RawRecord] = []
            for row in cursor.fetchall():
                try:
                    meta = json.loads(row["metadata_json"])
                except Exception:
                    meta = {}
                records.append(
                    RawRecord(
                        id=row["id"],
                        source_uri=row["source_uri"],
                        source_type=row["source_type"],
                        content_sha256=row["content_sha256"],
                        raw_payload=row["raw_payload"],
                        content_length=row["content_length"],
                        metadata=meta,
                        ingested_at=row["ingested_at"],
                        status=row["status"],
                    )
                )
            return records

    def mark_all_dirty(self, projection_name: Optional[str] = None) -> int:
        """Mark projection states as dirty to force rebuilding."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if projection_name:
                cursor.execute(
                    "UPDATE projection_states SET status = 'dirty' WHERE projection_name = ?",
                    (projection_name,),
                )
            else:
                cursor.execute("UPDATE projection_states SET status = 'dirty'")
            count = cursor.rowcount
            conn.commit()
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Retrieve storage health, counts, and projection statuses."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(content_length), 0) FROM raw_records")
            row = cursor.fetchone()
            total_records = row[0] if row else 0
            total_content_bytes = row[1] if row else 0

            cursor.execute("SELECT source_type, COUNT(*) FROM raw_records GROUP BY source_type")
            source_breakdown = {r[0]: r[1] for r in cursor.fetchall()}

            cursor.execute(
                """
                SELECT projection_name, status, COUNT(*)
                FROM projection_states
                GROUP BY projection_name, status
                """
            )
            projections: Dict[str, Dict[str, int]] = {}
            for proj, stat, cnt in cursor.fetchall():
                if proj not in projections:
                    projections[proj] = {}
                projections[proj][stat] = cnt

            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

            return {
                "database_path": str(self.db_path),
                "database_size_bytes": db_size,
                "total_records": total_records,
                "total_content_bytes": total_content_bytes,
                "source_types": source_breakdown,
                "projections": projections,
            }

    def prune_records(self, retention_days: int) -> int:
        """Delete raw records older than retention period."""
        cutoff = time.time() - (retention_days * 86400)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM raw_records WHERE ingested_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def vacuum(self) -> None:
        """Run VACUUM to reclaim free space."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
