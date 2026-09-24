"""Tests for PR & Branch Lifecycle bots and Factory commands."""

from __future__ import annotations

import json
from click.testing import CliRunner

from hath0r_cli import cli
from hath0r_cli.bots import BranchBot, DocumentationBot, GitJanitorBot, PRBot


def test_branch_bot_validate_name() -> None:
    bot = BranchBot()
    # Canonical
    assert bot.validate_name("development")["is_canonical"] is True
    assert bot.validate_name("master")["is_canonical"] is True

    # Valid work branch
    res = bot.validate_name("feature/78-pr-lifecycle-factory")
    assert res["valid"] is True
    assert res["is_work_branch"] is True
    assert res["issue_number"] == 78

    # Release branch
    res_rel = bot.validate_name("release/1.0.0")
    assert res_rel["valid"] is True
    assert res_rel["is_release"] is True

    # Invalid branch
    res_inv = bot.validate_name("random-branch-without-issue")
    assert res_inv["valid"] is False


def test_cli_branch_validate() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["branch", "validate", "feature/78-my-feature"])
    assert res.exit_code == 0
    assert "valid work branch" in res.stdout

    res_fail = runner.invoke(cli.main, ["branch", "validate", "invalid-branch"])
    assert "violates naming conventions" in res_fail.stdout


def test_cli_factory_list() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "factory", "list"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    factories = data["data"]["factories"]
    assert any(f["id"] == "pr-and-branch-lifecycle-factory" for f in factories)


def test_documentation_bot_summary() -> None:
    bot = DocumentationBot()
    summary = bot.generate_pr_summary({
        "number": 54,
        "title": "chore: sync",
        "headRefName": "chore/53-governance-sync",
        "baseRefName": "development",
        "author": {"login": "somesayray"},
        "body": "Test summary",
    })
    assert "# PR #54: chore: sync" in summary
    assert "@somesayray" in summary
