"""Unit tests for Issue #553: IterationCascadeBot enforcing the 4-stage cascade (Task -> CLI/MCP -> Computer -> Web)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.iteration_cascade_bot import IterationCascadeBot
from hath0r_cli.cli import main
from hath0r_cli.step_runner import BotRegistry


def test_iteration_cascade_blocks_out_of_order_and_premature_web(tmp_path: Path) -> None:
    """Verify IterationCascadeBot blocks Stage 2/3/4 when earlier stages are skipped or confidence >= 0.70."""
    bot = IterationCascadeBot(cwd=tmp_path)
    state = bot.start_session("preflight validation check", strict_order=True)

    # Attempting Stage 2, Stage 3, or Stage 4 before Stage 1 is blocked
    s2_early = bot.run_stage2_cli_mcp(state)
    assert s2_early["success"] is False
    assert s2_early["status"] == "BLOCKED_OUT_OF_ORDER"

    s3_early = bot.run_stage3_computer(state)
    assert s3_early["success"] is False
    assert s3_early["status"] == "BLOCKED_OUT_OF_ORDER"

    s4_early = bot.run_stage4_web(state)
    assert s4_early["success"] is False
    assert s4_early["status"] == "BLOCKED_PREMATURE_WEB_ESCALATION"

    # Now execute Stage 1 (Task), Stage 2 (CLI/MCP), and Stage 3 (Computer) with high confidence (0.90)
    s1 = bot.run_stage1_task(state)
    assert s1["success"] is True
    assert s1["calibration_gate"]["max_age_hours"] == 4.0

    s2 = bot.run_stage2_cli_mcp(state, confidence=0.90)
    assert s2["success"] is True
    assert s2["agentgraph_levels_queried"] == ["L1_MCP", "L2_CLI_MEMORY"]

    s3 = bot.run_stage3_computer(state, confidence=0.90)
    assert s3["success"] is True

    # Stage 4 (Web) is STILL blocked because local confidence >= 0.70
    s4_blocked = bot.run_stage4_web(state)
    assert s4_blocked["success"] is False
    assert s4_blocked["status"] == "BLOCKED_LOCAL_KNOWLEDGE_SUFFICIENT"


def test_iteration_cascade_allows_stage4_web_only_on_verified_miss_and_compounds(tmp_path: Path) -> None:
    """Verify Stage 4 (Web) executes only when Stage 2 & Stage 3 return confidence < 0.70, and compounds to MemoryGraph."""
    bot = IterationCascadeBot(cwd=tmp_path)
    state = bot.start_session("preflight validation check", strict_order=True)

    assert bot.run_stage1_task(state)["success"] is True
    assert bot.run_stage2_cli_mcp(state, confidence=0.45)["success"] is True
    assert bot.run_stage3_computer(state, confidence=0.50)["success"] is True

    s4 = bot.run_stage4_web(
        state,
        external_finding="External RFC 9110 HTTP specification details for edge gateway",
    )
    assert s4["success"] is True
    assert s4["status"] == "STAGE4_COMPLETED_AND_COMPOUNDED"
    assert Path(s4["compounded_to_memory"]["graph_file"]).is_file()


def test_iteration_cascade_stage1_missing_workflow_offer(tmp_path: Path) -> None:
    """Verify Stage 1 halts and returns Missing-Workflow Offer when task has no matching workflow."""
    bot = IterationCascadeBot(cwd=tmp_path)
    intent = "subspace tachyon array alignment calibration"
    res = bot.execute_cascade(intent, strict_workflow_first=True)
    assert res["success"] is False
    assert res["halted_at"] == "task"
    offer = res["stage1"]["missing_workflow_offer"]
    assert offer["acceptance_test"] == intent


def test_bot_registry_and_cli_workflow_cascade(tmp_path: Path) -> None:
    """Verify IterationCascadeBot is registered in BotRegistry and accessible via `hath0r workflow cascade`."""
    registry = BotRegistry(cwd=tmp_path)
    assert isinstance(registry.get_bot("iteration-cascade-bot"), IterationCascadeBot)

    runner = CliRunner()
    res = runner.invoke(
        main,
        ["-o", "json", "workflow", "cascade", "--intent", "preflight validation check"],
    )
    assert res.exit_code == 0
    payload = json.loads(res.output)
    assert payload["state"] == "ok"
    assert payload["data"]["completed_stages"] == ["task", "cli_mcp", "computer"]
