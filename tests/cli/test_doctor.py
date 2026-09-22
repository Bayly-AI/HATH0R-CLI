"""C4 — structured JSON for hath0r doctor."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import jsonschema
import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli import __version__, cli
from hath0r_cli.doctor import run_checks
from tests.framework_paths import framework_schemas as _fs

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
REAL_GROUP = Path("/Users/raybayly/Development/OpenSource")


FRAMEWORK_SCHEMAS = _fs()


def _schema(name: str) -> dict:
    return json.loads((FRAMEWORK_SCHEMAS / name).read_text(encoding="utf-8"))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_minimal_group(root: Path) -> Path:
    """Build a complete-enough OpenSource group under root for doctor to pass."""
    group = root / "OpenSource"
    group.mkdir()
    _write(group / "AGENTS.md", "group: hath0r-opensource\n")
    _write(group / "WARP.md", "policy\n")
    (group / ".hath0r" / "knowledgebase" / "catalogs").mkdir(parents=True)

    tower = str(group / "HATH0R-CLI")
    products = {
        "group_id": "hath0r-opensource",
        "products": [
            {
                "product_id": "hath0r-cli",
                "product_name": "HATH0R CLI",
                "role": "control-tower",
                "canonical": True,
                "is_control_tower": True,
            },
            {
                "product_id": "hath0r-framework",
                "product_name": "HATHOR Framework",
                "role": "framework",
                "canonical": True,
                "is_control_tower": False,
            },
            {
                "product_id": "hath0r-poc",
                "product_name": "HATHOR POC",
                "role": "poc",
                "canonical": False,
                "is_control_tower": False,
            },
        ],
    }
    hub_catalog = {
        "group_id": "hath0r-opensource",
        "control_tower_path": tower,
        "products": products["products"],
    }
    _write(
        group / ".hath0r" / "knowledgebase" / "catalogs" / "suite-products.yaml",
        yaml.safe_dump(hub_catalog),
    )

    # Control tower
    cli_root = group / "HATH0R-CLI"
    (cli_root / "cfg").mkdir(parents=True)
    _write(cli_root / "AGENTS.md", "HATH0R-CLI\n")
    _write(
        cli_root / "cfg" / "control-tower.yaml",
        f"remote: Bayly-AI/HATH0R-CLI\nlocal_path: {tower}\n",
    )
    _write(
        cli_root / "cfg" / "suite.yaml",
        f"control_tower_path: {tower}\nproduct_id: hath0r-cli\n",
    )
    _write(
        cli_root / "cfg" / "knowledge-tower.yaml",
        f"is_control_tower: true\ncontrol_tower_path: {tower}\n",
    )
    _write(cli_root / "cfg" / "products.yaml", yaml.safe_dump(products))

    # Framework + POC members
    for name, product_id in (("hath0r", "hath0r-framework"), ("hath0r-poc", "hath0r-poc")):
        member = group / name
        (member / "cfg").mkdir(parents=True)
        _write(member / "AGENTS.md", "HATH0R-CLI control tower\n")
        _write(
            member / "cfg" / "knowledge-tower.yaml",
            f"is_control_tower: false\ncontrol_tower_path: {tower}\n",
        )
        _write(
            member / "cfg" / "suite.yaml",
            f"control_tower_path: {tower}\nproduct_id: {product_id}\n",
        )

    return group


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_run_checks_all_pass(tmp_path: Path) -> None:
    group = _build_minimal_group(tmp_path)
    result = run_checks(group, group / ".hath0r" / "knowledgebase")
    assert result.failed_count == 0
    assert result.overall_state == "ok"
    assert result.ok_count == len(result.checks)
    data = result.to_data(verbose=False)
    assert data["counts"]["ok"] + data["counts"]["failed"] == len(data["checks"])
    assert all("path" not in c for c in data["checks"])
    ids = [c["id"] for c in data["checks"]]
    assert "catalog-drift" in ids
    assert all(re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", i) for i in ids)


def test_run_checks_optional_poc_absent(tmp_path: Path) -> None:
    """Archived non-canonical POC may be omitted without failing doctor."""
    group = _build_minimal_group(tmp_path)
    shutil.rmtree(group / "hath0r-poc")
    result = run_checks(group, group / ".hath0r" / "knowledgebase")
    assert result.failed_count == 0
    assert result.overall_state == "ok"
    member = next(c for c in result.checks if c.id == "member-poc")
    assert member.state == "ok"
    assert "not checked out" in member.message


def test_run_checks_missing_kb(tmp_path: Path) -> None:
    group = _build_minimal_group(tmp_path)
    shutil.rmtree(group / ".hath0r" / "knowledgebase")
    result = run_checks(group, group / ".hath0r" / "knowledgebase")
    assert result.overall_state == "degraded"
    assert result.failed_count >= 1
    kb = next(c for c in result.checks if c.id == "canonical-kb")
    assert kb.state == "unavailable"


def test_doctor_json_success(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    group = _build_minimal_group(tmp_path)
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(group))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code == 0, result.output
    assert ANSI_RE.search(result.output) is None
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema("hath0r-cli-response-v1.schema.json")).validate(payload)
    assert payload["command"] == "doctor"
    assert payload["state"] == "ok"
    assert payload["meta"]["cli_version"] == __version__
    data = payload["data"]
    jsonschema.Draft7Validator(_schema("hath0r-cli-doctor-v1.schema.json")).validate(data)
    assert data["counts"]["ok"] + data["counts"]["failed"] == len(data["checks"])
    assert data["counts"]["failed"] == 0
    assert all("path" not in c for c in data["checks"])
    assert payload["diagnostics"] == []


def test_doctor_json_degraded_exit_6(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = _build_minimal_group(tmp_path)
    (group / "WARP.md").unlink()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(group))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code == 6, result.output
    payload = json.loads(result.output)
    assert payload["state"] == "degraded"
    assert payload["data"]["counts"]["failed"] >= 1
    assert any(d.get("details", {}).get("check_id") for d in payload["diagnostics"])


def test_doctor_json_verbose_includes_paths(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = _build_minimal_group(tmp_path)
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(group))
    result = runner.invoke(cli.main, ["--output", "json", "--verbose", "doctor"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert any("path" in c for c in payload["data"]["checks"])


def test_doctor_text_still_renders(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = _build_minimal_group(tmp_path)
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(group))
    result = runner.invoke(cli.main, ["--output", "text", "doctor"])
    assert result.exit_code == 0, result.output
    assert "HATH0R doctor" in result.output
    assert f"hath0r {__version__}" in result.output
    assert "doctor passed" in result.output


def test_doctor_catalog_drift_detected(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    group = _build_minimal_group(tmp_path)
    # Break tower products catalog
    bad = {
        "group_id": "hath0r-opensource",
        "products": [
            {
                "product_id": "hath0r-cli",
                "product_name": "HATH0R CLI",
                "role": "control-tower",
                "canonical": True,
                "is_control_tower": False,  # drift
            }
        ],
    }
    (group / "HATH0R-CLI" / "cfg" / "products.yaml").write_text(
        yaml.safe_dump(bad), encoding="utf-8"
    )
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(group))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code == 6
    payload = json.loads(result.output)
    drift = next(c for c in payload["data"]["checks"] if c["id"] == "catalog-drift")
    assert drift["state"] != "ok"


@pytest.mark.skipif(not REAL_GROUP.is_dir(), reason="real OpenSource group not present")
def test_doctor_real_group_smoke(runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(REAL_GROUP))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code in {0, 6}, result.output
    payload = json.loads(result.output)
    assert payload["command"] == "doctor"
    assert payload["schema"] == "hath0r.cli.response/1"
