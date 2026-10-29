"""GitWorkflowBot: promotion-path policy, release cutting, promotion PRs, sync and merge guards."""

import json
import subprocess

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot, normalize_stage, previous_stage
from hath0r_cli.cli import main

# ---------------------------------------------------------------- policy (mirrors enforce-promotion-path.yml)


@pytest.mark.parametrize(
    "head,base,allowed",
    [
        ("feature/42-add-kb-sync", "development", True),
        ("chore/7-Bump.deps_v2", "development", True),
        ("feature/add-kb", "development", False),
        ("testing", "development", False),
        ("release/1.4.0", "development", False),
        ("development", "testing", True),
        ("release/1.4.0", "testing", True),
        ("feature/42-x", "testing", False),
        ("testing", "staging", True),
        ("development", "staging", False),
        ("staging", "master", True),
        ("release/1.4.0-rc.1", "master", True),
        ("testing", "master", False),
        ("staging", "production", True),
        ("development", "nowhere", False),
    ],
)
def test_check_path_matches_ci(head, base, allowed):
    assert GitWorkflowBot().check_path(head, base)["allowed"] is allowed


def test_check_path_metadata():
    work = GitWorkflowBot().check_path("feature/42-add-kb", "development")
    assert work["issue_number"] == 42 and work["merge_strategy"] == "squash" and not work["human_gate"]
    prod = GitWorkflowBot().check_path("staging", "production")
    assert prod["base"] == "master" and prod["environment"] == "production"
    assert prod["human_gate"] and prod["merge_strategy"] == "merge"


def test_stage_helpers():
    assert normalize_stage("Prod") == "master"
    assert previous_stage("testing") == "development"
    assert previous_stage("production") == "staging"
    assert previous_stage("development") is None


# ---------------------------------------------------------------- real git fixtures


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _commit(cwd, name, content, msg):
    (cwd / name).write_text(content)
    _git(cwd, "add", name)
    _git(cwd, "commit", "-q", "-m", msg)


@pytest.fixture
def repo(tmp_path):
    """Working clone with a bare origin holding all canonical branches at one commit."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    work.mkdir()
    _git(work, "init", "-q", "-b", "development")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _commit(work, "VERSION", "1.0.0\n", "init")
    _git(work, "remote", "add", "origin", str(origin))
    for b in ("development", "testing", "staging", "master"):
        _git(work, "push", "-q", "origin", f"development:refs/heads/{b}")
    _git(work, "fetch", "-q", "origin")
    return work


@pytest.fixture
def bot(repo, monkeypatch):
    b = GitWorkflowBot(cwd=repo)
    calls = []

    def fake_gh(*args):
        calls.append(args)
        if args[:2] == ("pr", "list"):
            return 0, "[]", ""
        if args[:2] == ("pr", "create"):
            return 0, "https://github.com/o/r/pull/77", ""
        return 0, "", ""

    monkeypatch.setattr(b, "_gh", fake_gh)
    b.gh_calls = calls
    return b


def test_status_counts_pending_commits(repo, bot):
    _commit(repo, "a.txt", "a", "feat a")
    _git(repo, "push", "-q", "origin", "development")
    st = bot.status()
    first = st["stages"][0]
    assert st["success"] and first["from"] == "development" and first["pending_commits"] == 1
    assert st["stages"][1]["pending_commits"] == 0
    assert st["current_branch_kind"] == "canonical"


def test_promote_noop_when_nothing_pending(bot):
    res = bot.promote("testing")
    assert res["success"] and res["noop"]
    assert not any(c[:2] == ("pr", "create") for c in bot.gh_calls)


def test_promote_opens_pr_with_release_body(repo, bot):
    _commit(repo, "a.txt", "a", "feat a")
    _git(repo, "push", "-q", "origin", "development")
    res = bot.promote("testing")
    assert res["success"] and res["pr_number"] == 77 and res["pending_commits"] == 1
    create = next(c for c in bot.gh_calls if c[:2] == ("pr", "create"))
    body = create[create.index("--body") + 1]
    assert "feat a" in body and "merge commit" in body


def test_promote_rejects_skipping_a_stage(bot):
    res = bot.promote("staging", source="development")
    assert not res["success"] and "testing" in res["error"]


def test_cut_release_pushes_branch_without_checkout(repo, bot):
    res = bot.cut_release("v1.0.0")
    assert res["success"] and res["branch"] == "release/1.0.0" and res["warning"] is None
    assert bot.current_branch() == "development"
    out = subprocess.run(["git", "ls-remote", "--heads", "origin", "release/1.0.0"], cwd=repo, capture_output=True, text=True)
    assert "release/1.0.0" in out.stdout
    again = bot.cut_release("1.0.0")
    assert not again["success"] and "already exists" in again["error"]


def test_cut_release_warns_on_version_mismatch(bot):
    res = bot.cut_release("2.0.0")
    assert res["success"] and "1.0.0" in res["warning"]


def test_sync_merges_base_and_aborts_on_conflict(repo, bot):
    _git(repo, "checkout", "-q", "-b", "feature/1-x")
    _commit(repo, "f.txt", "mine", "work")
    _git(repo, "checkout", "-q", "development")
    _commit(repo, "g.txt", "theirs", "upstream")
    _git(repo, "push", "-q", "origin", "development")
    _git(repo, "checkout", "-q", "feature/1-x")
    assert bot.sync_branch()["success"]
    assert (repo / "g.txt").exists()

    _commit(repo, "g.txt", "mine-again", "conflicting")
    _git(repo, "checkout", "-q", "development")
    _commit(repo, "g.txt", "theirs-again", "upstream2")
    _git(repo, "push", "-q", "origin", "development")
    _git(repo, "checkout", "-q", "feature/1-x")
    res = bot.sync_branch()
    assert not res["success"] and res["conflicts"] == ["g.txt"]
    assert (repo / "g.txt").read_text() == "mine-again"  # merge aborted, tree restored


def test_sync_refuses_canonical(bot):
    assert not bot.sync_branch()["success"]


# ---------------------------------------------------------------- merge guard


def _merge_bot(monkeypatch, base, head):
    b = GitWorkflowBot()
    calls = []

    def fake_gh(*args):
        calls.append(args)
        if args[:2] == ("pr", "view"):
            return 0, json.dumps({"baseRefName": base, "headRefName": head, "state": "OPEN", "url": "u"}), ""
        return 0, "merged", ""

    monkeypatch.setattr(b, "_gh", fake_gh)
    return b, calls


def test_merge_work_pr_squashes_and_deletes_branch(monkeypatch):
    b, calls = _merge_bot(monkeypatch, "development", "feature/3-y")
    res = b.merge(3)
    assert res["success"] and res["strategy"] == "squash"
    assert ("pr", "merge", "3", "--squash", "--delete-branch") == calls[-1]


def test_merge_promotion_requires_human_and_uses_merge_commit(monkeypatch):
    b, calls = _merge_bot(monkeypatch, "master", "staging")
    blocked = b.merge(9)
    assert not blocked["success"] and "human-gated" in blocked["error"]
    ok = b.merge(9, human_approved=True)
    assert ok["success"] and calls[-1] == ("pr", "merge", "9", "--merge")


# ---------------------------------------------------------------- CLI surface


def test_cli_pr_check_json_and_exit_code():
    runner = CliRunner()
    ok = runner.invoke(main, ["-o", "json", "--quiet", "pr", "check", "--head", "feature/5-z", "--base", "development"])
    assert ok.exit_code == 0 and json.loads(ok.output)["data"]["allowed"] is True
    bad = runner.invoke(main, ["-o", "json", "--quiet", "pr", "check", "--head", "feature/5-z", "--base", "master"])
    assert bad.exit_code == 1 and json.loads(bad.output)["state"] == "error"


def test_cli_promote_release_rejects_bad_version():
    res = CliRunner().invoke(main, ["-o", "json", "--quiet", "promote", "release", "banana", "--dry-run"])
    assert res.exit_code == 1 and "SemVer" in json.loads(res.output)["data"]["error"]


def test_cli_branch_start_dry_run():
    res = CliRunner().invoke(
        main, ["-o", "json", "--quiet", "branch", "start", "feature", "12", "Add Thing", "--no-issue-check", "--dry-run"]
    )
    assert res.exit_code == 0 and json.loads(res.output)["data"]["branch"] == "feature/12-add-thing"
