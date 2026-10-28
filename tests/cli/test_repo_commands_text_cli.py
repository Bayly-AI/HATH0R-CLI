"""Text-mode CLI tests for `hath0r repo` with hygiene and sibling bots mocked."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

import hath0r_cli.bots.repo_clean as repo_clean
import hath0r_cli.bots.sibling_bot as sibling_bot
from hath0r_cli.cli import main
from tests.fakebot import patch_bot


def _run(*args: str):
    return CliRunner().invoke(main, ["-o", "text", *args])


@pytest.fixture
def repos(tmp_path, monkeypatch):
    for name in ("alpha", "beta"):
        (tmp_path / name / ".git").mkdir(parents=True)
    (tmp_path / "loose-file").write_text("x", encoding="utf-8")
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(tmp_path))
    return tmp_path


def test_repo_audit_dirty_and_clean(monkeypatch, repos):
    patch_bot(monkeypatch, repo_clean, "RepoHygieneBot",
              {"clean": False, "errant_count": 1, "errant_files": [{"name": "junk.txt", "size_bytes": 3}]})
    patch_bot(monkeypatch, repo_clean, "ConfigOrganizerBot",
              {"clean": False, "misplaced_count": 1, "misplaced_configs": [{"name": ".eslintrc", "recommended_dest": ".cfg/"}]})
    patch_bot(monkeypatch, repo_clean, "KnowledgeOrganizerBot",
              {"organized": False, "findings_count": 1, "findings": [{"file": "AGENTS.md", "lines": 900, "recommendation": "split"}]})
    res = _run("repo", "audit", "--all-repos")
    assert res.exit_code == 1
    assert "junk.txt" in res.output and ".eslintrc" in res.output and "split" in res.output
    assert "alpha" in res.output and "beta" in res.output

    patch_bot(monkeypatch, repo_clean, "RepoHygieneBot", {"clean": True})
    patch_bot(monkeypatch, repo_clean, "ConfigOrganizerBot", {"clean": True})
    patch_bot(monkeypatch, repo_clean, "KnowledgeOrganizerBot", {"organized": True})
    res = _run("repo", "audit", "--repo", str(repos / "alpha"))
    assert res.exit_code == 0 and "Clean (no errant" in res.output


def test_repo_audit_missing_repo():
    res = _run("repo", "audit", "--repo", "/definitely/not/here")
    assert res.exit_code == 1 and "does not exist" in res.output


def test_repo_clean(monkeypatch, repos):
    patch_bot(monkeypatch, repo_clean, "ConfigOrganizerBot", {"relocations": [{"action": "moved .eslintrc"}]})
    patch_bot(monkeypatch, repo_clean, "RepoHygieneBot", {"actions": [{"action": "archived junk.txt"}]})
    res = _run("repo", "clean", "--repo", str(repos / "alpha"), "--dry-run")
    assert "[DRY-RUN]" in res.output and "moved .eslintrc" in res.output

    patch_bot(monkeypatch, repo_clean, "ConfigOrganizerBot", {"relocations": []})
    patch_bot(monkeypatch, repo_clean, "RepoHygieneBot", {"actions": []})
    assert "spotless" in _run("repo", "clean", "--repo", str(repos / "alpha")).output


@pytest.mark.parametrize("cmd", [["repo", "workflow"], ["clean-repos"], ["clean-repo"]])
def test_repo_workflow(monkeypatch, repos, cmd):
    patch_bot(monkeypatch, repo_clean, "CleanReposWorkflowBot", {
        "success": True,
        "repos": [{"repo": "alpha", "path": "/a", "steps": {"01": "ok"}, "clean": True},
                  {"repo": "beta", "path": "/b", "steps": {}, "clean": False, "error": "dirty tree"}],
    })
    res = _run(*cmd, "--repo", str(repos / "alpha"), "--no-commit")
    assert res.exit_code == 0, res.output
    assert "Fully In Sync" in res.output and "dirty tree" in res.output


def test_repo_siblings(monkeypatch):
    report = {
        "all_canonical_present": False,
        "products": {
            "atc": {"name": "ATC", "present": True, "local_version": "0.2", "remote_version": "0.3", "path": "/atc"},
            "mcp": {"name": "MCP", "present": False, "canonical": True},
            "opt": {"present": False},
        },
    }
    patch_bot(monkeypatch, sibling_bot, "SiblingManagerBot", report)
    res = _run("repo", "siblings", "--check-remote")
    assert res.exit_code == 0 and "Some canonical siblings are missing" in res.output


@pytest.mark.parametrize(
    "install, container, args, code, fragment",
    [
        ({"success": True, "name": "atc", "path": "/p", "version": "1", "installed_deps": True},
         {"success": True, "source": "local", "container_name": "c"}, ["--container", "--image-url", "u"], 0, "local git"),
        ({"success": True, "name": "atc", "path": "/p", "already_installed": True}, None, [], 0, "Already installed"),
        ({"success": True, "name": "atc", "path": "/p"}, {"success": False, "error": "no docker"},
         ["--container", "--no-prompt"], 1, "no docker"),
        ({"success": False, "error": "404"}, None, [], 1, ""),
    ],
)
def test_repo_install(monkeypatch, install, container, args, code, fragment):
    class Bot:
        def download_and_install(self, *a, **k):
            return dict(install)

        def install_container(self, *a, **k):
            return dict(container or {})

    monkeypatch.setattr(sibling_bot, "SiblingManagerBot", Bot)
    res = _run("repo", "install", "hath0r-atc", *args)
    assert res.exit_code == code, res.output
    assert fragment in res.output


def test_repo_ensure(monkeypatch):
    results = [
        {"name": "atc", "action": "already_present", "path": "/a"},
        {"name": "mcp", "action": "would_install", "repo": "o/mcp"},
        {"product_id": "kb", "success": True, "path": "/k"},
        {"name": "x", "success": False, "error": "denied"},
    ]
    patch_bot(monkeypatch, sibling_bot, "SiblingManagerBot", {"success": False, "results": results})
    res = _run("repo", "ensure", "--dry-run")
    assert res.exit_code == 1
    for fragment in ("already installed", "would install", "installed (/k)", "denied"):
        assert fragment in res.output
