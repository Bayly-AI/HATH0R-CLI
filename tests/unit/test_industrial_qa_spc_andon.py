"""Phase 2 of the industrial QA plan (#580): SPC monitor (#586, #587) and Andon (#588, #589)."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.agent_dag_runner import AgentDAGRunner
from hath0r_cli.bots.andon_bot import AndonBot, AndonStop
from hath0r_cli.bots.local_quality_gate_bot import LocalQualityGateBot
from hath0r_cli.bots.spc_monitor_bot import SPCMonitorBot
from hath0r_cli.bots.token_tree_budget import TokenBudgetExceeded, TokenTreeBudgetGuard
from hath0r_cli.cli import main
from hath0r_cli.qa.spc import capability, chart, cusum, ewma, western_electric
from hath0r_cli.step_runner import SERVICE_BOT_MAP, BotRegistry, execute_workflow


# ------------------------------------------------------------------------------ SPC maths
def test_western_electric_rules():
    assert any(r["rule"] == 1 for r in western_electric([0, 0, 4], 0.0, 1.0))
    assert any(r["rule"] == 2 for r in western_electric([2.5, 0, 2.5], 0.0, 1.0))
    assert any(r["rule"] == 3 for r in western_electric([1.5, 1.5, 0, 1.5, 1.5], 0.0, 1.0))
    assert any(r["rule"] == 4 for r in western_electric([0.5] * 8, 0.0, 1.0))
    assert western_electric([0.1, -0.2, 0.3, -0.1], 0.0, 1.0) == []


def test_ewma_and_cusum_detect_small_sustained_shift():
    vals = [0.0] * 10 + [1.5] * 15  # 1.5 sigma shift: inside Shewhart limits, caught by EWMA/CUSUM
    assert ewma(vals, center=0.0, sigma=1.0)["signals"]
    assert cusum(vals, center=0.0, sigma=1.0)["signals"]
    assert not ewma([0.0] * 25, center=0.0, sigma=1.0)["signals"]


def test_chart_marks_short_baseline_provisional():
    res = chart([0.9, 0.91, 0.92, 0.9])
    assert res["status"].startswith("provisional_")


def test_capability_one_sided():
    rng = random.Random(1)
    vals = [0.95 + rng.gauss(0, 0.01) for _ in range(40)]
    res = capability(vals, lsl=0.8)
    assert res["cp"] is None
    assert res["cpk"] > 1.33 and res["ppk"] > 1.33


# ------------------------------------------------------------------------------ SPC bot
def _history(root: Path, values):
    hist = root / ".hath0r" / "evals" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    for i, v in enumerate(values):
        card = {
            "eval_id": f"eval-{i:03d}",
            "evaluated_at": f"2026-11-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00",
            "r_task": v,
            "tier_scores": {"deterministic": 1.0, "trajectory": v, "adversarial": 1.0, "goal_alignment": v},
            "duration_ms": 200.0 + i % 3,
        }
        (hist / f"eval-{i:03d}.json").write_text(json.dumps(card), encoding="utf-8")


def _thresholds(root: Path, mode: str):
    (root / "thresholds.json").write_text(json.dumps({"thresholds": {}, "capability": {"mode": mode}}), encoding="utf-8")


def _stable(n=30, seed=2):
    rng = random.Random(seed)
    return [round(0.93 + rng.gauss(0, 0.005), 4) for _ in range(n)]


def test_spc_status_warns_but_does_not_block_by_default(tmp_path):
    _history(tmp_path, _stable() + [0.70])
    res = SPCMonitorBot(cwd=tmp_path).status()
    assert res["mode"] == "warn"
    assert res["metrics"]["r_task"]["status"] == "out_of_control"
    assert res["warnings"] and res["success"] is True and res["blocking"] is False
    assert (tmp_path / ".hath0r" / "spc" / "latest.json").is_file()


def test_spc_block_mode_fails_and_pulls_andon(tmp_path):
    _history(tmp_path, _stable() + [0.70])
    _thresholds(tmp_path, "block")
    res = SPCMonitorBot(cwd=tmp_path).gate()
    assert res["blocking"] and res["success"] is False
    st = AndonBot(cwd=tmp_path).status()
    assert st["stopped"] and st["active"][0]["source"] == "spc-monitor-bot"


def test_spc_in_control_history_has_no_warnings(tmp_path):
    _history(tmp_path, _stable(40, seed=4))  # a seed with no chance false alarms (WE rules + EWMA + CUSUM)
    res = SPCMonitorBot(cwd=tmp_path).status(metrics=["r_task"])
    assert res["metrics"]["r_task"]["status"] == "in_control"
    assert res["capability"]["capable"] is True
    assert res["warnings"] == []


def test_spc_frozen_recent_baseline_is_used(tmp_path):
    _history(tmp_path, [1.0] * 20 + _stable(20))
    bot = SPCMonitorBot(cwd=tmp_path)
    first = bot.chart("r_task")
    assert first["status"] == "out_of_control"  # zero-variation early baseline flags everything after it
    b = bot.baseline("r_task", points=20, recent=True)
    assert b["success"] and b["window"] == "recent"
    after = bot.chart("r_task")
    assert after["baseline_frozen"] is True
    assert after["baseline"]["center"] == pytest.approx(b["center"])


def test_spc_low_cpk_is_a_warning(tmp_path):
    rng = random.Random(4)
    _history(tmp_path, [0.83 + rng.gauss(0, 0.02) for _ in range(30)])
    res = SPCMonitorBot(cwd=tmp_path).status(metrics=["r_task"])
    assert any("Cpk" in w for w in res["warnings"])
    assert res["success"] is True


def test_spc_reads_token_ledger(tmp_path):
    ledger = tmp_path / ".hath0r" / "finops" / "token_telemetry.jsonl"
    ledger.parent.mkdir(parents=True)
    ledger.write_text("\n".join(json.dumps({"timestamp": f"2026-11-11T00:00:{i:02d}", "total_tokens": 100 + i, "cost_usd": 0.001, "latency_ms": 5}) for i in range(5)), encoding="utf-8")
    assert [p["value"] for p in SPCMonitorBot(cwd=tmp_path).series("total_tokens")] == [100, 101, 102, 103, 104]


def test_spc_unknown_metric():
    with pytest.raises(ValueError, match="unknown metric"):
        SPCMonitorBot().series("nope")


def test_spc_cli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _history(tmp_path, _stable() + [0.70])
    runner = CliRunner()
    res = runner.invoke(main, ["-o", "json", "spc", "status"])
    assert res.exit_code == 0
    out = json.loads(res.output)
    assert any(d["code"] == "SPC_SIGNAL" and d["severity"] == "warning" for d in out["diagnostics"])
    res = runner.invoke(main, ["-o", "json", "spc", "chart", "-m", "bogus"])
    assert res.exit_code == 2
    res = runner.invoke(main, ["-o", "json", "spc", "capability"])
    assert json.loads(res.output)["data"]["lsl"] == 0.8
    _thresholds(tmp_path, "block")
    assert runner.invoke(main, ["-o", "json", "spc", "status"]).exit_code == 1


def test_quality_local_reports_capability(tmp_path):
    _history(tmp_path, _stable(30))
    cap = LocalQualityGateBot(cwd=tmp_path)._capability_check(tmp_path)
    assert cap["available"] and cap["mode"] == "warn" and cap["blocking"] is False
    payload = LocalQualityGateBot(cwd=tmp_path).build_default_thresholds_payload(tmp_path)
    assert payload["capability"]["mode"] == "warn" and payload["capability"]["min_cpk_warn"] == 1.33


# ------------------------------------------------------------------------------- Andon
def test_andon_lifecycle_requires_ack_before_clear(tmp_path):
    bot = AndonBot(cwd=tmp_path, route_to_radar=False)
    ev = bot.raise_event(source="test", reason="broken build")
    with pytest.raises(AndonStop):
        bot.check()
    with pytest.raises(ValueError, match="acknowledge it first"):
        bot.clear(ev["event_id"])
    bot.ack(ev["event_id"], by="ray")
    assert bot.status()["stopped"] is True  # acknowledged is still stopped
    bot.clear(ev["event_id"], by="ray", note="fixed")
    assert bot.status()["stopped"] is False
    with pytest.raises(ValueError, match="already cleared"):
        bot.clear(ev["event_id"])
    assert bot.verify()["valid"]


def test_andon_warn_does_not_stop_and_can_clear_without_ack(tmp_path):
    bot = AndonBot(cwd=tmp_path, route_to_radar=False)
    ev = bot.raise_event(source="test", reason="slow", severity="warn")
    assert bot.check()["active_warnings"] == 1
    bot.clear(ev["event_id"])
    assert bot.status()["active"] == []


def test_andon_ledger_tamper_detected(tmp_path):
    bot = AndonBot(cwd=tmp_path, route_to_radar=False)
    bot.raise_event(source="a", reason="one")
    bot.raise_event(source="b", reason="two")
    lines = bot.ledger_path.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["reason"] = "edited"
    lines[0] = json.dumps(rec)
    bot.ledger_path.write_text("\n".join(lines) + "\n")
    v = bot.verify()
    assert not v["valid"] and v["tampered_records"] == [0]


def test_andon_rejects_unknown_severity_and_event(tmp_path):
    bot = AndonBot(cwd=tmp_path, route_to_radar=False)
    with pytest.raises(ValueError):
        bot.raise_event(source="x", reason="y", severity="panic")
    with pytest.raises(ValueError, match="unknown"):
        bot.ack("andon-missing")


def test_andon_stop_routes_to_decision_radar(tmp_path):
    AndonBot(cwd=tmp_path).raise_event(source="test", reason="needs a person")
    active = json.loads((tmp_path / ".hath0r" / "decisions" / "active.json").read_text())
    assert "needs a person" in json.dumps(active)


def test_workflow_step_with_andon_stop_halts_later_workflows(tmp_path):
    registry = BotRegistry(cwd=tmp_path)
    wf = {"id": "wf", "steps": [{"id": "boom", "bot": "andon-bot", "action": "no-such-action", "on_failure": "continue", "andon": "stop"}]}
    first = execute_workflow(wf, registry)
    assert not first.success
    assert AndonBot(cwd=tmp_path).status()["stopped"]
    second = execute_workflow({"id": "wf2", "steps": [{"bot": "andon-bot", "action": "status"}]}, registry)
    assert second.aborted and "Andon stop active" in (second.steps[0].error or "")


def test_failure_policy_alias_is_honoured(tmp_path):
    registry = BotRegistry(cwd=tmp_path)
    wf = {"id": "wf", "steps": [
        {"bot": "andon-bot", "action": "no-such-action", "failure_policy": "continue"},
        {"bot": "andon-bot", "action": "status"},
    ]}
    res = execute_workflow(wf, registry)
    assert len(res.steps) == 2 and not res.aborted


def test_dag_runner_refuses_to_start_while_stopped(tmp_path):
    AndonBot(cwd=tmp_path, route_to_radar=False).raise_event(source="t", reason="stop")
    spec = {"name": "d", "cwd": str(tmp_path), "nodes": [{"id": "a"}]}
    assert AgentDAGRunner().execute_dag(spec)["status"] == "andon_stopped"
    assert AgentDAGRunner().execute_dag({**spec, "andon": False})["status"] == "success"


def test_budget_guard_pulls_andon(tmp_path):
    guard = TokenTreeBudgetGuard(max_tokens_budget=10, andon_cwd=tmp_path)
    with pytest.raises(TokenBudgetExceeded):
        guard.record_usage("tree", prompt_tokens=20, completion_tokens=0)
    st = AndonBot(cwd=tmp_path).status()
    assert st["stopped"] and st["active"][0]["source"] == "token-tree-budget-guard"


def test_andon_cli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["-o", "json", "andon", "status"]).exit_code == 0
    ev = json.loads(runner.invoke(main, ["-o", "json", "andon", "raise", "--reason", "manual"]).output)["data"]
    assert runner.invoke(main, ["-o", "json", "andon", "status"]).exit_code == 1
    assert runner.invoke(main, ["-o", "json", "andon", "clear", ev["event_id"]]).exit_code == 2
    assert runner.invoke(main, ["-o", "json", "andon", "ack", ev["event_id"]]).exit_code == 0
    assert runner.invoke(main, ["-o", "json", "andon", "clear", ev["event_id"]]).exit_code == 0
    assert runner.invoke(main, ["-o", "json", "andon", "verify"]).exit_code == 0


def test_services_registered():
    assert SERVICE_BOT_MAP["spc"]["owning_bots"][0] == "spc-monitor-bot"
    assert SERVICE_BOT_MAP["andon"]["owning_bots"][0] == "andon-bot"
