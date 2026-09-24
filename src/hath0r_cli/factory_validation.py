"""Factory specification schema validation and discovery engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml


@dataclass
class FactoryValidationResult:
    """Result of validating a single factory specification file."""

    factory_id: str
    name: str
    file_path: Path
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bots_count: int = 0
    workflows_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "factory_id": self.factory_id,
            "name": self.name,
            "file": str(self.file_path),
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "bots_count": self.bots_count,
            "workflows_count": self.workflows_count,
        }


def get_factory_schema() -> dict[str, Any]:
    """Load the canonical hath0r-factory-v1 schema from contracts."""
    schema_path = Path(__file__).resolve().parents[2] / "contracts" / "hath0r-factory-v1.schema.json"
    if not schema_path.is_file():
        raise FileNotFoundError(f"Canonical factory schema not found at {schema_path}")
    loaded: Any = json.loads(schema_path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def validate_factory_file(file_path: Path, schema: dict[str, Any] | None = None) -> FactoryValidationResult:
    """Validate a single factory YAML manifest against the factory schema and bot reference integrity."""
    if not schema:
        schema = get_factory_schema()

    if not file_path.is_file():
        return FactoryValidationResult(
            factory_id=file_path.stem,
            name=file_path.name,
            file_path=file_path,
            valid=False,
            errors=[f"File not found: {file_path}"],
        )

    try:
        content = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return FactoryValidationResult(
            factory_id=file_path.stem,
            name=file_path.name,
            file_path=file_path,
            valid=False,
            errors=[f"YAML parsing error: {exc}"],
        )

    if not isinstance(content, dict):
        return FactoryValidationResult(
            factory_id=file_path.stem,
            name=file_path.name,
            file_path=file_path,
            valid=False,
            errors=["Factory manifest must be a YAML object/dictionary."],
        )

    factory_id = str(content.get("factory_id", file_path.stem))
    name = str(content.get("name", file_path.stem))

    validator = jsonschema.Draft202012Validator(schema)
    validation_errors = list(validator.iter_errors(content))

    errors = []
    for err in validation_errors:
        path_str = ".".join(str(p) for p in err.absolute_path) or "root"
        errors.append(f"Schema violation at '{path_str}': {err.message}")

    warnings: list[str] = []
    bots = content.get("bots", [])
    workflows = content.get("workflows", [])

    bots_count = len(bots) if isinstance(bots, list) else 0
    workflows_count = len(workflows) if isinstance(workflows, list) else 0

    # Cross-reference bot IDs in workflow steps
    if isinstance(bots, list) and isinstance(workflows, list):
        declared_bots: dict[str, set[str]] = {}
        for b in bots:
            if isinstance(b, dict) and "id" in b:
                caps = set(b.get("capabilities", [])) if isinstance(b.get("capabilities"), list) else set()
                declared_bots[b["id"]] = caps

        for wf in workflows:
            if not isinstance(wf, dict):
                continue
            wf_id = wf.get("id", "unknown")
            steps = wf.get("steps", [])
            if isinstance(steps, list):
                for idx, st in enumerate(steps):
                    if not isinstance(st, dict):
                        continue
                    bot_ref = st.get("bot")
                    action_ref = st.get("action")
                    if bot_ref and bot_ref not in declared_bots:
                        errors.append(
                            f"Workflow '{wf_id}' step {idx + 1} references undeclared bot '{bot_ref}'."
                        )
                    elif bot_ref in declared_bots and action_ref:
                        caps = declared_bots[bot_ref]
                        if caps and action_ref not in caps:
                            warnings.append(
                                f"Workflow '{wf_id}' step {idx + 1} action '{action_ref}' "
                                f"not listed in bot '{bot_ref}' declared capabilities."
                            )

    is_valid = len(errors) == 0
    return FactoryValidationResult(
        factory_id=factory_id,
        name=name,
        file_path=file_path,
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        bots_count=bots_count,
        workflows_count=workflows_count,
    )


def validate_all_factories(group_root: Path | None = None) -> list[FactoryValidationResult]:
    """Find and validate all factory manifests across group and CLI configurations."""
    cli_repo_root = Path(__file__).resolve().parents[2]
    candidate_dirs: list[Path] = [cli_repo_root / "cfg" / "factories"]
    if group_root:
        candidate_dirs.insert(0, group_root / "cfg" / "factories")

    schema = get_factory_schema()
    seen_files: set[str] = set()
    results: list[FactoryValidationResult] = []

    for d in candidate_dirs:
        if d.is_dir():
            for f in sorted(d.glob("*.yaml")):
                real = str(f.resolve())
                if real not in seen_files:
                    seen_files.add(real)
                    results.append(validate_factory_file(f, schema=schema))

    return results
