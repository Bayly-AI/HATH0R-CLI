"""Contract tests: CLI JSON against Framework schemas + exit agreement."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from hath0r_cli import cli


def _schema(framework_schemas: Path, name: str) -> dict:
    return json.loads((framework_schemas / name).read_text(encoding="utf-8"))


def test_version_contract(runner: CliRunner, framework_schemas: Path) -> None:
    result = runner.invoke(cli.main, ["--output", "json", "--version"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema(framework_schemas, "hath0r-cli-response-v1.schema.json")).validate(payload)
    jsonschema.Draft7Validator(_schema(framework_schemas, "hath0r-cli-version-v1.schema.json")).validate(
        payload["data"]
    )


def test_doctor_contract_ok(
    runner: CliRunner, mock_group_root: Path, framework_schemas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(mock_group_root))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema(framework_schemas, "hath0r-cli-response-v1.schema.json")).validate(payload)
    jsonschema.Draft7Validator(_schema(framework_schemas, "hath0r-cli-doctor-v1.schema.json")).validate(payload["data"])
    assert payload["state"] == "ok"


def test_doctor_contract_exit_6_on_failure(
    runner: CliRunner, mock_group_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (mock_group_root / "WARP.md").unlink()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(mock_group_root))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code == 6
    payload = json.loads(result.output)
    assert payload["state"] == "degraded"


def test_kb_path_contract(
    runner: CliRunner, mock_kb: Path, framework_schemas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HATH0R_KB_PATH", str(mock_kb))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema(framework_schemas, "hath0r-cli-kb-path-v1.schema.json")).validate(
        payload["data"]
    )


def test_kb_path_exit_3_missing(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_KB_PATH", str(tmp_path / "nope"))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["state"] == "unavailable"
    assert payload["diagnostics"][0]["code"] == "KNOWLEDGEBASE_NOT_FOUND"


def test_kb_products_contract(
    runner: CliRunner, mock_kb: Path, framework_schemas: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HATH0R_KB_PATH", str(mock_kb))
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema(framework_schemas, "hath0r-cli-kb-products-v1.schema.json")).validate(
        payload["data"]
    )


def test_kb_products_exit_2_invalid(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kb = tmp_path / "kb"
    (kb / "catalogs").mkdir(parents=True)
    (kb / "catalogs" / "suite-products.yaml").write_text(":\n bad", encoding="utf-8")
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload["diagnostics"][0]["code"] == "PRODUCT_CATALOG_INVALID"


def test_kb_products_exit_3_missing(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_KB_PATH", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["diagnostics"][0]["code"] == "PRODUCT_CATALOG_NOT_FOUND"
