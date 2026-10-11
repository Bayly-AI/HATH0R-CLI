"""Embedded ELT Bot for Hath0r CLI — Non-Destructive Raw Data Ingestion."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.elt_store import RawRecord, RawStagingStore


@dataclass
class IngestionBatchResult:
    """Summary of batch ingestion execution."""

    source_type: str
    total_scanned: int
    staged_new: int
    duplicates_skipped: int
    errors: List[str] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "total_scanned": self.total_scanned,
            "staged_new": self.staged_new,
            "duplicates_skipped": self.duplicates_skipped,
            "errors": self.errors,
            "records": self.records,
        }


class EmbeddedELTBot:
    """Managing bot for Embedded ELT extraction and raw staging."""

    def __init__(
        self,
        cwd: Optional[Path | str] = None,
        store: Optional[RawStagingStore] = None,
    ) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.store = store or RawStagingStore()

    def extract_and_stage_docs(
        self,
        target_dir: Path | str,
        glob_pattern: str = "**/*.md",
    ) -> IngestionBatchResult:
        """Extract documentation files and stage raw markdown content without destructive parsing."""
        path = Path(target_dir)
        if not path.is_absolute():
            path = self.cwd / path

        result = IngestionBatchResult(
            source_type="docs",
            total_scanned=0,
            staged_new=0,
            duplicates_skipped=0,
        )

        if not path.exists():
            result.errors.append(f"Target directory does not exist: {path}")
            return result

        for file_path in path.glob(glob_pattern):
            if not file_path.is_file():
                continue

            result.total_scanned += 1
            try:
                raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
                try:
                    rel_uri = str(file_path.relative_to(self.cwd))
                except ValueError:
                    rel_uri = str(file_path)

                stat = file_path.stat()
                metadata = {
                    "filename": file_path.name,
                    "mtime": stat.st_mtime,
                    "size_bytes": stat.st_size,
                    "extension": file_path.suffix,
                    "target_dir": str(path),
                }

                stage_res = self.store.stage_record(
                    source_uri=rel_uri,
                    source_type="docs",
                    raw_payload=raw_text,
                    metadata=metadata,
                )

                if stage_res["is_duplicate"]:
                    result.duplicates_skipped += 1
                else:
                    result.staged_new += 1

                result.records.append(stage_res)
            except Exception as err:
                result.errors.append(f"Failed to read {file_path}: {err}")

        return result

    def extract_and_stage_mcp(
        self,
        server_id: str,
        source_id: Optional[str] = None,
        sample_payload: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract data from Model Context Protocol (MCP) data sources into raw staging."""
        uri = f"mcp://{server_id}" + (f"/{source_id}" if source_id else "")

        if sample_payload is not None:
            raw_payload = sample_payload
        else:
            # Synthetic / fallback sample representation for MCP probe
            raw_payload = json.dumps(
                {
                    "server_id": server_id,
                    "source_id": source_id,
                    "sampled_at": time.time(),
                    "type": "mcp_resource_snapshot",
                }
            )

        metadata = {
            "server_id": server_id,
            "source_id": source_id,
            "extracted_via": "EmbeddedELTBot.extract_and_stage_mcp",
        }

        stage_res = self.store.stage_record(
            source_uri=uri,
            source_type="mcp",
            raw_payload=raw_payload,
            metadata=metadata,
        )

        return stage_res

    def extract_and_stage_git(
        self,
        repo_dir: Optional[Path | str] = None,
        max_commits: int = 25,
    ) -> IngestionBatchResult:
        """Extract git history log records into raw staging."""
        target_repo = Path(repo_dir) if repo_dir else self.cwd
        result = IngestionBatchResult(
            source_type="git",
            total_scanned=0,
            staged_new=0,
            duplicates_skipped=0,
        )

        try:
            cmd = [
                "git",
                "log",
                f"-n{max_commits}",
                "--pretty=format:%H%x00%an%x00%ae%x00%at%x00%s",
            ]
            proc = subprocess.run(cmd, cwd=str(target_repo), capture_output=True, text=True, check=True)
            lines = proc.stdout.strip().split("\n") if proc.stdout.strip() else []

            for line in lines:
                parts = line.split("\x00")
                if len(parts) < 5:
                    continue
                commit_hash, author_name, author_email, timestamp, subject = parts[:5]
                result.total_scanned += 1

                uri = f"git://commit/{commit_hash}"
                raw_payload = json.dumps(
                    {
                        "commit_hash": commit_hash,
                        "author": author_name,
                        "email": author_email,
                        "timestamp": float(timestamp),
                        "subject": subject,
                    }
                )
                metadata = {
                    "commit_hash": commit_hash,
                    "author": author_name,
                    "subject": subject,
                }

                stage_res = self.store.stage_record(
                    source_uri=uri,
                    source_type="git",
                    raw_payload=raw_payload,
                    metadata=metadata,
                )
                if stage_res["is_duplicate"]:
                    result.duplicates_skipped += 1
                else:
                    result.staged_new += 1
                result.records.append(stage_res)

        except Exception as err:
            result.errors.append(f"Git log extraction error: {err}")

        return result

    def extract_and_stage_telemetry(
        self,
        payload: Dict[str, Any] | str,
        source_uri: str = "otel/span",
    ) -> Dict[str, Any]:
        """Stage raw telemetry trace / span payload."""
        raw_str = payload if isinstance(payload, str) else json.dumps(payload)
        metadata = {
            "ingested_via": "EmbeddedELTBot.extract_and_stage_telemetry",
            "format": "json" if isinstance(payload, (dict, list)) else "raw",
        }
        return self.store.stage_record(
            source_uri=source_uri,
            source_type="telemetry",
            raw_payload=raw_str,
            metadata=metadata,
        )

    def stage_raw(
        self,
        source_uri: str,
        source_type: str,
        raw_payload: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Direct raw staging API."""
        return self.store.stage_record(
            source_uri=source_uri,
            source_type=source_type,
            raw_payload=raw_payload,
            metadata=metadata,
        )

    def get_status(self) -> Dict[str, Any]:
        """Retrieve raw staging storage statistics and health."""
        return self.store.get_stats()

    def prune(self, retention_days: int) -> Dict[str, Any]:
        """Prune stale records older than retention period."""
        deleted = self.store.prune_records(retention_days=retention_days)
        self.store.vacuum()
        return {
            "retention_days": retention_days,
            "records_deleted": deleted,
            "status": "pruned",
        }
