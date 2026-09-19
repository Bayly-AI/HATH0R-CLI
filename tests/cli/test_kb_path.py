"""C5 — structured JSON for hath0r kb path."""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from hath0r_cli import __version__, cli
from tests.framework_paths import framework_schemas as _fs

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


FRAMEWORK_SCHEMAS = _fs()


def _schema(name: str) -> dict:
    return json.loads((FRAMEWORK_SCHEMAS / name).read_text(encoding="utf-8"))


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_kb_path_json_present(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "knowledgebase"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 0, result.output
    assert ANSI_RE.search(result.output) is None
    payload = json.loads(result.output)
    jsonschema.Draft7Validator(_schema("hath0r-cli-response-v1.schema.json")).validate(payload)
    assert payload["command"] == "kb.path"
    assert payload["state"] == "ok"
    assert payload["meta"]["cli_version"] == __version__
    data = payload["data"]
    jsonschema.Draft7Validator(_schema("hath0r-cli-kb-path-v1.schema.json")).validate(data)
    assert data["configured"] is True
    assert data["available"] is True
    assert data["path"] == str(kb)
    assert payload["diagnostics"] == []


def test_kb_path_json_missing(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "no-such-kb"
    monkeypatch.setenv("HATH0R_KB_PATH", str(missing))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["command"] == "kb.path"
    assert payload["state"] == "unavailable"
    data = payload["data"]
    assert data["configured"] is True
    assert data["available"] is False
    assert data["path"] == str(missing)
    codes = [d["code"] for d in payload["diagnostics"]]
    assert "KNOWLEDGEBASE_NOT_FOUND" in codes


def test_kb_path_json_override(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "custom-kb"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    # Also set a bogus group root to prove KB override wins for path resolution.
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path / "not-a-group"))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["data"]["path"] == str(kb)
    assert payload["data"]["available"] is True


def test_kb_path_text_unchanged(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "text", "kb", "path"])
    assert result.exit_code == 0
    assert result.output.strip() == str(kb)


def test_kb_path_text_missing(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "gone"
    monkeypatch.setenv("HATH0R_KB_PATH", str(missing))
    result = runner.invoke(cli.main, ["--output", "text", "kb", "path"])
    assert result.exit_code != 0
    assert str(missing) in result.output
