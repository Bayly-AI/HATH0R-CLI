"""Text-mode CLI tests for `hath0r factory`, run inside a scratch group root."""

from __future__ import annotations

import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli.cli import main

FACTORY = {
    "factory_id": "demo",
    "name": "Demo Factory",
    "version": "1.0.0",
    "description": "  Scratch factory for tests.  ",
    "bots": [{"id": "git", "name": "Git Bot", "capabilities": ["status", "log"]}],
    "workflows": [
        {
            "id": "nightly",
            "name": "Nightly",
            "schedule": "0 3 * * *",
            "steps": [{"bot": "git", "action": "status"}, {"bot": "nope", "action": "missing"}],
        },
        {"id": "adhoc", "name": "Ad hoc", "steps": [{"bot": "git", "action": "status"}]},
    ],
}


@pytest.fixture
def group(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_text("# hath0r-opensource group\n", encoding="utf-8")
    (tmp_path / ".hath0r").mkdir()
    factories = tmp_path / "cfg" / "factories"
    factories.mkdir(parents=True)
    (factories / "demo.yaml").write_text(yaml.safe_dump(FACTORY), encoding="utf-8")
    (factories / "broken.yaml").write_text("factory_id: [unclosed", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _run(*args: str, fmt: str = "text"):
    res = CliRunner().invoke(main, ["-o", fmt, "factory", *args])
    assert res.exception is None or isinstance(res.exception, SystemExit), res.output
    return res


def test_factory_list_and_info_text(group):
    assert "Demo Factory" in _run("list").output or "demo" in _run("list").output
    info = _run("info", "demo")
    assert info.exit_code == 0
    assert "Git Bot" in info.output and "Nightly" in info.output
    assert _run("info", "absent").exit_code == 1


def test_factory_run_text(group):
    assert _run("run", "absent", "--dry-run").exit_code == 1
    res = _run("run", "demo", "--dry-run")
    assert "Executed factory 'demo'" in res.output
    _run("run", "demo", "-w", "adhoc", "--dry-run", fmt="json")


def test_factory_crud_text(group):
    assert _run("create", "fresh", "--name", "Fresh", "--dry-run").exit_code == 0
    assert "Created factory 'fresh'" in _run("create", "fresh", "--name", "Fresh", "--description", "d").output
    assert _run("create", "fresh").exit_code == 1
    assert _run("create", "fresh", "--force").exit_code == 0
    assert _run("update", "fresh", "--version", "2.0.0", "--dry-run").exit_code == 0
    assert _run("update", "fresh", "--name", "Fresher", "--description", "x").exit_code == 0
    assert _run("update", "absent", "--name", "X").exit_code == 1
    assert _run("delete", "fresh", "--dry-run").exit_code == 0
    assert _run("delete", "fresh").exit_code == 0
    assert _run("delete", "fresh").exit_code == 1


def test_factory_schedule_text(group, tmp_path):
    listing = _run("schedule", "list")
    assert listing.exit_code == 0 and listing.output.strip()
    target = tmp_path / "target"
    target.mkdir()
    assert _run("schedule", "sync", "--target-dir", str(target), "--dry-run").exit_code == 0
    assert _run("schedule", "sync", "--target-dir", str(target)).exit_code == 0


def test_factory_schedule_empty_text(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_text("hath0r-opensource\n", encoding="utf-8")
    (tmp_path / ".hath0r").mkdir()
    (tmp_path / "cfg" / "factories").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    assert "No factories found" in _run("list").output
    assert _run("schedule", "list").exit_code == 0
    assert _run("schedule", "sync", "--target-dir", str(tmp_path), "--dry-run").exit_code == 0
