"""C3 — structured JSON for hath0r --version (schema-backed tests)."""

from __future__ import annotations

import json
import re

import jsonschema
import pytest
from click.testing import CliRunner

from hath0r_cli import __version__, cli
from tests.framework_paths import framework_schemas as _fs

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


FRAMEWORK_SCHEMAS = _fs()


def _load_schema(name: str) -> dict:
    path = FRAMEWORK_SCHEMAS / name
    assert path.is_file(), f"missing Framework schema: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_version_json_matches_framework_schemas(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["--output", "json", "--version"])
    assert result.exit_code == 0, result.output
    assert ANSI_RE.search(result.output) is None
    assert "\x1b" not in result.output

    payload = json.loads(result.output)
    envelope_schema = _load_schema("hath0r-cli-response-v1.schema.json")
    version_schema = _load_schema("hath0r-cli-version-v1.schema.json")

    # Draft-07 validators; $ref to diagnostic is not needed for success path.
    jsonschema.Draft7Validator(envelope_schema).validate(payload)
    assert payload["command"] == "version"
    assert payload["state"] == "ok"
    assert payload["data"] is not None
    jsonschema.Draft7Validator(version_schema).validate(payload["data"])

    assert payload["data"]["binary"] == "hath0r"
    assert payload["data"]["package"] == "hath0r-cli"
    assert payload["data"]["version"] == __version__
    assert SEMVER_RE.match(payload["data"]["version"])
    assert payload["meta"]["cli_version"] == __version__
    assert isinstance(payload["diagnostics"], list)
    assert payload["diagnostics"] == []


def test_version_text_unchanged(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["--output", "text", "--version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"hath0r, version {__version__}"
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)
