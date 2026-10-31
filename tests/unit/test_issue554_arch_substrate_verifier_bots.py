"""Unit tests for Issue #554: ArchitecturePreservationBot, SubstrateUtilizationBot & TaskCompletionVerifierBot."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.architecture_preservation_bot import ArchitecturePreservationBot
from hath0r_cli.bots.substrate_utilization_bot import SubstrateUtilizationBot
from hath0r_cli.bots.task_completion_verifier_bot import TaskCompletionVerifierBot
from hath0r_cli.cli import main
from hath0r_cli.step_runner import BotRegistry


def test_architecture_preservation_bot_verifies_repo_and_fleet(tmp_path: Path) -> None:
    """Verify ArchitecturePreservationBot checks Service-Bot coverage, hidden roots, and CLAUDE.md sync."""
    bot = ArchitecturePreservationBot(cwd=tmp_path)
    res = bot.verify_repo(tmp_path)
    assert res["success"] is True
    assert res["unmapped_commands"] == []
    assert res["missing_workflows"] == []
    assert res["forbidden_hidden_dirs"] == []

    # Creating a forbidden hidden dir (.ai) triggers failure
    (tmp_path / ".ai").mkdir()
    res_bad = bot.verify_repo(tmp_path)
    assert res_bad["success"] is False
    assert ".ai" in res_bad["forbidden_hidden_dirs"]


def test_substrate_utilization_bot_detects_ddtrace_and_verifies_substrate(tmp_path: Path) -> None:
    """Verify SubstrateUtilizationBot scans AST for ddtrace and counts SuperSqueeze/OTel usages."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    sample = src_dir / "module.py"
    sample.write_text(
        "from hath0r_cli.telemetry import trace_span\n"
        "from hath0r_cli.bots.supercompress_bot import SuperCompressBot\n"
        "def run():\n"
        "    return SuperCompressBot()\n",
        encoding="utf-8",
    )

    bot = SubstrateUtilizationBot(cwd=tmp_path)
    res = bot.audit_substrate(src_dir)
    assert res["success"] is True
    assert res["ddtrace_imports"] == []
    assert res["otel_trace_span_files"] == 1
    assert res["supersqueeze_files"] == 1

    # Adding legacy ddtrace import triggers failure
    bad_file = src_dir / "legacy.py"
    bad_file.write_text("import ddtrace\n", encoding="utf-8")
    res_bad = bot.audit_substrate(src_dir)
    assert res_bad["success"] is False
    assert len(res_bad["ddtrace_imports"]) == 1


def test_task_completion_verifier_bot_probes(tmp_path: Path) -> None:
    """Verify TaskCompletionVerifierBot evaluates FactSettlementEngine probes and continuous R_task."""
    eval_dir = tmp_path / ".hath0r" / "evals"
    eval_dir.mkdir(parents=True)
    (eval_dir / "latest.json").write_text(
        json.dumps({"passed_gate": True, "composite_reward": 0.9412}),
        encoding="utf-8",
    )

    bot = TaskCompletionVerifierBot(cwd=tmp_path)
    res = bot.verify_completion(require_eval=True)
    assert res["success"] is True
    assert res["open_cruise_control_blockers"] == 0
    assert res["probes"]["cccd.calibration.fresh:4h"] is True
    assert res["probes"]["eval.gate.passed"] is True
    assert res["probes"]["workflow.first.verified"] is True


def test_bot_registry_and_arch_cli_commands(tmp_path: Path) -> None:
    """Verify the 3 bots are registered in BotRegistry and accessible via `hath0r arch`."""
    registry = BotRegistry(cwd=tmp_path)
    assert isinstance(registry.get_bot("architecture-preservation-bot"), ArchitecturePreservationBot)
    assert isinstance(registry.get_bot("substrate-utilization-bot"), SubstrateUtilizationBot)
    assert isinstance(registry.get_bot("task-completion-verifier-bot"), TaskCompletionVerifierBot)

    runner = CliRunner()
    res_verify = runner.invoke(main, ["-o", "json", "arch", "verify"])
    assert res_verify.exit_code == 0
    assert json.loads(res_verify.output)["data"]["success"] is True

    res_sub = runner.invoke(main, ["-o", "json", "arch", "substrate"])
    assert res_sub.exit_code == 0
    assert json.loads(res_sub.output)["data"]["success"] is True
