"""Doctor check engine — pure evaluation separated from rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional until C6
    yaml = None  # type: ignore[assignment]


@dataclass
class DoctorCheck:
    """One doctor check result."""

    id: str
    label: str
    state: str  # ok | unavailable | error (schema allows degraded too)
    message: str
    detail: str = ""
    path: str | None = None  # absolute path for --verbose only


@dataclass
class DoctorResult:
    """Aggregated doctor evaluation."""

    group_id: str
    control_tower_product_id: str
    control_tower_configured: bool
    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for c in self.checks if c.state == "ok")

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if c.state != "ok")

    @property
    def overall_state(self) -> str:
        if self.failed_count == 0:
            return "ok"
        return "degraded"

    def to_data(self, *, verbose: bool = False) -> dict[str, Any]:
        """Build HATHOR-TS-005 §10 data payload (no absolute paths unless verbose)."""
        checks_out: list[dict[str, Any]] = []
        for c in self.checks:
            item: dict[str, Any] = {
                "id": c.id,
                "state": c.state if c.state in {"ok", "degraded", "unavailable", "error"} else "error",
                "message": c.message,
            }
            if verbose and c.path:
                item["path"] = c.path
            checks_out.append(item)
        return {
            "group_id": self.group_id,
            "control_tower": {
                "product_id": self.control_tower_product_id,
                "configured": self.control_tower_configured,
            },
            "checks": checks_out,
            "counts": {"ok": self.ok_count, "failed": self.failed_count},
        }


def _file_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    try:
        return needle in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _path_ok(path: Path, want_dir: bool = True) -> bool:
    return path.is_dir() if want_dir else path.is_file()


def _add(
    checks: list[DoctorCheck],
    *,
    check_id: str,
    label: str,
    ok: bool,
    ok_message: str,
    fail_message: str,
    detail: str = "",
    path: Path | str | None = None,
    fail_state: str = "unavailable",
) -> None:
    p = str(path) if path is not None else None
    checks.append(
        DoctorCheck(
            id=check_id,
            label=label,
            state="ok" if ok else fail_state,
            message=ok_message if ok else fail_message,
            detail=detail or (p or ""),
            path=p,
        )
    )


def _load_yaml(path: Path) -> Any | None:
    if yaml is None or not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _catalog_product_map(data: Any) -> dict[str, bool] | None:
    """Return product_id -> is_control_tower map, or None if unusable."""
    if not isinstance(data, dict):
        return None
    products = data.get("products")
    if not isinstance(products, list):
        return None
    out: dict[str, bool] = {}
    for item in products:
        if not isinstance(item, dict):
            continue
        pid = item.get("product_id")
        if not isinstance(pid, str) or not pid:
            continue
        out[pid] = bool(item.get("is_control_tower", False))
    return out if out else None


def _product_canonical_flags(data: Any) -> dict[str, bool]:
    """Return product_id -> canonical flag (default True if omitted)."""
    out: dict[str, bool] = {}
    if not isinstance(data, dict):
        return out
    products = data.get("products")
    if not isinstance(products, list):
        return out
    for item in products:
        if not isinstance(item, dict):
            continue
        pid = item.get("product_id")
        if not isinstance(pid, str) or not pid:
            continue
        out[pid] = bool(item.get("canonical", True))
    return out


def run_checks(root: Path, kb: Path) -> DoctorResult:
    """Evaluate all doctor checks against root and kb paths."""
    tower = root / "HATH0R-CLI"
    tower_cfg = tower / "cfg"
    expected_tower = str(tower)
    members = {
        "framework": root / "hath0r",
        "cli": tower,
        "poc": root / "hath0r-poc",
    }
    # Map short member names → catalog product_id for optional/required policy.
    member_product_ids = {
        "framework": "hath0r-framework",
        "cli": "hath0r-cli",
        "poc": "hath0r-poc",
    }
    tower_products_data = _load_yaml(tower_cfg / "products.yaml")
    canonical_flags = _product_canonical_flags(tower_products_data)
    checks: list[DoctorCheck] = []

    _add(
        checks,
        check_id="group-root",
        label="group root",
        ok=_path_ok(root),
        ok_message="Group root is present.",
        fail_message="Group root directory is missing.",
        path=root,
    )
    _add(
        checks,
        check_id="group-agents",
        label="group AGENTS.md",
        ok=_path_ok(root / "AGENTS.md", want_dir=False),
        ok_message="Group AGENTS.md is present.",
        fail_message="Group AGENTS.md is missing.",
        path=root / "AGENTS.md",
    )
    _add(
        checks,
        check_id="group-warp",
        label="group WARP.md",
        ok=_path_ok(root / "WARP.md", want_dir=False),
        ok_message="Group WARP.md is present.",
        fail_message="Group WARP.md is missing.",
        path=root / "WARP.md",
    )
    _add(
        checks,
        check_id="canonical-kb",
        label="canonical KB",
        ok=_path_ok(kb),
        ok_message="Canonical knowledgebase directory is present.",
        fail_message="Canonical knowledgebase directory is missing.",
        path=kb,
    )
    catalog = kb / "catalogs" / "suite-products.yaml"
    _add(
        checks,
        check_id="suite-catalog",
        label="suite catalog",
        ok=_path_ok(catalog, want_dir=False),
        ok_message="Suite product catalog file is present.",
        fail_message="Suite product catalog file is missing.",
        path=catalog,
    )
    _add(
        checks,
        check_id="catalog-tower-path",
        label="catalog tower path",
        ok=_file_contains(catalog, expected_tower),
        ok_message="Catalog references the control tower path.",
        fail_message="Catalog control tower path is missing or mismatched.",
        path=catalog,
        fail_state="error",
    )

    _add(
        checks,
        check_id="control-tower-root",
        label="control tower root",
        ok=_path_ok(tower),
        ok_message="Control tower repository root is present.",
        fail_message="Control tower repository root is missing.",
        path=tower,
    )
    for name in ("control-tower.yaml", "suite.yaml", "knowledge-tower.yaml", "products.yaml"):
        path = tower_cfg / name
        _add(
            checks,
            check_id=f"tower-cfg-{name.removesuffix('.yaml')}",
            label=f"tower cfg:{name}",
            ok=_path_ok(path, want_dir=False),
            ok_message=f"Tower config {name} is present.",
            fail_message=f"Tower config {name} is missing.",
            path=path,
        )

    kt = tower_cfg / "knowledge-tower.yaml"
    _add(
        checks,
        check_id="tower-is-control-tower",
        label="tower is_control_tower",
        ok=_file_contains(kt, "is_control_tower: true"),
        ok_message="Tower knowledge-tower.yaml declares is_control_tower: true.",
        fail_message="Tower is_control_tower flag is false or missing.",
        path=kt,
        fail_state="error",
    )
    _add(
        checks,
        check_id="tower-control-tower-path",
        label="tower control_tower_path",
        ok=_file_contains(kt, expected_tower)
        and _file_contains(tower_cfg / "suite.yaml", expected_tower),
        ok_message="Tower configs reference the control tower path.",
        fail_message="Tower control_tower_path is mismatched.",
        path=kt,
        fail_state="error",
    )
    _add(
        checks,
        check_id="tower-remote",
        label="tower remote",
        ok=_file_contains(tower_cfg / "control-tower.yaml", "Bayly-AI/HATH0R-CLI"),
        ok_message="Tower remote is Bayly-AI/HATH0R-CLI.",
        fail_message="Tower remote is missing or mismatched.",
        path=tower_cfg / "control-tower.yaml",
        fail_state="error",
    )

    for name, path in members.items():
        product_id = member_product_ids[name]
        # Control tower + framework stay required. Non-canonical catalog rows
        # (e.g. archived POC) are optional local fixtures — missing is ok.
        required = True if name in {"cli", "framework"} else canonical_flags.get(
            product_id, True
        )
        present = _path_ok(path)

        if not required and not present:
            _add(
                checks,
                check_id=f"member-{name}",
                label=f"member:{name}",
                ok=True,
                ok_message=(
                    f"Optional member {name} is not checked out "
                    f"(archived/non-canonical fixture; ok)."
                ),
                fail_message=f"Member repository {name} is missing.",
                path=path,
            )
            _add(
                checks,
                check_id=f"agents-{name}",
                label=f"agents:{name}",
                ok=True,
                ok_message=f"Optional member {name} AGENTS.md skipped (not checked out).",
                fail_message=f"Member {name} AGENTS.md is missing.",
                path=path / "AGENTS.md",
            )
            if name != "cli":
                _add(
                    checks,
                    check_id=f"member-tower-pointer-{name}",
                    label=f"member tower pointer:{name}",
                    ok=True,
                    ok_message=(
                        f"Optional member {name} tower pointer skipped "
                        f"(not checked out)."
                    ),
                    fail_message=f"Member {name} has no control tower pointer.",
                    path=path,
                )
            continue

        _add(
            checks,
            check_id=f"member-{name}",
            label=f"member:{name}",
            ok=present,
            ok_message=(
                f"Member repository {name} is present."
                if required
                else f"Optional member {name} is present (archived fixture)."
            ),
            fail_message=f"Member repository {name} is missing.",
            path=path,
        )
        _add(
            checks,
            check_id=f"agents-{name}",
            label=f"agents:{name}",
            ok=_path_ok(path / "AGENTS.md", want_dir=False),
            ok_message=f"Member {name} AGENTS.md is present.",
            fail_message=f"Member {name} AGENTS.md is missing.",
            path=path / "AGENTS.md",
        )
        if name == "cli":
            continue
        member_kt = path / "cfg" / "knowledge-tower.yaml"
        member_suite = path / "cfg" / "suite.yaml"
        if member_kt.is_file() or member_suite.is_file():
            ok_pointer = True
            if member_kt.is_file():
                ok_pointer = ok_pointer and _file_contains(member_kt, expected_tower)
                ok_pointer = ok_pointer and _file_contains(member_kt, "is_control_tower: false")
            if member_suite.is_file():
                ok_pointer = ok_pointer and _file_contains(member_suite, expected_tower)
            _add(
                checks,
                check_id=f"member-tower-pointer-{name}",
                label=f"member tower pointer:{name}",
                ok=ok_pointer,
                ok_message=f"Member {name} points at the control tower.",
                fail_message=f"Member {name} control tower pointer is mismatched.",
                path=member_kt if member_kt.is_file() else member_suite,
                fail_state="error",
            )
        else:
            _add(
                checks,
                check_id=f"member-tower-pointer-{name}",
                label=f"member tower pointer:{name}",
                ok=_file_contains(path / "AGENTS.md", "HATH0R-CLI"),
                ok_message=f"Member {name} AGENTS.md references HATH0R-CLI.",
                fail_message=f"Member {name} has no control tower pointer.",
                path=path / "AGENTS.md",
                fail_state="error",
            )

    # Catalog drift: tower cfg/products.yaml vs KB hub suite-products.yaml
    tower_products = tower_cfg / "products.yaml"
    hub_map = _catalog_product_map(_load_yaml(catalog))
    tower_map = _catalog_product_map(_load_yaml(tower_products))
    if hub_map is None or tower_map is None:
        drift_ok = False
        drift_msg = "Unable to compare tower and hub product catalogs."
        if hub_map is None and not catalog.is_file():
            drift_msg = "Hub catalog missing; cannot verify catalog drift."
        elif tower_map is None and not tower_products.is_file():
            drift_msg = "Tower products.yaml missing; cannot verify catalog drift."
        elif yaml is None:
            drift_msg = "PyYAML not installed; cannot verify catalog drift."
        else:
            drift_msg = "Catalog YAML is invalid or missing product entries."
    else:
        drift_ok = hub_map == tower_map
        drift_msg = (
            "Tower and hub catalogs agree on product_id and is_control_tower."
            if drift_ok
            else "Tower cfg/products.yaml and hub suite-products.yaml disagree on product_id/is_control_tower."
        )
    _add(
        checks,
        check_id="catalog-drift",
        label="catalog drift",
        ok=drift_ok,
        ok_message=drift_msg,
        fail_message=drift_msg,
        path=catalog,
        fail_state="error",
    )

    tower_configured = any(c.id == "control-tower-root" and c.state == "ok" for c in checks)
    return DoctorResult(
        group_id="hath0r-opensource",
        control_tower_product_id="hath0r-cli",
        control_tower_configured=tower_configured,
        checks=checks,
    )


def diagnostics_for(result: DoctorResult) -> list[dict[str, Any]]:
    """Build diagnostic dicts for failed checks (envelope Diagnostic fields)."""
    out: list[dict[str, Any]] = []
    for c in result.checks:
        if c.state == "ok":
            continue
        code = "DEPENDENCY_CHECK_FAILED"
        if c.id == "canonical-kb":
            code = "KNOWLEDGEBASE_NOT_FOUND"
        elif c.id in {"suite-catalog", "catalog-tower-path", "catalog-drift"}:
            code = "PRODUCT_CATALOG_INVALID" if c.state == "error" else "PRODUCT_CATALOG_NOT_FOUND"
        out.append(
            {
                "code": code,
                "message": c.message,
                "severity": "error",
                "remediation": "Verify the OpenSource group layout and run hath0r doctor --verbose.",
                "provenance": {"component": "hath0r-cli", "operation": "doctor"},
                "details": {"check_id": c.id},
            }
        )
    return out
