"""C6 — structured JSON for hath0r kb products."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli import __version__, cli
from hath0r_cli.catalog import CatalogError, parse_catalog

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
FRAMEWORK_SCHEMAS = Path("/Users/raybayly/Development/OpenSource/hath0r/lib/schemas")


def _schema(name: str) -> dict:
    return json.loads((FRAMEWORK_SCHEMAS / name).read_text(encoding="utf-8"))


def _valid_catalog() -> dict:
    return {
        "group_id": "hath0r-opensource",
        "control_tower_path": "/mock/HATH0R-CLI",
        "products": [
            {
                "product_id": "hath0r-cli",
                "product_name": "HATH0R CLI",
                "role": "control-tower",
                "canonical": True,
                "is_control_tower": True,
                "local_path": "/should/be/stripped",
                "remote": "https://example.invalid",
            },
            {
                "product_id": "hath0r-poc",
                "product_name": "HATHOR POC",
                "role": "integration-test-bed",
                "canonical": True,
                "is_control_tower": False,
            },
        ],
    }


def _write_catalog(kb: Path, data: dict | str) -> Path:
    catalogs = kb / "catalogs"
    catalogs.mkdir(parents=True)
    path = catalogs / "suite-products.yaml"
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_parse_catalog_valid(tmp_path: Path) -> None:
    kb = tmp_path / "kb"
    path = _write_catalog(kb, _valid_catalog())
    result = parse_catalog(path)
    assert result.group_id == "hath0r-opensource"
    assert result.control_tower_product_id == "hath0r-cli"
    assert len(result.products) == 2
    assert set(result.products[0].keys()) == {
        "product_id",
        "product_name",
        "role",
        "canonical",
        "is_control_tower",
    }
    assert "local_path" not in result.products[0]
    assert "remote" not in result.products[0]


def test_parse_catalog_missing(tmp_path: Path) -> None:
    with pytest.raises(CatalogError) as exc:
        parse_catalog(tmp_path / "missing.yaml")
    assert exc.value.code == "PRODUCT_CATALOG_NOT_FOUND"


def test_parse_catalog_malformed_yaml(tmp_path: Path) -> None:
    kb = tmp_path / "kb"
    path = _write_catalog(kb, ":\n  - bad")
    with pytest.raises(CatalogError) as exc:
        parse_catalog(path)
    assert exc.value.code == "PRODUCT_CATALOG_INVALID"


def test_parse_catalog_zero_towers(tmp_path: Path) -> None:
    data = _valid_catalog()
    for p in data["products"]:
        p["is_control_tower"] = False
    path = _write_catalog(tmp_path / "kb", data)
    with pytest.raises(CatalogError) as exc:
        parse_catalog(path)
    assert "exactly one" in exc.value.message


def test_parse_catalog_multiple_towers(tmp_path: Path) -> None:
    data = _valid_catalog()
    for p in data["products"]:
        p["is_control_tower"] = True
    path = _write_catalog(tmp_path / "kb", data)
    with pytest.raises(CatalogError) as exc:
        parse_catalog(path)
    assert "exactly one" in exc.value.message


def test_kb_products_json_ok(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    _write_catalog(kb, _valid_catalog())
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 0, result.output
    assert ANSI_RE.search(result.output) is None
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema("hath0r-cli-response-v1.schema.json")).validate(payload)
    assert payload["command"] == "kb.products"
    assert payload["state"] == "ok"
    assert payload["meta"]["cli_version"] == __version__
    data = payload["data"]
    jsonschema.Draft7Validator(_schema("hath0r-cli-kb-products-v1.schema.json")).validate(data)
    assert data["group_id"] == "hath0r-opensource"
    assert data["control_tower_product_id"] == "hath0r-cli"
    assert len(data["products"]) == 2
    assert payload["diagnostics"] == []


def test_kb_products_json_missing(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HATH0R_KB_PATH", str(tmp_path / "empty-kb"))
    (tmp_path / "empty-kb").mkdir()
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["state"] == "unavailable"
    assert payload["data"] is None
    assert payload["diagnostics"][0]["code"] == "PRODUCT_CATALOG_NOT_FOUND"


def test_kb_products_json_invalid(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    _write_catalog(kb, "not: a: valid: [")
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 2, result.output
    payload = json.loads(result.output)
    assert payload["state"] == "error"
    assert payload["diagnostics"][0]["code"] == "PRODUCT_CATALOG_INVALID"


def test_kb_products_text_prints_raw(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    _write_catalog(kb, _valid_catalog())
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "text", "kb", "products"])
    assert result.exit_code == 0, result.output
    assert "hath0r-cli" in result.output
    assert "product_id" in result.output
