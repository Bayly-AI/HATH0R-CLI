"""Unit tests for Issue #551: 100% BotRegistry service-bot coverage, 4-hour pre-task auto-calibration, SuperSqueeze wiring, and hath0r-net OTel alignment."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from hath0r_cli.bots.cag_engine import CAGEngine
from hath0r_cli.bots.ci_cccd_bot import CalibrationBot, CCCDCalibrationLoop, CICCCDManagingBot
from hath0r_cli.bots.hahp_protocol import HAHPProtocolManager
from hath0r_cli.bots.supercompress_bot import SuperCompressBot, SuperSqueezeBot
from hath0r_cli.factories.step_runner import SERVICE_BOT_MAP, BotRegistry
from hath0r_cli.lazy_group import COMMAND_REGISTRY


def test_bot_registry_registers_all_69_plus_bots_and_maps_every_cli_service(tmp_path: Path) -> None:
    """CR-FEATURE-WORKFLOW-STANDARD-001: Every Feature/CLI command is a Service run by >= 1 registered Bot."""
    registry = BotRegistry(cwd=tmp_path)
    bot_ids = set(registry.registered_bot_ids())
    assert len(bot_ids) >= 69, f"Expected >= 69 registered bots, got {len(bot_ids)}"

    for cmd_name in COMMAND_REGISTRY:
        assert cmd_name in SERVICE_BOT_MAP, f"CLI command '{cmd_name}' missing from SERVICE_BOT_MAP"
        meta = SERVICE_BOT_MAP[cmd_name]
        owning_bots = meta.get("owning_bots", [])
        assert len(owning_bots) >= 1, f"CLI command '{cmd_name}' has zero owning bots"
        for b_id in owning_bots:
            assert b_id in bot_ids, f"Owning bot '{b_id}' for '{cmd_name}' is not registered in BotRegistry"


def test_4_hour_pre_task_auto_calibration_gate(tmp_path: Path) -> None:
    """Verify CCCDCalibrationLoop and CICCCDManagingBot enforce 4.0h max_age_hours and auto-calibrate when expired."""
    state_file = tmp_path / ".hath0r" / "cccd_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)

    # Write a 5.2-hour-old calibration state (> 4.0h limit, though < old 24h limit)
    stale_dt = datetime.now(timezone.utc) - timedelta(hours=5.2)
    state_file.write_text(
        json.dumps(
            {
                "active_calibration": True,
                "last_run_timestamp": stale_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_calibration_runs": 10,
                "current_parameters": {
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                    "retry_count": 3,
                    "guardrail_threshold": 0.85,
                },
                "drift_metrics": {"accuracy_drift": 0.01, "latency_drift_ms": 10.0, "token_tax_drift": 0.0},
                "history": [],
            }
        ),
        encoding="utf-8",
    )

    loop = CCCDCalibrationLoop(cwd=tmp_path, state_file=state_file)
    check = loop.check_calibration_freshness()
    assert check["max_age_hours"] == 4.0
    assert check["is_fresh"] is False
    assert check["stale"] is True

    bot = CICCCDManagingBot(root_dir=str(tmp_path))
    assert CalibrationBot is CICCCDManagingBot
    ensured = bot.ensure_calibrated(max_age_hours=4.0, trigger_source="test_issue_551")
    assert ensured["is_fresh"] is True
    assert ensured["auto_calibrated"] is True
    assert ensured["calibration_id"] == 11

    # Immediate second check is fresh and does not re-run calibration
    ensured_again = bot.ensure_calibrated(max_age_hours=4.0, trigger_source="test_issue_551")
    assert ensured_again["is_fresh"] is True
    assert ensured_again["auto_calibrated"] is False


def test_supersqueeze_wired_across_cag_hahp_and_bot_registry(tmp_path: Path) -> None:
    """Verify SuperSqueezeBot (SuperCompressBot) compresses CAG envelopes, HAHP handoffs, and BotRegistry steps."""
    assert SuperSqueezeBot is SuperCompressBot

    # 1. BotRegistry dispatch for supersqueeze-bot
    registry = BotRegistry(cwd=tmp_path)
    long_lines = "\n".join(
        ["# Canonical Architecture Specification"]
        + [f"Filler diagnostic line {i} about routine cluster metrics." for i in range(60)]
        + ["SuperSqueeze reduces token overhead across Level 1 MCP and Level 2 CLI."]
    )
    step_res = registry.invoke(
        "supersqueeze-bot",
        "squeeze",
        {"query": "SuperSqueeze Level 1 MCP", "context": long_lines, "threshold": 0.5, "force_local": True},
    )
    assert step_res.success is True
    assert step_res.data["savings_pct"] > 20.0
    assert "Canonical Architecture Specification" in step_res.data["compressed_text"]

    # 2. CAGEngine.pack_context with squeeze=True
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\n" + long_lines, encoding="utf-8")
    cag = CAGEngine()
    env = cag.pack_context(workspace_root=tmp_path, query="SuperSqueeze", squeeze=True)
    assert env["supersqueeze"]["squeezed"] is True
    assert env["supersqueeze"]["owning_bot"] == "SuperSqueezeBot"

    # 3. HAHPProtocolManager.create_envelope compresses verbose scratchpad_delta (>150 words)
    hahp = HAHPProtocolManager()
    verbose_scratchpad = " ".join([f"Paragraph {i} verbose scratchpad handoff notes for agent." for i in range(40)])
    handoff = hahp.create_envelope(
        sender_agent="planner-agent",
        recipient_agent="executor-agent",
        scratchpad_delta=verbose_scratchpad,
    )
    assert handoff.state_variables["_supersqueeze"]["squeezed"] is True
    assert handoff.state_variables["_supersqueeze"]["owning_bot"] == "SuperSqueezeBot"


def test_otel_json_aligned_with_hath0r_net() -> None:
    """Verify cfg/observability/otel.json points to Hath0r-phoenix (:38000/phoenix), Hathor-MLFLOW, and Hath0r-Cruise-Control."""
    repo_root = Path(__file__).resolve().parents[2]
    otel_data = json.loads((repo_root / "cfg" / "observability" / "otel.json").read_text(encoding="utf-8"))
    assert otel_data["exporters"]["otlp"]["default_endpoint"] == "http://localhost:38000/phoenix"
    net = otel_data["network_services"]
    assert net["phoenix"]["container"] == "Hath0r-phoenix"
    assert net["mlflow"]["container"] == "Hathor-MLFLOW"
    assert net["cruise_control"]["container"] == "Hath0r-Cruise-Control"
