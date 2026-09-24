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


def test_cli_factory_validate_all() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "factory", "validate"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["total"] >= 1
    assert data["data"]["valid_count"] >= 1
    assert data["data"]["invalid_count"] == 0


def test_cli_factory_validate_specific() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "text", "factory", "validate", "pr-and-branch-lifecycle-factory"])
    assert res.exit_code == 0
    assert "VALID" in res.stdout


def test_cli_factory_validate_invalid(tmp_path) -> None:
    import yaml

    bad_factory = tmp_path / "bad-factory.yaml"
    bad_factory.write_text(
        yaml.dump({
            "factory_id": "bad-factory",
            "name": "Bad Factory",
            "version": "1.0.0",
            "bots": [
                {"id": "bot-a", "name": "Bot A", "capabilities": ["do-a"]}
            ],
            "workflows": [
                {
                    "id": "wf-1",
                    "name": "WF 1",
                    "steps": [
                        {"bot": "nonexistent-bot", "action": "do-unknown"}
                    ]
                }
            ]
        }),
        encoding="utf-8"
    )

    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "factory", "validate", str(bad_factory)])
    assert res.exit_code == 1
    data = json.loads(res.stdout)
    assert data["state"] == "error"
    assert data["data"]["invalid_count"] == 1
    assert any("references undeclared bot 'nonexistent-bot'" in d["message"] for d in data["diagnostics"])


def test_dry_run_bots_safety() -> None:
    # BranchBot
    b_bot = BranchBot()
    b_res = b_bot.create_branch("feature", 81, "dry-run-test", dry_run=True)
    assert b_res["success"] is True
    assert b_res["dry_run"] is True
    assert "[DRY-RUN]" in b_res["action"]

    # GitJanitorBot
    j_bot = GitJanitorBot()
    j_res = j_bot.prune_branch("feature/99-old", remote=True, dry_run=True)
    assert j_res["success"] is True
    assert j_res["dry_run"] is True
    assert "[DRY-RUN]" in j_res["action"]

    # PRBot merge
    p_bot = PRBot()
    m_res = p_bot.merge_pr(99, dry_run=True)
    assert m_res["success"] is True
    assert m_res["dry_run"] is True
    assert "[DRY-RUN]" in m_res["action"]


def test_cli_factory_run_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(
        cli.main,
        ["--output", "json", "factory", "run", "pr-and-branch-lifecycle-factory", "--dry-run"],
    )
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["dry_run"] is True
    assert data["meta"]["dry_run"] is True


def test_cli_janitor_prune_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "janitor", "prune", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["dry_run"] is True
    assert data["meta"]["dry_run"] is True


def test_bot_registry_dynamic_dispatch() -> None:
    from hath0r_cli.step_runner import BotRegistry

    reg = BotRegistry()
    assert "branch-bot" in reg.registered_bot_ids()
    assert "pr-bot" in reg.registered_bot_ids()
    assert "git-janitor-bot" in reg.registered_bot_ids()
    assert "documentation-bot" in reg.registered_bot_ids()

    # Valid dispatch
    branch_res = reg.invoke("branch-bot", "validate-name", {"name": "feature/80-test"})
    assert branch_res.success is True
    assert branch_res.data["valid"] is True

    # Missing bot
    missing_bot_res = reg.invoke("nonexistent-bot", "any-action")
    assert missing_bot_res.success is False
    assert "not registered" in missing_bot_res.error

    # Unknown action on registered bot
    unknown_action_res = reg.invoke("branch-bot", "fly-to-moon")
    assert unknown_action_res.success is False
    assert "Unknown action" in unknown_action_res.error


def test_execute_workflow_declarative() -> None:
    from hath0r_cli.step_runner import BotRegistry, execute_workflow

    reg = BotRegistry()
    wf_def = {
        "id": "test-doc-wf",
        "name": "Test Documentation Workflow",
        "steps": [
            {
                "bot": "documentation-bot",
                "action": "generate-summary",
                "args": {
                    "pr_data": {
                        "number": 80,
                        "title": "feat: dynamic step runner",
                        "headRefName": "feature/80-dynamic-step-runner",
                        "baseRefName": "development",
                        "author": {"login": "somesayray"},
                        "body": "Implements dynamic dispatch",
                    }
                },
            },
            {
                "bot": "documentation-bot",
                "action": "sync-wiki",
                "args": {"title": "Release Note 80"},
            },
        ],
    }

    res = execute_workflow(wf_def, reg)
    assert res.success is True
    assert len(res.steps) == 2
    assert "PR #80" in res.steps[0].data["summary"]
    assert res.steps[1].data["status"] == "ready"



