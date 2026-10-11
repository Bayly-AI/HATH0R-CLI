"""CLI tests for ATC and MCP sibling commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_atc_status_missing(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    res = runner.invoke(main, ["--output", "json", "atc", "status"])
    assert res.exit_code == 6
    data = json.loads(res.output)
    assert data["command"] == "atc.status"
    assert data["state"] == "error"
    assert data["data"]["installed"] is False


def test_cli_atc_status_present(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    atc_dir = tmp_path / "hath0r-atc"
    atc_dir.mkdir()
    (atc_dir / "VERSION").write_text("0.2.2\n", encoding="utf-8")

    res = runner.invoke(main, ["--output", "json", "atc", "status"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "atc.status"
    assert data["state"] == "ok"
    assert data["data"]["installed"] is True
    assert data["data"]["version"] == "0.2.2"


def test_cli_atc_install_already_installed(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    atc_dir = tmp_path / "hath0r-atc"
    atc_dir.mkdir()
    (atc_dir / "VERSION").write_text("0.2.2\n", encoding="utf-8")

    res = runner.invoke(main, ["--output", "json", "atc", "install"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "atc.install"
    assert data["state"] == "ok"
    assert data["data"]["already_installed"] is True


def test_cli_mcp_install_already_installed(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    mcp_dir = tmp_path / "hath0r-mcp"
    mcp_dir.mkdir()
    (mcp_dir / "VERSION").write_text("1.0.1\n", encoding="utf-8")

    res = runner.invoke(main, ["--output", "json", "mcp", "install"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "mcp.install"
    assert data["state"] == "ok"
    assert data["data"]["already_installed"] is True
