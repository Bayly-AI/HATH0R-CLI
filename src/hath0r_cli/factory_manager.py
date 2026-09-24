"""Factory Manager — CRUD + path resolution for declarative factory manifests.

Factories live under ``cfg/factories/`` (preferred) or ``.hath0r/factories/``.
Never under ``.ai/`` / ``.aegis/`` / ``.infraOS/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from hath0r_cli.factory_validation import validate_factory_file

_FACTORY_ID_RE = re.compile(r"^[a-z0-9-]+$")
_FORBIDDEN_ROOTS = (".ai", ".aegis", ".infraOS")


def _safe_load(path: Path) -> dict[str, Any] | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict) and data.get("factory_id"):
        return data
    return None


def resolve_factories_dir(cwd: Path | None = None, group_root: Path | None = None) -> Path:
    """Pick the writable factories directory for this checkout / group."""
    roots: list[Path] = []
    if cwd is not None:
        roots.append(cwd.resolve())
    if group_root is not None:
        roots.append(group_root.resolve())
    # CLI package repo root (src/hath0r_cli → parents[2])
    roots.append(Path(__file__).resolve().parents[2])

    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        for rel in (Path("cfg") / "factories", Path(".hath0r") / "factories"):
            candidate = root / rel
            # Reject forbidden hidden roots
            if any(part in _FORBIDDEN_ROOTS for part in candidate.parts):
                continue
            if candidate.is_dir():
                return candidate

    # Default: create under cwd cfg/factories when possible
    base = (cwd or Path.cwd()).resolve()
    target = base / "cfg" / "factories"
    target.mkdir(parents=True, exist_ok=True)
    return target


@dataclass
class FactoryManagerBot:
    """CRUD + validate lifecycle for factory YAML manifests."""

    cwd: Path = field(default_factory=Path.cwd)
    group_root: Path | None = None

    def factories_dir(self) -> Path:
        return resolve_factories_dir(cwd=self.cwd, group_root=self.group_root)

    def list_factories(self) -> list[dict[str, Any]]:
        directory = self.factories_dir()
        items: list[dict[str, Any]] = []
        if not directory.is_dir():
            return items
        for path in sorted(directory.glob("*.yaml")):
            data = _safe_load(path)
            if not data:
                continue
            items.append(
                {
                    "id": data.get("factory_id"),
                    "name": data.get("name"),
                    "version": data.get("version"),
                    "description": (data.get("description") or "").strip(),
                    "bots_count": len(data.get("bots") or []),
                    "workflows_count": len(data.get("workflows") or []),
                    "file": str(path),
                }
            )
        return items

    def get_factory(self, factory_id: str) -> dict[str, Any] | None:
        directory = self.factories_dir()
        for path in directory.glob("*.yaml"):
            data = _safe_load(path)
            if data and data.get("factory_id") == factory_id:
                return {**data, "_file": str(path)}
        return None

    def path_for(self, factory_id: str) -> Path | None:
        data = self.get_factory(factory_id)
        if not data:
            return None
        return Path(str(data["_file"]))

    def create(
        self,
        factory_id: str,
        *,
        name: str | None = None,
        description: str = "",
        category: str = "automation",
        dry_run: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        if not _FACTORY_ID_RE.match(factory_id):
            return {
                "success": False,
                "error": f"Invalid factory_id '{factory_id}'. Must match ^[a-z0-9-]+$.",
            }
        if self.get_factory(factory_id) and not force:
            return {
                "success": False,
                "error": f"Factory '{factory_id}' already exists. Use update/edit or --force.",
            }

        directory = self.factories_dir()
        path = directory / f"{factory_id}.yaml"
        payload: dict[str, Any] = {
            "factory_id": factory_id,
            "name": name or factory_id.replace("-", " ").title(),
            "version": "1.0.0",
            "description": description
            or f"Automation factory '{factory_id}' managed by Factory Manager bot.",
            "author": "Bayly-AI",
            "category": category,
            "bots": [
                {
                    "id": "factory-manager-bot",
                    "name": "Factory Manager Bot",
                    "role": "factory-lifecycle",
                    "capabilities": ["list", "create", "update", "delete", "validate", "execute"],
                }
            ],
            "workflows": [
                {
                    "id": "noop",
                    "name": "Placeholder workflow",
                    "description": "Replace with real steps. Validates factory structure only.",
                    "steps": [
                        {
                            "bot": "factory-manager-bot",
                            "action": "validate",
                            "on_failure": "abort",
                        }
                    ],
                }
            ],
        }

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "factory_id": factory_id,
                "path": str(path),
                "action": f"[DRY-RUN] Would write factory manifest to {path}",
                "manifest": payload,
            }

        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Hath0r Factory Specification v1\n"
            "# Generated by Factory Manager bot\n\n"
            + yaml.safe_dump(payload, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        validation = validate_factory_file(path)
        return {
            "success": validation.valid,
            "factory_id": factory_id,
            "path": str(path),
            "created": True,
            "valid": validation.valid,
            "errors": list(validation.errors),
        }

    def update(
        self,
        factory_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        patch: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        existing = self.get_factory(factory_id)
        if not existing:
            return {"success": False, "error": f"Factory '{factory_id}' not found."}

        path = Path(str(existing.pop("_file")))
        data = dict(existing)
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if version is not None:
            data["version"] = version
        if patch:
            # Shallow merge only for top-level keys (bots/workflows replaced if provided)
            for key, value in patch.items():
                if key == "factory_id":
                    continue
                data[key] = value

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "factory_id": factory_id,
                "path": str(path),
                "action": f"[DRY-RUN] Would update {path}",
                "manifest": data,
            }

        path.write_text(
            "# Hath0r Factory Specification v1\n"
            "# Updated by Factory Manager bot\n\n"
            + yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
        validation = validate_factory_file(path)
        return {
            "success": validation.valid,
            "factory_id": factory_id,
            "path": str(path),
            "updated": True,
            "valid": validation.valid,
            "errors": list(validation.errors),
        }

    def delete(self, factory_id: str, *, dry_run: bool = False) -> dict[str, Any]:
        path = self.path_for(factory_id)
        if path is None:
            return {"success": False, "error": f"Factory '{factory_id}' not found."}
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "factory_id": factory_id,
                "path": str(path),
                "action": f"[DRY-RUN] Would delete {path}",
            }
        path.unlink(missing_ok=True)
        return {"success": True, "factory_id": factory_id, "path": str(path), "deleted": True}

    def validate(self, factory_id: str | None = None) -> dict[str, Any]:
        if factory_id:
            path = self.path_for(factory_id)
            if path is None:
                return {"success": False, "error": f"Factory '{factory_id}' not found."}
            result = validate_factory_file(path)
            return {
                "success": result.valid,
                "factory_id": factory_id,
                "valid": result.valid,
                "errors": list(result.errors),
                "warnings": list(result.warnings),
            }
        items = []
        ok = True
        for entry in self.list_factories():
            path = Path(entry["file"])
            result = validate_factory_file(path)
            items.append(result.to_dict())
            ok = ok and result.valid
        return {"success": ok, "factories": items, "valid": ok}
