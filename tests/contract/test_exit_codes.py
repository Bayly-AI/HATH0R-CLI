"""Exit code / envelope state agreement (Framework exit-codes contract)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner  # noqa: F401 — used via fixture type elsewhere

from hath0r_cli import cli
from tests.framework_paths import framework_exit_codes


def test_exit_code_contract_file_exists() -> None:
    assert framework_exit_codes().is_file()


def test_success_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["--output", "json", "--version"])
    assert result.exit_code == 0
    assert json.loads(result.output)["state"] == "ok"


def test_doctor_degraded_maps_to_exit_6(
    runner: CliRunner, mock_group_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (mock_group_root / "AGENTS.md").unlink()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(mock_group_root))
    result = runner.invoke(cli.main, ["--output", "json", "doctor"])
    assert result.exit_code == 6
    payload = json.loads(result.output)
    assert payload["state"] == "degraded"


def test_not_found_maps_to_exit_3(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HATH0R_KB_PATH", str(tmp_path / "missing"))
    result = runner.invoke(cli.main, ["--output", "json", "--quiet", "kb", "path"])
    assert result.exit_code == 3
    assert json.loads(result.output)["state"] == "unavailable"


def test_validation_maps_to_exit_2(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kb = tmp_path / "kb"
    (kb / "catalogs").mkdir(parents=True)
    (kb / "catalogs" / "suite-products.yaml").write_text("{]", encoding="utf-8")
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    result = runner.invoke(cli.main, ["--output", "json", "kb", "products"])
    assert result.exit_code == 2
    assert json.loads(result.output)["state"] == "error"
