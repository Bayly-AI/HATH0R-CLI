"""Tests for --output modes and hath0r.cli.response/1 envelope."""

from __future__ import annotations

import json
import re
from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli import __version__, cli
from hath0r_cli.envelope import RESPONSE_SCHEMA, CliResponse, Diagnostic, ResponseMeta
from hath0r_cli.output import emit, progress_err, resolve_output_mode


RFC3339_Z = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$"
)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _parse_envelope(stdout: str) -> dict:
    return json.loads(stdout)


def test_resolve_output_mode_auto_tty() -> None:
    tty = StringIO()
    tty.isatty = lambda: True  # type: ignore[method-assign]
    assert resolve_output_mode("auto", stdout=tty) == "text"


def test_resolve_output_mode_auto_non_tty() -> None:
    pipe = StringIO()
    pipe.isatty = lambda: False  # type: ignore[method-assign]
    assert resolve_output_mode("auto", stdout=pipe) == "json"


def test_resolve_output_mode_explicit() -> None:
    assert resolve_output_mode("json") == "json"
    assert resolve_output_mode("text") == "text"


def test_envelope_to_dict_shape() -> None:
    resp = CliResponse(
        command="version",
        generated_at="2026-09-16T16:00:00Z",
        state="ok",
        data={"version": "0.2.0"},
        diagnostics=[
            Diagnostic(
                code="INTERNAL_ERROR",
                message="boom",
                severity="error",
                remediation="retry",
            )
        ],
        meta=ResponseMeta(cli_version="0.2.0", duration_ms=3),
    )
    payload = resp.to_dict()
    assert payload["schema"] == RESPONSE_SCHEMA
    assert payload["schema"] == "hath0r.cli.response/1"
    assert payload["command"] == "version"
    assert payload["state"] == "ok"
    assert payload["data"]["version"] == "0.2.0"
    assert payload["diagnostics"][0]["code"] == "INTERNAL_ERROR"
    assert payload["meta"]["cli_version"] == "0.2.0"
    assert payload["meta"]["duration_ms"] == 3


def test_emit_json_no_ansi() -> None:
    buf = StringIO()
    resp = CliResponse(
        command="version",
        generated_at="2026-09-16T16:00:00Z",
        state="ok",
        data=None,
        meta=ResponseMeta(cli_version="0.2.0", duration_ms=0),
    )
    mode = emit(resp, "json", stdout=buf)
    assert mode == "json"
    raw = buf.getvalue()
    assert raw.endswith("\n")
    assert ANSI_RE.search(raw) is None
    assert "\x1b" not in raw
    payload = json.loads(raw)
    assert payload["schema"] == "hath0r.cli.response/1"


def test_emit_text_calls_renderer() -> None:
    called = {"n": 0}

    def renderer() -> None:
        called["n"] += 1

    resp = CliResponse(command="version", generated_at="2026-09-16T16:00:00Z", state="ok")
    mode = emit(resp, "text", text_renderer=renderer)
    assert mode == "text"
    assert called["n"] == 1


def test_progress_err_respects_quiet() -> None:
    err = StringIO()
    progress_err("working", quiet=False, stream=err)
    assert "working" in err.getvalue()
    err2 = StringIO()
    progress_err("working", quiet=True, stream=err2)
    assert err2.getvalue() == ""


def test_version_json(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["--output", "json", "--version"])
    assert result.exit_code == 0, result.output
    assert ANSI_RE.search(result.output) is None
    payload = _parse_envelope(result.output)
    assert payload["schema"] == "hath0r.cli.response/1"
    assert payload["command"] == "version"
    assert payload["state"] == "ok"
    assert RFC3339_Z.match(payload["generated_at"])
    # Ensure generated_at parses as datetime
    datetime.fromisoformat(payload["generated_at"].replace("Z", "+00:00"))
    assert payload["meta"]["cli_version"] == __version__
    assert isinstance(payload["meta"]["duration_ms"], int)
    assert payload["meta"]["duration_ms"] >= 0
    assert payload["data"]["binary"] == "hath0r"
    assert payload["data"]["package"] == "hath0r-cli"
    assert payload["data"]["version"] == __version__
    assert isinstance(payload["diagnostics"], list)


def test_version_text(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["--output", "text", "--version"])
    assert result.exit_code == 0, result.output
    assert f"hath0r, version {__version__}" in result.output
    # Must not be JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


def test_version_short_flag_json(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["-o", "json", "--version"])
    assert result.exit_code == 0
    payload = _parse_envelope(result.output)
    assert payload["command"] == "version"


def test_auto_non_tty_uses_json(runner: CliRunner) -> None:
    # CliRunner stdout is not a TTY by default.
    result = runner.invoke(cli.main, ["-o", "auto", "--version"])
    assert result.exit_code == 0
    payload = _parse_envelope(result.output)
    assert payload["schema"] == "hath0r.cli.response/1"


def test_package_version_is_020() -> None:
    assert __version__ == "0.2.0"
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    assert 'version = "0.2.0"' in text


def test_doctor_json_basic_envelope(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Minimal env so doctor can run without the real group (will report failures).
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path / "missing-group"))
    (tmp_path / "missing-group").mkdir()
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    # Doctor exits non-zero when checks fail; envelope still emitted.
    assert result.output.strip()
    assert ANSI_RE.search(result.output) is None
    payload = _parse_envelope(result.output)
    assert payload["schema"] == "hath0r.cli.response/1"
    assert payload["command"] == "doctor"
    assert payload["state"] in {"ok", "degraded", "unavailable", "error"}
    assert payload["meta"]["cli_version"] == __version__
    assert isinstance(payload["meta"]["duration_ms"], int)
    assert payload["meta"]["duration_ms"] >= 0
    assert "data" in payload
    assert isinstance(payload["diagnostics"], list)


def test_doctor_text_still_works(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "OpenSource"
    root.mkdir()
    (root / "AGENTS.md").write_text("hath0r-opensource\n", encoding="utf-8")
    (root / ".hath0r").mkdir()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(root))
    result = runner.invoke(cli.main, ["--output", "text", "doctor"])
    # Text mode should still produce human-readable doctor output.
    assert "HATH0R doctor" in result.output or "group root" in result.output
    assert f"hath0r {__version__}" in result.output


def test_kb_path_json_envelope(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["command"] == "kb.path"
    assert payload["state"] == "ok"
    assert payload["schema"] == "hath0r.cli.response/1"


def test_kb_path_text_preserves_path(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "text", "kb", "path"])
    assert result.exit_code == 0
    assert str(kb) in result.output


def test_quiet_suppresses_stderr_progress(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))

    noisy = runner.invoke(cli.main, ["--output", "json", "kb", "path"])
    quiet = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert quiet.exit_code == 0, quiet.stdout
    assert noisy.exit_code == 0, noisy.stdout

    assert "resolving" in (noisy.stderr or "")
    assert "resolving" not in (quiet.stderr or "")

    # stdout remains pure JSON in both cases (no ANSI, no progress).
    assert _parse_envelope(quiet.stdout)["command"] == "kb.path"
    assert _parse_envelope(noisy.stdout)["command"] == "kb.path"
    assert "resolving" not in quiet.stdout
    assert "resolving" not in noisy.stdout
