"""ContractsBot: Validate and synchronize JSON schema contracts across member repositories."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from hath0r_cli.common import _cli_repo_root, _discover_group_root


class ContractsBot:
    """Manages schema contract validation, parity checks, and synchronization."""

    def __init__(self, cwd: Optional[Path] = None, canonical_dir: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
        self.canonical_dir = canonical_dir or self._discover_canonical_schemas_dir()

    def _discover_canonical_schemas_dir(self) -> Path:
        """Locate canonical contracts/schemas directory in group or CLI repo."""
        group_root = _discover_group_root(self.cwd)
        if group_root:
            for cand_name in ("hath0r", "hath0r-framework", "HATH0R-Agentic-Framework"):
                cand_dir = group_root / cand_name / "contracts" / "schemas"
                if cand_dir.is_dir():
                    return cand_dir

        cli_root = _cli_repo_root()
        cli_schemas = cli_root / "contracts" / "schemas"
        if cli_schemas.is_dir():
            return cli_schemas

        # Fallback to local
        return self.cwd / "contracts" / "schemas"

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """Calculate SHA256 hex digest of file contents."""
        hasher = hashlib.sha256()
        hasher.update(path.read_bytes())
        return hasher.hexdigest()

    def validate_contracts(self, target_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Validate local schema contracts against canonical definitions and check JSON schema syntax."""
        local_schemas_dir = (target_dir or self.cwd) / "contracts" / "schemas"
        if not self.canonical_dir.is_dir():
            return {
                "success": False,
                "error": f"Canonical schemas directory not found: {self.canonical_dir}",
            }

        local_files: Dict[str, Path] = {}
        if local_schemas_dir.is_dir():
            local_files = {f.name: f for f in local_schemas_dir.glob("*.json")}

        canonical_files = {f.name: f for f in self.canonical_dir.glob("*.json")}
        all_names: Set[str] = set(local_files.keys()).union(set(canonical_files.keys()))

        items: List[Dict[str, Any]] = []
        in_sync_count = 0
        drifted_count = 0
        missing_local_count = 0
        untracked_count = 0

        for name in sorted(all_names):
            in_canonical = name in canonical_files
            in_local = name in local_files

            status = "unknown"
            diff = None
            syntax_valid = True

            if in_canonical and in_local:
                canon_path = canonical_files[name]
                loc_path = local_files[name]

                canon_hash = self._file_sha256(canon_path)
                loc_hash = self._file_sha256(loc_path)

                # Check JSON syntax
                try:
                    json.loads(loc_path.read_text(encoding="utf-8"))
                except Exception as e:
                    syntax_valid = False
                    diff = f"Invalid JSON syntax: {e}"

                if not syntax_valid:
                    status = "invalid"
                    drifted_count += 1
                elif canon_hash == loc_hash:
                    status = "in_sync"
                    in_sync_count += 1
                else:
                    status = "drifted"
                    diff = f"SHA mismatch: local={loc_hash[:8]} vs canonical={canon_hash[:8]}"
                    drifted_count += 1

            elif in_canonical and not in_local:
                status = "missing_local"
                missing_local_count += 1
            else:  # in_local and not in_canonical
                status = "untracked"
                untracked_count += 1

            items.append(
                {
                    "schema": name,
                    "status": status,
                    "in_canonical": in_canonical,
                    "in_local": in_local,
                    "diff": diff,
                }
            )

        overall_state = "ok" if (drifted_count == 0 and missing_local_count == 0) else "drift_detected"

        return {
            "success": True,
            "state": overall_state,
            "canonical_dir": str(self.canonical_dir),
            "local_dir": str(local_schemas_dir),
            "summary": {
                "total_schemas": len(items),
                "in_sync": in_sync_count,
                "drifted": drifted_count,
                "missing_local": missing_local_count,
                "untracked": untracked_count,
            },
            "schemas": items,
        }

    def sync_contracts(self, target_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Synchronize canonical schemas into target repository contracts/schemas."""
        target_schemas_dir = (target_dir or self.cwd) / "contracts" / "schemas"

        if not self.canonical_dir.is_dir():
            return {
                "success": False,
                "error": f"Canonical schemas directory not found: {self.canonical_dir}",
            }

        val = self.validate_contracts(target_dir=target_dir)
        if not val.get("success"):
            return val

        if not dry_run:
            target_schemas_dir.mkdir(parents=True, exist_ok=True)

        synced: List[str] = []
        canonical_files = {f.name: f for f in self.canonical_dir.glob("*.json")}

        for item in val.get("schemas", []):
            name = item.get("schema")
            status = item.get("status")

            if status in ("drifted", "missing_local") and name in canonical_files:
                src_file = canonical_files[name]
                dst_file = target_schemas_dir / name
                if not dry_run:
                    shutil.copy2(src_file, dst_file)
                synced.append(name)

        return {
            "success": True,
            "dry_run": dry_run,
            "canonical_dir": str(self.canonical_dir),
            "target_dir": str(target_schemas_dir),
            "synced_count": len(synced),
            "synced_schemas": synced,
            "message": f"{'[DRY RUN] Would sync' if dry_run else 'Synced'} {len(synced)} schema contract(s).",
        }
