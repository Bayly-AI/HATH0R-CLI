"""Unit tests for Issue #552: MCPCentralizationBot, MCPWorkflowEngineBot, Workflow-First Offer, and Level 1/2 AgentGraph parity."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.mcp_centralization_bot import MCPCentralizationBot
from hath0r_cli.bots.mcp_workflow_engine_bot import MCPWorkflowEngineBot
from hath0r_cli.cli import main
from hath0r_cli.step_runner import BotRegistry


def test_mcp_centralization_bot_audits_parity_and_pins_schemas(tmp_path: Path) -> None:
    """Verify MCPCentralizationBot audits Level 1/2 parity and pins pruned SHA-256 schemas."""
    bot = MCPCentralizationBot(cwd=tmp_path)
    parity = bot.audit_parity()
    assert parity["success"] is True
    assert parity["level1_mcp_tools_count"] >= 20
    assert parity["level2_cli_commands_count"] >= 70
    assert parity["unmapped_cli_commands"] == []
    assert parity["unmapped_l1_tools"] == []

    pin_res = bot.prune_and_pin_schemas()
    assert pin_res["success"] is True
    assert pin_res["tools_pinned"] >= 20
    assert pin_res["reduction_percent"] > 0.0
    pin_path = Path(pin_res["pin_file"])
    assert pin_path.is_file()
    pin_doc = json.loads(pin_path.read_text(encoding="utf-8"))
    assert "kb_search" in pin_doc["pins"]
    assert len(pin_doc["pins"]["kb_search"]["sha256"]) == 64


def test_mcp_workflow_engine_bot_missing_workflow_offer_and_scaffold(tmp_path: Path) -> None:
    """Verify unmatched intents trigger Missing-Workflow Offer with original request as acceptance test."""
    bot = MCPWorkflowEngineBot(cwd=tmp_path)
    intent = "quantum photonic telemetry synthesis for satellite uplink"
    match_res = bot.match_workflow(intent, strict_offer=True)
    assert match_res["matched"] is False
    assert match_res["offer_required"] is True
    offer = match_res["missing_workflow_offer"]
    assert offer is not None
    assert offer["acceptance_test"] == intent
    assert offer["owning_bots"] == ["mcp-workflow-engine-bot", "factory-manager-bot"]

    # Scaffold the missing workflow and verify it then matches and executes
    scaffold_res = bot.scaffold_workflow(intent, owning_bots=["mcp-workflow-engine-bot"])
    assert scaffold_res["success"] is True
    assert Path(scaffold_res["file"]).is_file()
    assert scaffold_res["acceptance_test"] == intent

    rematch = bot.match_workflow(intent, strict_offer=True)
    assert rematch["matched"] is True
    assert rematch["workflow"]["acceptance_test"] == intent

    exec_res = bot.execute_workflow_first(intent, dry_run=True)
    assert exec_res["success"] is True
    assert exec_res["status"] == "COMPLETED"
    assert exec_res["cruise_control_gate"]["status"] == "APPROVED"
    assert exec_res["phoenix_trace"]["endpoint"] == "http://localhost:38000/phoenix"


def test_bot_registry_dispatches_centralization_and_workflow_bots(tmp_path: Path) -> None:
    """Verify BotRegistry instantiates MCPCentralizationBot and MCPWorkflowEngineBot."""
    registry = BotRegistry(cwd=tmp_path)
    assert isinstance(registry.get_bot("mcp-centralization-bot"), MCPCentralizationBot)
    assert isinstance(registry.get_bot("mcp-workflow-engine-bot"), MCPWorkflowEngineBot)

    res1 = registry.invoke("mcp-centralization-bot", "audit_parity")
    assert res1.success is True
    res2 = registry.invoke(
        "mcp-workflow-engine-bot",
        "offer_missing_workflow",
        {"intent": "sync interstellar ledger"},
    )
    assert res2.success is True
    assert res2.data["acceptance_test"] == "sync interstellar ledger"


def test_workflow_and_mcp_cli_commands() -> None:
    """Verify `hath0r workflow list|offer` and `hath0r mcp parity` CLI commands succeed."""
    runner = CliRunner()
    res_list = runner.invoke(main, ["-o", "json", "workflow", "list"])
    assert res_list.exit_code == 0
    payload_list = json.loads(res_list.output)
    assert payload_list["state"] == "ok"
    assert payload_list["data"]["count"] >= 20

    res_offer = runner.invoke(
        main,
        ["-o", "json", "workflow", "offer", "--intent", "audit orbital mesh latency"],
    )
    assert res_offer.exit_code == 0
    payload_offer = json.loads(res_offer.output)
    assert payload_offer["data"]["acceptance_test"] == "audit orbital mesh latency"

    res_parity = runner.invoke(main, ["-o", "json", "mcp", "parity"])
    assert res_parity.exit_code == 0
    payload_parity = json.loads(res_parity.output)
    assert payload_parity["data"]["success"] is True
