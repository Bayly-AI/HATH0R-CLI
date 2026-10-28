"""Unit tests for TaskEvaluatorBot and CR-TASK-EVAL-001 CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots import TaskAnnouncerBot
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot
from hath0r_cli.cli import main as cli
from hath0r_cli.step_runner import BotRegistry


def _seed_compliant_workspace(tmp_path: Path) -> None:
    """Create a compliant temporary workspace with VERSION, CHANGELOG, and compounded memory."""
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0] - 2026-10-28\n- Init\n", encoding="utf-8")
    mbot = MemoryManagerBot(cwd=tmp_path)
    mbot.initialize_memory(dry_run=False)
    mbot.session_read(note="Reading session before compounding", dry_run=False)
    mbot.compound_memory(
        node_id="episode:test-task",
        node_type="episode",
        label="Test Task Execution",
        content="Implemented automatic task evaluation tests.",
        tags=["test", "evals"],
        sync_agentgraph=False,
        dry_run=False,
    )


def test_task_evaluator_bot_evaluate_and_verify(tmp_path: Path) -> None:
    """Verify 4-tier evaluation runs, persists .hath0r/evals/latest.json, compounds eval node, and passes verify."""
    _seed_compliant_workspace(tmp_path)
    bot = TaskEvaluatorBot(cwd=tmp_path)

    res = bot.evaluate_task(
        task_id="issue-510",
        skip_tests=True,
        compound_node=True,
        sync_observability=False,
        dry_run=False,
    )
    assert res["success"] is True
    assert res["passed_gate"] is True
    assert res["r_task"] >= 0.80
    assert res["compounded_node_id"] == "eval:issue-510"
    assert (tmp_path / ".hath0r" / "evals" / "latest.json").is_file()

    status = bot.get_status()
    assert status["exists"] is True
    assert status["passed_gate"] is True
    assert status["hash_valid"] is True

    ver = bot.verify_evaluated(task_id="issue-510")
    assert ver["passed_gate"] is True
    assert ver["r_task"] >= 0.80

    # Verify TaskAnnouncerBot with enforce_eval_gate=True succeeds
    ann_bot = TaskAnnouncerBot(cwd=tmp_path)
    ann_res = ann_bot.announce_complete(task_id="issue-510", enforce_memory_gate=True, enforce_eval_gate=True)
    assert ann_res["success"] is True
    assert ann_res["eval_gate"]["passed_gate"] is True


def test_task_evaluator_bot_detects_corrupt_or_failing_scorecard(tmp_path: Path) -> None:
    """Verify verify_evaluated fails when scorecard indicates a failed gate."""
    _seed_compliant_workspace(tmp_path)
    bot = TaskEvaluatorBot(cwd=tmp_path)
    evals_dir = tmp_path / ".hath0r" / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    (evals_dir / "latest.json").write_text(
        json.dumps(
            {
                "eval_id": "eval-fail",
                "task_id": "issue-510",
                "repo_name": tmp_path.name,
                "branch": "feature/510-test",
                "passed_gate": False,
                "r_task": 0.45,
                "tier_scores": {"deterministic": 0.25},
                "blocking_reasons": ["Tier 1 deterministic gate failed: test_suite"],
            }
        ),
        encoding="utf-8",
    )

    ver = bot.verify_evaluated(task_id="issue-510", auto_run_if_missing=False)
    assert ver["passed_gate"] is False
    assert "CR-TASK-EVAL-001 violation" in (ver["error"] or "")

    ann_bot = TaskAnnouncerBot(cwd=tmp_path)
    ann_res = ann_bot.announce_complete(task_id="issue-510", enforce_memory_gate=True, enforce_eval_gate=True)
    assert ann_res["success"] is False
    assert "CR-TASK-EVAL-001" in (ann_res["error"] or "")


def test_step_runner_dispatches_task_evaluator_bot(tmp_path: Path) -> None:
    """Verify BotRegistry registers and dispatches task-evaluator-bot actions."""
    _seed_compliant_workspace(tmp_path)
    reg = BotRegistry(cwd=tmp_path)
    assert "task-evaluator-bot" in reg.registered_bot_ids()

    res_run = reg.invoke("task-evaluator-bot", "run-eval", {"task_id": "issue-510", "skip_tests": True}, dry_run=True)
    assert res_run.success is True

    res_ver = reg.invoke("task-evaluator-bot", "verify-eval", {"task_id": "issue-510"}, dry_run=True)
    assert res_ver.success is True

    res_st = reg.invoke("task-evaluator-bot", "status", {}, dry_run=True)
    assert res_st.success is True


def test_cli_evals_commands(tmp_path: Path, monkeypatch) -> None:
    """Verify hath0r evals run, status, verify, report, consensus, and redteam CLI commands in JSON and text modes."""
    _seed_compliant_workspace(tmp_path)
    (tmp_path / ".git").mkdir(exist_ok=True)
    cfg_dir = tmp_path / "cfg" / "evals"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "task-eval.json").write_text(
        json.dumps(
            {
                "version": "1.0.0",
                "rule_id": "CR-TASK-EVAL-001",
                "thresholds": {"min_r_task": 0.80},
                "observability": {"phoenix_enabled": True, "mlflow_enabled": True},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    # Status before any evaluation exists (text mode)
    r_status_empty = runner.invoke(cli, ["--output", "text", "evals", "status"])
    assert r_status_empty.exit_code == 0

    # Run evaluation in text mode with observability sync
    r_run = runner.invoke(cli, ["--output", "text", "evals", "run", "--task-id", "issue-510", "--skip-tests"])
    assert r_run.exit_code == 0
    assert "PASSED" in r_run.output

    # Status after evaluation exists (text mode)
    r_status = runner.invoke(cli, ["--output", "text", "evals", "status"])
    assert r_status.exit_code == 0
    assert "issue-510" in r_status.output

    # Verify in text mode
    r_verify = runner.invoke(cli, ["--output", "text", "evals", "verify", "--task-id", "issue-510"])
    assert r_verify.exit_code == 0
    assert "CR-TASK-EVAL-001 Verified" in r_verify.output

    # Report in text mode over parent directory
    r_report = runner.invoke(cli, ["--output", "text", "evals", "report", "--root", str(tmp_path.parent)])
    assert r_report.exit_code == 0
    assert tmp_path.name in r_report.output

    # Consensus and Redteam in text mode
    r_cons = runner.invoke(cli, ["--output", "text", "evals", "consensus", "--threshold", "0.70"])
    assert r_cons.exit_code == 0
    assert "PASSED" in r_cons.output

    r_rt = runner.invoke(cli, ["--output", "text", "evals", "redteam", "--component", "eval_engine"])
    assert r_rt.exit_code == 0
    assert "eval_engine" in r_rt.output


def test_task_evaluator_bot_observability_and_missing_auto_run(tmp_path: Path, monkeypatch) -> None:
    """Verify MLflow live sync path, corrupt scorecard handling, and auto_run_if_missing on verify_evaluated."""
    _seed_compliant_workspace(tmp_path)
    from hath0r_cli.bots.mlflow_manager_bot import mlflow_manager_bot

    monkeypatch.setattr(mlflow_manager_bot, "check_status", lambda group="hath0r": {"healthy": True})
    monkeypatch.setattr(mlflow_manager_bot, "log_run", lambda **kwargs: "mlflow-run-999")

    bot = TaskEvaluatorBot(cwd=tmp_path)
    # Verify auto_run_if_missing=False when missing fails
    ver_missing = bot.verify_evaluated(task_id="issue-510", auto_run_if_missing=False)
    assert ver_missing["passed_gate"] is False
    assert "Missing .hath0r/evals/latest.json" in (ver_missing["error"] or "")

    # Verify auto_run_if_missing=True automatically evaluates and passes
    ver_auto = bot.verify_evaluated(task_id="issue-510", auto_run_if_missing=True)
    assert ver_auto["passed_gate"] is True

    # Verify corrupt JSON handling in get_status
    latest_file = tmp_path / ".hath0r" / "evals" / "latest.json"
    latest_file.write_text("{not-valid-json", encoding="utf-8")
    st_corrupt = bot.get_status()
    assert st_corrupt["success"] is False
    assert "Corrupt evaluation scorecard" in (st_corrupt["error"] or "")
