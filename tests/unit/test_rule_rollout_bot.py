"""Tests for RuleRolloutBot and `hath0r rules` (#528)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import pytest
from click.testing import CliRunner

from hath0r_cli.bots import run_cmd
from hath0r_cli.bots.rule_rollout_bot import (
    CANONICAL_RULE_SECTIONS,
    RuleRolloutBot,
    bump_patch,
    changelog_with_entry,
    insert_section,
    remote_slug,
)

RULE = "CR-CLI-ENTRY-001"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _make_repo(root: Path, remotes: Path, name: str, files: Dict[str, str], remote: Optional[str] = None) -> Path:
    """Create ``root/name`` with ``files`` on ``development``, pushed to a bare remote."""
    remote = remote or name
    bare = remotes / f"{remote}.git"
    if not bare.exists():
        bare.parent.mkdir(parents=True, exist_ok=True)
        _git(remotes, "init", "-q", "--bare", "-b", "development", str(bare))
        seed = remotes / f"{remote}-seed"
        seed.mkdir()
        _git(seed, "init", "-q", "-b", "development")
        for rel, text in files.items():
            (seed / rel).write_text(text, encoding="utf-8")
        _git(seed, "add", "-A")
        _git(seed, "commit", "-q", "-m", "seed")
        _git(seed, "remote", "add", "origin", str(bare))
        _git(seed, "push", "-q", "origin", "development")
    repo = root / name
    _git(root, "clone", "-q", "-b", "development", str(bare), str(repo))
    return repo


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for key, val in {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }.items():
        monkeypatch.setenv(key, val)
    root = tmp_path / "Development"
    remotes = tmp_path / "remotes"
    root.mkdir()
    remotes.mkdir()
    agents = "# AGENTS.md — X\n\nIntro.\n\n## CR-OTHER-RULE-001\n\nBody.\n"
    _make_repo(
        root,
        remotes,
        "alpha",
        {
            "AGENTS.md": agents,
            "VERSION": "1.2.3\n",
            "pyproject.toml": '[project]\nname = "alpha"\nversion = "1.2.3"\n',
            "CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n\n- wip\n\n## [1.2.3] - 2026-01-01\n\n- old\n",
        },
    )
    _make_repo(root, remotes, "alpha-clone", {}, remote="alpha")
    _make_repo(root, remotes, "beta", {"AGENTS.md": f"# A\n\n## {RULE}: x\n", "VERSION": "0.1.0\n"})
    _make_repo(root, remotes, "gamma", {"AGENTS.md": agents, "VERSION": "0.2.0\n", "CHANGELOG.md": "## [0.2.0]\n"})
    _make_repo(root, remotes, "delta", {"README.md": "x\n"})
    _make_repo(root, remotes, "zeta", {"AGENTS.md": agents, "package.json": '{\n  "version": "0.0.1"\n}\n'})
    return root, remotes


class FakeGh:
    """Pass git through; answer `gh` and map origin URLs to GitHub slugs."""

    def __init__(self, pending: Optional[Dict[str, str]] = None) -> None:
        self.pending = pending or {}
        self.calls: List[List[str]] = []

    def __call__(self, args: List[str], cwd: Optional[Path] = None):
        self.calls.append(list(args))
        if args[0] == "gh" and args[1:3] == ["pr", "list"]:
            slug = args[args.index("-R") + 1]
            return 0, json.dumps([{"url": self.pending[slug]}] if slug in self.pending else []), ""
        if args[0] == "gh" and args[1:3] == ["pr", "create"]:
            return 0, f"https://github.com/{args[args.index('-R') + 1]}/pull/99", ""
        if args[0] == "git" and args[-3:] == ["remote", "get-url", "origin"]:
            code, out, err = run_cmd(args, cwd)
            name = Path(out).name.removesuffix(".git") if code == 0 else ""
            return code, f"https://github.com/Org/{name}.git", err
        return run_cmd(args, cwd)


def _by_repo(res):
    return {r["repo"]: r for r in res["repos"]}


# ------------------------------------------------------------------ helpers


def test_bump_patch():
    assert bump_patch("1.2.3") == "1.2.4"
    assert bump_patch(None) == "0.1.0"
    assert bump_patch("not-semver") == "0.1.0"


def test_insert_section_above_first_heading_or_appended():
    assert insert_section("# T\n\n## A\n", "## NEW\n\n") == "# T\n\n## NEW\n\n## A\n"
    assert insert_section("# T\n", "## NEW\n\n") == "# T\n\n## NEW\n\n"


def test_changelog_entry_keeps_unreleased_on_top():
    out = changelog_with_entry("# C\n\n## [Unreleased]\n\n## [1.0.0]\n", "1.0.1", "e")
    assert out.index("[Unreleased]") < out.index("[1.0.1]") < out.index("[1.0.0]")
    assert "## [0.1.0]" in changelog_with_entry(None, "0.1.0", "e")


def test_remote_slug():
    assert remote_slug("https://github.com/Bayly-AI/HATH0R-CLI.git") == "Bayly-AI/HATH0R-CLI"
    assert remote_slug("git@github.com:somesayray/Ray-AI.git") == "somesayray/Ray-AI"
    assert remote_slug("/tmp/x.git") is None


def test_resolve_rule(tmp_path: Path):
    assert RuleRolloutBot.resolve_rule(RULE)["section"] == CANONICAL_RULE_SECTIONS[RULE]["section"]
    with pytest.raises(ValueError):
        RuleRolloutBot.resolve_rule("not-a-rule")
    with pytest.raises(ValueError):
        RuleRolloutBot.resolve_rule("CR-UNKNOWN-RULE-001")
    bad = tmp_path / "s.md"
    bad.write_text("## CR-OTHER-001\n")
    with pytest.raises(ValueError):
        RuleRolloutBot.resolve_rule("CR-NEW-RULE-001", bad)
    good = tmp_path / "g.md"
    good.write_text("## CR-NEW-RULE-001: New\n\n- x\n")
    assert RuleRolloutBot.resolve_rule("CR-NEW-RULE-001", good)["section"].startswith("## CR-NEW-RULE-001")


# --------------------------------------------------------------- workflows


def test_status_classifies_and_dedupes(workspace):
    root, _ = workspace
    bot = RuleRolloutBot(runner=FakeGh(pending={"Org/gamma": "https://github.com/Org/gamma/pull/5"}))
    res = bot.status(RULE, root)
    repos = _by_repo(res)
    assert set(repos) == {"alpha", "beta", "gamma", "delta", "zeta"}  # alpha-clone shares alpha's remote
    assert repos["alpha"]["status"] == "missing"
    assert repos["beta"]["status"] == "compliant"
    assert repos["gamma"]["status"] == "pending-pr"
    assert repos["gamma"]["pr"].endswith("/pull/5")
    assert repos["delta"]["status"] == "no-agents-md"
    assert repos["zeta"]["status"] == "missing"


def test_preview_writes_nothing(workspace, tmp_path: Path):
    root, _ = workspace
    res = RuleRolloutBot(runner=FakeGh()).ensure_all(RULE, root=root, work_dir=tmp_path / "wt")
    assert res["mode"] == "preview"
    assert res["success"]
    assert not (tmp_path / "wt").exists()
    assert RULE not in (root / "alpha" / "AGENTS.md").read_text()
    # without --work-dir, preview must not create a temp directory either
    assert RuleRolloutBot(runner=FakeGh()).ensure_all(RULE, root=root)["work_dir"] is None


def test_apply_commits_in_worktree_and_leaves_checkout_untouched(workspace, tmp_path: Path):
    root, _ = workspace
    (root / "alpha" / "dirty.txt").write_text("local work\n")
    res = RuleRolloutBot(runner=FakeGh()).ensure_all(
        RULE, root=root, apply=True, work_dir=tmp_path / "wt", keep_worktrees=True
    )
    assert res["success"], res
    alpha = _by_repo(res)["alpha"]
    assert alpha["status"] == "prepared"
    assert (alpha["old_version"], alpha["new_version"]) == ("1.2.3", "1.2.4")
    wt = Path(alpha["worktree"])
    agents = (wt / "AGENTS.md").read_text()
    assert agents.index(RULE) < agents.index("## CR-OTHER-RULE-001")
    assert 'version = "1.2.4"' in (wt / "pyproject.toml").read_text()
    changelog = (wt / "CHANGELOG.md").read_text()
    assert changelog.index("[Unreleased]") < changelog.index("[1.2.4]") < changelog.index("[1.2.3]")
    assert _git(wt, "status", "--porcelain") == ""
    # primary checkout unchanged
    assert (root / "alpha" / "dirty.txt").exists()
    assert RULE not in (root / "alpha" / "AGENTS.md").read_text()
    zeta = _by_repo(res)["zeta"]
    assert zeta["new_version"] == "0.1.0"
    assert '"version": "0.1.0"' in (Path(zeta["worktree"]) / "package.json").read_text()


def test_publish_opens_issue_pushes_branch_and_pr(workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root, remotes = workspace
    created = []

    def fake_issue_run(args, cwd=None):
        created.append(args)
        return 0, f"https://github.com/{args[args.index('--repo') + 1]}/issues/7", ""

    monkeypatch.setattr("hath0r_cli.bots.issue_manager.run_cmd", fake_issue_run)
    gh = FakeGh()
    res = RuleRolloutBot(runner=gh).ensure_all(RULE, root=root, publish=True, work_dir=tmp_path / "wt")
    assert res["success"], res
    alpha = _by_repo(res)["alpha"]
    assert alpha["status"] == "published"
    assert alpha["branch"] == "chore/7-cli-entry-rule"
    assert alpha["pr"] == "https://github.com/Org/alpha/pull/99"
    assert "worktree" not in alpha  # cleaned up
    pushed = _git(remotes / "alpha.git", "show", "chore/7-cli-entry-rule:VERSION")
    assert pushed == "1.2.4"
    pr_call = next(c for c in gh.calls if c[:3] == ["gh", "pr", "create"])
    body = pr_call[pr_call.index("--body") + 1]
    assert "Closes #7" in body
    assert "Version Impact: patch" in body
    assert pr_call[pr_call.index("--base") + 1] == "development"
    assert sorted(c[c.index("--repo") + 1] for c in created) == ["Org/alpha", "Org/gamma", "Org/zeta"]


def test_commit_hook_failure_is_reported_not_bypassed(workspace, tmp_path: Path):
    root, _ = workspace
    hook = root / "alpha" / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho blocked by hook\nexit 1\n")
    hook.chmod(0o755)
    res = RuleRolloutBot(runner=FakeGh()).ensure_all(RULE, root=root, apply=True, work_dir=tmp_path / "wt")
    alpha = _by_repo(res)["alpha"]
    assert alpha["status"] == "error"
    assert "blocked by hook" in alpha["error"]
    assert not res["success"]


# --------------------------------------------------------------------- CLI


def test_cli_list_and_invalid_rule():
    from hath0r_cli.commands.rules import rules_cmd

    runner = CliRunner()
    out = runner.invoke(rules_cmd, ["list"], obj={"output": "text"})
    assert out.exit_code == 0
    assert RULE in out.output
    bad = runner.invoke(rules_cmd, ["ensure-all", "--rule", "CR-UNKNOWN-RULE-001", "--root", "/nonexistent"], obj={})
    assert bad.exit_code == 1


@pytest.mark.parametrize("output", ["text", "json"])
def test_cli_status_and_apply_render(workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str):
    from hath0r_cli.commands import rules as rules_mod

    root, _ = workspace
    monkeypatch.setattr(rules_mod, "RuleRolloutBot", lambda cwd=None: RuleRolloutBot(runner=FakeGh()))
    runner = CliRunner()
    obj = {"output": output}
    status = runner.invoke(rules_mod.rules_cmd, ["status", "--rule", RULE, "--root", str(root)], obj=obj)
    assert status.exit_code == 0, status.output
    assert "alpha" in status.output
    applied = runner.invoke(
        rules_mod.rules_cmd,
        ["ensure-all", "--rule", RULE, "--root", str(root), "--apply", "--work-dir", str(tmp_path / "wt")],
        obj=obj,
    )
    assert applied.exit_code == 0, applied.output
    assert "1.2.4" in applied.output
