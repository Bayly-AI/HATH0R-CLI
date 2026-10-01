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
        """Locate canonical contracts/schemas directory in group, framework, or CLI repo."""
        group_root = _discover_group_root(self.cwd)
        if group_root:
            for cand_name in ("hath0r", "hath0r-framework", "HATH0R-Agentic-Framework"):
                cand_root = group_root / cand_name
                for sub in ("contracts/schemas", "contracts"):
                    cand_dir = cand_root / sub
                    if cand_dir.is_dir() and any(cand_dir.glob("*.json")):
                        return cand_dir

        cli_root = _cli_repo_root()
        for sub in ("contracts/schemas", "contracts"):
            cli_schemas = cli_root / sub
            if cli_schemas.is_dir() and any(cli_schemas.glob("*.json")):
                return cli_schemas

        # Fallback to local contracts
        local_schemas = self.cwd / "contracts" / "schemas"
        if local_schemas.is_dir():
            return local_schemas
        return self.cwd / "contracts"

    @staticmethod
    def _file_sha256(path: Path) -> str:
        """Calculate SHA256 hex digest of file contents."""
        hasher = hashlib.sha256()
        hasher.update(path.read_bytes())
        return hasher.hexdigest()

    def _resolve_target_dir(self, target_dir: Optional[Path]) -> Path:
        base = target_dir or self.cwd
        if (base / "contracts" / "schemas").is_dir():
            return base / "contracts" / "schemas"
        if (base / "contracts").is_dir():
            return base / "contracts"
        return base / "contracts" / "schemas"

    def validate_contracts(self, target_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Validate local schema contracts against canonical definitions and check JSON schema syntax."""
        local_dir = self._resolve_target_dir(target_dir)

        canonical_files: Dict[str, Path] = {}
        if self.canonical_dir.is_dir():
            canonical_files = {f.name: f for f in self.canonical_dir.glob("*.json")}

        if not canonical_files:
            return {
                "success": False,
                "error": f"No canonical schema contracts found in: {self.canonical_dir}",
            }

        local_files: Dict[str, Path] = {}
        if local_dir.is_dir():
            local_files = {f.name: f for f in local_dir.glob("*.json")}

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
            "local_dir": str(local_dir),
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
        """Synchronize canonical schemas into target repository contracts directory."""
        target_dir_path = self._resolve_target_dir(target_dir)

        canonical_files: Dict[str, Path] = {}
        if self.canonical_dir.is_dir():
            canonical_files = {f.name: f for f in self.canonical_dir.glob("*.json")}

        if not canonical_files:
            return {
                "success": False,
                "error": f"No canonical schema contracts found in: {self.canonical_dir}",
            }

        val = self.validate_contracts(target_dir=target_dir)
        if not val.get("success"):
            return val

        if not dry_run:
            target_dir_path.mkdir(parents=True, exist_ok=True)

        synced: List[str] = []

        for item in val.get("schemas", []):
            name = item.get("schema")
            status = item.get("status")

            if status in ("drifted", "missing_local") and name in canonical_files:
                src_file = canonical_files[name]
                dst_file = target_dir_path / name
                if not dry_run:
                    shutil.copy2(src_file, dst_file)
                synced.append(name)

        return {
            "success": True,
            "dry_run": dry_run,
            "canonical_dir": str(self.canonical_dir),
            "target_dir": str(target_dir_path),
            "synced_count": len(synced),
            "synced_schemas": synced,
            "message": f"{'[DRY RUN] Would sync' if dry_run else 'Synced'} {len(synced)} schema contract(s).",
        }
