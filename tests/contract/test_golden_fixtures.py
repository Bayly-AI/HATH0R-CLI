"""Validate golden contract fixtures against Framework JSON Schemas."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest

from tests.framework_paths import framework_schemas

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REAL_PATH_RE = re.compile(r"/Users/|/home/|\\\\Users\\\\")

COMMAND_DATA_SCHEMA = {
    "version": "hath0r-cli-version-v1.schema.json",
    "doctor": "hath0r-cli-doctor-v1.schema.json",
    "kb.path": "hath0r-cli-kb-path-v1.schema.json",
    "kb.products": "hath0r-cli-kb-products-v1.schema.json",
}

REQUIRED_FIXTURES = [
    "version-ok.json",
    "doctor-ok.json",
    "doctor-degraded.json",
    "kb-path-ok.json",
    "kb-path-missing.json",
    "kb-products-ok.json",
    "kb-products-missing.json",
    "kb-products-invalid.json",
]


def _load_schema(name: str) -> dict:
    path = framework_schemas() / name
    assert path.is_file(), f"missing schema {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _envelope_validator() -> jsonschema.Draft7Validator:
    """Build envelope validator with local diagnostic $ref resolution if present."""
    envelope = _load_schema("hath0r-cli-response-v1.schema.json")
    diagnostic = _load_schema("hath0r-cli-diagnostic-v1.schema.json")
    store = {}
    for schema in (envelope, diagnostic):
        sid = schema.get("$id")
        if sid:
            store[sid] = schema
    # Also allow bare filename refs used in some drafts.
    store["hath0r-cli-diagnostic-v1.schema.json"] = diagnostic
    store["./hath0r-cli-diagnostic-v1.schema.json"] = diagnostic
    resolver = jsonschema.RefResolver.from_schema(envelope, store=store)
    return jsonschema.Draft7Validator(envelope, resolver=resolver)


@pytest.fixture(scope="module")
def envelope_validator() -> jsonschema.Draft7Validator:
    return _envelope_validator()


def test_all_required_fixtures_present() -> None:
    names = {p.name for p in FIXTURES.glob("*.json")}
    assert set(REQUIRED_FIXTURES) <= names
    assert len(REQUIRED_FIXTURES) == 8


@pytest.mark.parametrize("name", REQUIRED_FIXTURES)
def test_fixture_validates_against_framework_schemas(
    name: str, envelope_validator: jsonschema.Draft7Validator
) -> None:
    raw = (FIXTURES / name).read_text(encoding="utf-8")
    assert REAL_PATH_RE.search(raw) is None, f"{name} contains real home paths"
    assert "password" not in raw.lower()
    assert "secret" not in raw.lower() or "no secrets" in raw.lower()

    payload = json.loads(raw)
    for field in ("schema", "command", "generated_at", "state", "data", "diagnostics", "meta"):
        assert field in payload, f"{name} missing {field}"

    assert payload["schema"] == "hath0r.cli.response/1"
    assert payload["generated_at"] == "2026-09-16T00:00:00Z"
    assert payload["meta"]["cli_version"] == "0.2.0"
    assert isinstance(payload["meta"]["duration_ms"], int)
    assert payload["meta"]["duration_ms"] >= 0

    envelope_validator.validate(payload)

    command = payload["command"]
    data = payload["data"]
    if data is not None:
        data_schema_name = COMMAND_DATA_SCHEMA[command]
        jsonschema.Draft7Validator(_load_schema(data_schema_name)).validate(data)
    else:
        assert payload["state"] in {"unavailable", "error"}
        assert payload["diagnostics"], f"{name} error fixture needs diagnostics"

    if payload["state"] != "ok":
        assert payload["diagnostics"], f"{name} non-ok fixture needs diagnostics"
        for diag in payload["diagnostics"]:
            assert "code" in diag and "message" in diag and "severity" in diag
            assert "provenance" in diag


def test_doctor_fixture_counts_agree() -> None:
    for name in ("doctor-ok.json", "doctor-degraded.json"):
        payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        checks = payload["data"]["checks"]
        counts = payload["data"]["counts"]
        ok = sum(1 for c in checks if c["state"] == "ok")
        failed = len(checks) - ok
        assert counts["ok"] == ok
        assert counts["failed"] == failed
        assert counts["ok"] + counts["failed"] == len(checks)
