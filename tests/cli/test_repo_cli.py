"""CLI integration tests for repo audit and clean with --repo and --all-repos flags."""

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_repo_audit_single_repo(tmp_path: Path):
    runner = CliRunner()
    # Setup clean repo structure
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")

    res = runner.invoke(main, ["--output", "json", "repo", "audit", "--repo", str(tmp_path)])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "repo.audit"
    assert data["state"] == "ok"
    assert data["data"]["all_clean"] is True
    assert data["data"]["repo_count"] == 1


def test_cli_repo_clean_dry_run(tmp_path: Path):
    runner = CliRunner()
    # Setup stray file
    (tmp_path / "stray.tmp").write_text("temp", encoding="utf-8")

    res = runner.invoke(main, ["--output", "json", "repo", "clean", "--repo", str(tmp_path), "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "repo.clean"
    assert data["data"]["dry_run"] is True
    assert data["data"]["repo_count"] == 1


def test_cli_repo_audit_all_repos(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    # Mock group root with two repos
    repo_a = tmp_path / "repo-a"
    repo_b = tmp_path / "repo-b"
    repo_a.mkdir()
    repo_b.mkdir()
    (repo_a / ".git").mkdir()
    (repo_b / ".git").mkdir()
    (repo_a / "AGENTS.md").write_text("# Repo A\n", encoding="utf-8")
    (repo_b / "AGENTS.md").write_text("# Repo B\n", encoding="utf-8")

    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    res = runner.invoke(main, ["--output", "json", "repo", "audit", "--all-repos"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "repo.audit"
    assert data["data"]["repo_count"] == 2


def test_cli_repo_siblings(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    res = runner.invoke(main, ["--output", "json", "repo", "siblings"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "repo.siblings"
    assert "products" in data["data"]
    assert "hath0r-atc" in data["data"]["products"]
    assert "hath0r-mcp" in data["data"]["products"]


def test_cli_repo_ensure_dry_run(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    res = runner.invoke(main, ["--output", "json", "repo", "ensure", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "repo.ensure"
    assert data["data"]["success"] is True
    assert data["data"]["dry_run"] is True


def test_cli_repo_install_mock(tmp_path: Path, monkeypatch):
    runner = CliRunner()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))

    # Pre-create directory so it acts as already installed
    atc_dir = tmp_path / "hath0r-atc"
    atc_dir.mkdir()
    (atc_dir / "VERSION").write_text("0.2.2\n", encoding="utf-8")

    res = runner.invoke(main, ["--output", "json", "repo", "install", "hath0r-atc"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "repo.install"
    assert data["data"]["success"] is True
    assert data["data"]["already_installed"] is True

