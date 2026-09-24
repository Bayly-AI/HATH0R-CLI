"""Tests for PR & Branch Lifecycle bots and Factory commands."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_cli_factory_info() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(
        cli.main,
        ["--output", "json", "factory", "info", "pr-and-branch-lifecycle-factory"],
    )
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["factory_id"] == "pr-and-branch-lifecycle-factory"
    assert len(data["data"]["workflows"]) >= 1

    # Text output test
    text_res = runner.invoke(
        cli.main,
        ["--output", "text", "factory", "info", "pr-and-branch-lifecycle-factory"],
    )
    assert text_res.exit_code == 0
    assert "Factory:" in text_res.stdout
    assert "Declared Workflows:" in text_res.stdout


def test_cli_factory_run_workflow_targeting() -> None:
    runner = CliRunner(mix_stderr=False)
    # Valid workflow target
    res = runner.invoke(
        cli.main,
        [
            "--output",
            "json",
            "factory",
            "run",
            "pr-and-branch-lifecycle-factory",
            "--workflow",
            "triage-dependabot",
            "--dry-run",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert len(data["data"]["workflows"]) == 1
    assert data["data"]["workflows"][0]["id"] == "triage-dependabot"

    # Invalid workflow target
    err_res = runner.invoke(
        cli.main,
        [
            "--output",
            "json",
            "factory",
            "run",
            "pr-and-branch-lifecycle-factory",
            "--workflow",
            "nonexistent-workflow",
            "--dry-run",
        ],
    )
    assert err_res.exit_code == 1
    err_data = json.loads(err_res.stdout)
    assert err_data["state"] == "error"
    assert any(d["code"] == "WORKFLOW_NOT_FOUND" for d in err_data.get("diagnostics", []))


def test_execute_workflow_failure_policies(tmp_path: Path) -> None:
    from hath0r_cli.step_runner import BotRegistry, execute_workflow

    reg = BotRegistry()

    # 1. Policy: abort (default)
    wf_abort = {
        "id": "wf-abort",
        "name": "WF Abort",
        "steps": [
            {"bot": "branch-bot", "action": "fly-to-mars", "on_failure": "abort"},
            {"bot": "branch-bot", "action": "validate-name", "args": {"name": "feature/1-ok"}},
        ],
    }
    res_abort = execute_workflow(wf_abort, reg)
    assert res_abort.success is False
    assert res_abort.aborted is True
    # Second step should NOT have run
    assert len(res_abort.steps) == 1
    assert res_abort.steps[0].aborted is True

    # 2. Policy: continue
    wf_continue = {
        "id": "wf-continue",
        "name": "WF Continue",
        "steps": [
            {"bot": "branch-bot", "action": "fly-to-mars", "on_failure": "continue"},
            {"bot": "branch-bot", "action": "validate-name", "args": {"name": "feature/1-ok"}},
        ],
    }
    res_continue = execute_workflow(wf_continue, reg)
    assert res_continue.success is False
    assert res_continue.aborted is False
    # Second step SHOULD have run
    assert len(res_continue.steps) == 2
    assert res_continue.steps[0].success is False
    assert res_continue.steps[1].success is True

    # 3. Policy: retry
    wf_retry = {
        "id": "wf-retry",
        "name": "WF Retry",
        "steps": [
            {"bot": "branch-bot", "action": "fly-to-mars", "on_failure": "retry", "retry_count": 2},
        ],
    }
    res_retry = execute_workflow(wf_retry, reg)
    assert res_retry.success is False
    assert res_retry.aborted is True
    assert res_retry.steps[0].retries == 2


def test_telemetry_spooling(tmp_path: Path) -> None:
    from hath0r_cli.step_runner import spool_telemetry_event

    spool_file = spool_telemetry_event(
        event_type="test.event",
        payload={"foo": "bar", "run_id": "run_123"},
        base_dir=tmp_path,
    )
    assert spool_file is not None
    assert spool_file.exists()
    assert ".hath0r/spool" in str(spool_file)

    lines = spool_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    event_data = json.loads(lines[0])
    assert event_data["schema"] == "hath0r.telemetry.event/1"
    assert event_data["event_type"] == "test.event"
    assert event_data["payload"]["run_id"] == "run_123"


def test_factory_scheduler_discovery_and_generation(tmp_path: Path) -> None:
    from hath0r_cli.scheduler import (
        discover_scheduled_workflows,
        generate_github_workflow_content,
        sync_factory_schedules_to_github,
    )

    scheduled = discover_scheduled_workflows()
    assert len(scheduled) >= 2
    # Ensure pr-and-branch-lifecycle-factory scheduled workflows are discovered
    triage_wf = next((s for s in scheduled if s.workflow_id == "triage-dependabot"), None)
    assert triage_wf is not None
    assert triage_wf.schedule == "0 */2 * * *"
    assert triage_wf.next_run is not None

    # Test workflow YAML generation
    gh_yaml = generate_github_workflow_content(triage_wf, repo="Bayly-AI/HATH0R-CLI")
    assert "cron: \"0 */2 * * *\"" in gh_yaml
    assert "hath0r factory run pr-and-branch-lifecycle-factory --workflow triage-dependabot" in gh_yaml

    # Test sync with dry-run
    dry_results = sync_factory_schedules_to_github(tmp_path, dry_run=True)
    assert len(dry_results) >= 2
    assert all("[DRY-RUN]" in r["action"] for r in dry_results)
    assert not (tmp_path / ".github" / "workflows").exists()

    # Test actual sync
    sync_results = sync_factory_schedules_to_github(tmp_path, dry_run=False)
    assert len(sync_results) >= 2
    expected_wf = (
        tmp_path / ".github" / "workflows" / "factory-schedule-pr-and-branch-lifecycle-factory-triage-dependabot.yml"
    )
    assert expected_wf.exists()


def test_cli_factory_schedule_commands(tmp_path: Path) -> None:
    runner = CliRunner(mix_stderr=False)

    # factory schedule list (JSON)
    res_list_json = runner.invoke(cli.main, ["--output", "json", "factory", "schedule", "list"])
    assert res_list_json.exit_code == 0
    data = json.loads(res_list_json.stdout)
    assert data["state"] == "ok"
    assert len(data["data"]["schedules"]) >= 2

    # factory schedule list (Text)
    res_list_text = runner.invoke(cli.main, ["--output", "text", "factory", "schedule", "list"])
    assert res_list_text.exit_code == 0
    assert "Factory Automation Schedules" in res_list_text.stdout

    # factory schedule sync --dry-run
    res_sync_dry = runner.invoke(
        cli.main,
        ["--output", "json", "factory", "schedule", "sync", "--target-dir", str(tmp_path), "--dry-run"],
    )
    assert res_sync_dry.exit_code == 0
    data_sync = json.loads(res_sync_dry.stdout)
    assert data_sync["state"] == "ok"
    assert data_sync["data"]["dry_run"] is True
    assert data_sync["data"]["synced_count"] >= 2


def test_docker_bot_and_workflow_validation() -> None:
    from hath0r_cli.bots import DockerBot

    bot = DockerBot()
    # Validate canonical hath0r-poc-ui.json
    wf_file = Path(__file__).resolve().parents[2] / "cfg" / "docker" / "workflows" / "hath0r-poc-ui.json"
    assert wf_file.is_file()
    wf_data = json.loads(wf_file.read_text(encoding="utf-8"))

    res = bot.validate_workflow(wf_data)
    assert res["valid"] is True
    assert res["workflow_id"] == "hath0r-poc-ui-stack"

    # Validate bad document
    bad_res = bot.validate_workflow({"apiVersion": "wrong/v1"})
    assert bad_res["valid"] is False
    assert len(bad_res["errors"]) > 0


def test_docker_bot_lifecycle_dry_run() -> None:
    from hath0r_cli.bots import DockerBot

    bot = DockerBot()
    assert bot.build_container(dry_run=True)["success"] is True
    assert bot.up(dry_run=True)["success"] is True
    assert bot.healthcheck(dry_run=True)["success"] is True
    assert bot.diagnose(dry_run=True)["success"] is True
    assert bot.down(dry_run=True)["success"] is True


def test_cli_docker_commands() -> None:
    runner = CliRunner(mix_stderr=False)
    wf_file = str(Path(__file__).resolve().parents[2] / "cfg" / "docker" / "workflows" / "hath0r-poc-ui.json")

    # validate
    res_val = runner.invoke(cli.main, ["--output", "json", "docker", "workflow", "validate", wf_file])
    assert res_val.exit_code == 0
    assert json.loads(res_val.stdout)["state"] == "ok"

    # run --dry-run
    res_run = runner.invoke(cli.main, ["--output", "json", "docker", "workflow", "run", wf_file, "--dry-run"])
    assert res_run.exit_code == 0
    data = json.loads(res_run.stdout)
    assert data["state"] == "ok"
    assert data["data"]["dry_run"] is True
    assert len(data["data"]["steps"]) == 5

    # diagnose --dry-run
    res_diag = runner.invoke(cli.main, ["--output", "json", "docker", "diagnose", "hath0r-poc-ui", "--dry-run"])
    assert res_diag.exit_code == 0
    diag_data = json.loads(res_diag.stdout)
    assert diag_data["data"]["healthy"] is True


def test_end_of_task_factory_bots_dry_run() -> None:
    from hath0r_cli.bots import DocumentationBot, GitJanitorBot, PRBot, TaskAnnouncerBot

    pr_bot = PRBot()
    janitor_bot = GitJanitorBot()
    doc_bot = DocumentationBot()
    announcer_bot = TaskAnnouncerBot()

    # PR bot create_pr & monitor_checks & merge_pr
    pr_res = pr_bot.create_pr(head="feature/123-test-task", dry_run=True)
    assert pr_res["success"] is True
    assert pr_res["dry_run"] is True

    mon_res = pr_bot.monitor_checks(123, dry_run=True)
    assert mon_res["success"] is True
    assert mon_res["dry_run"] is True

    merge_res = pr_bot.merge_pr(123, admin=True, squash=True, delete_branch=True, dry_run=True)
    assert merge_res["success"] is True
    assert merge_res["dry_run"] is True

    # Git Janitor pull_development
    pull_res = janitor_bot.pull_development(base="development", dry_run=True)
    assert pull_res["success"] is True
    assert pull_res["dry_run"] is True

    # Documentation bot share_knowledge
    share_res = doc_bot.share_knowledge(summary="Completed feature", dry_run=True)
    assert share_res["success"] is True
    assert share_res["dry_run"] is True

    # Task announcer bot announce_complete
    ann_res = announcer_bot.announce_complete(task_id="issue-123", dry_run=True)
    assert ann_res["success"] is True
    assert ann_res["dry_run"] is True


def test_cli_task_finish_dry_run() -> None:
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(cli.main, ["--output", "json", "task", "finish", "--dry-run"])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert data["state"] == "ok"
    assert data["data"]["workflow"]["id"] == "end-of-task"
    assert len(data["data"]["workflow"]["steps"]) == 8
