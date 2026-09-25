"""Unit tests for EndOfTaskDaemonBot and task finish daemon mode."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from click.testing import CliRunner

from hath0r_cli import cli
from hath0r_cli.bots.daemon import EndOfTaskDaemonBot


def test_daemon_bot_dry_run() -> None:
    bot = EndOfTaskDaemonBot()
    res = bot.run_daemon(pr_number=99, branch="feature/99-test-daemon", dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["pr_number"] == 99
    assert res["branch"] == "feature/99-test-daemon"
    phases = [h["phase"] for h in res["history"]]
    assert "pr_identified" in phases
    assert "poll_checks" in phases
    assert "merge_pr" in phases
    assert "reap_branch" in phases
    assert "sync_development" in phases
    assert "share_knowledge" in phases
    assert "announce" in phases


def test_daemon_bot_polling_success() -> None:
    bot = EndOfTaskDaemonBot(poll_interval=0.01, timeout=5.0, sleeper=lambda _: None)

    # Mock PR bot methods
    bot.pr_bot.check_pr_status = MagicMock(return_value={
        "state": "OPEN",
        "statusCheckRollup": [
            {"name": "CI / test-and-lint", "conclusion": "SUCCESS", "state": "SUCCESS"},
            {"name": "PR Workflow Guard", "conclusion": "SUCCESS", "state": "SUCCESS"},
            {"name": "Version Policy Guard", "conclusion": "SUCCESS", "state": "SUCCESS"},
            {"name": "Enforce Promotion Path", "conclusion": "SUCCESS", "state": "SUCCESS"},
            # Simulate Sonar token infra failure that is bypassed
            {"name": "SonarCloud Quality Gate", "conclusion": "FAILURE", "state": "FAILURE"},
        ],
    })
    bot.pr_bot.merge_pr = MagicMock(return_value={"success": True, "output": "Merged PR #101"})
    bot.janitor_bot.pull_development = MagicMock(return_value={"success": True, "output": "Already up to date."})
    bot.janitor_bot.prune_branch = MagicMock(return_value={"success": True, "branch": "feature/101-test"})
    bot.doc_bot.share_knowledge = MagicMock(return_value={"success": True, "target_kb": ".hath0r/knowledgebase"})
    bot.announcer_bot.announce_complete = MagicMock(return_value={"success": True, "message": "Done"})

    res = bot.run_daemon(pr_number=101, branch="feature/101-test", dry_run=False)
    assert res["success"] is True
    assert res["pr_number"] == 101
    bot.pr_bot.merge_pr.assert_called_once()
    bot.janitor_bot.pull_development.assert_called_once()
    bot.janitor_bot.prune_branch.assert_called_once()


def test_daemon_bot_hard_code_failure_aborts() -> None:
    bot = EndOfTaskDaemonBot(poll_interval=0.01, timeout=5.0, sleeper=lambda _: None)

    bot.pr_bot.check_pr_status = MagicMock(return_value={
        "state": "OPEN",
        "statusCheckRollup": [
            {"name": "CI / test-and-lint", "conclusion": "FAILURE", "state": "FAILURE"},
        ],
    })
    bot.pr_bot.merge_pr = MagicMock()

    res = bot.run_daemon(pr_number=102, branch="feature/102-test", dry_run=False)
    assert res["success"] is False
    assert "Hard CI failure" in str(res.get("history"))
    bot.pr_bot.merge_pr.assert_not_called()


def test_cli_task_finish_daemon_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(
        cli.main,
        ["--output", "json", "task", "finish", "--daemon", "--pr", "77", "--dry-run"],
    )
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert "daemon" in data["data"]
    assert data["data"]["daemon"]["success"] is True
    assert data["data"]["daemon"]["pr_number"] == 77
