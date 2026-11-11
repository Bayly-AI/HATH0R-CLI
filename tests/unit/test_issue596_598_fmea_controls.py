"""FMEA controls for #596 (verification), #597 (premature termination) and #598 (clarification)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from hath0r_cli.bots import PRBot
from hath0r_cli.bots.andon_bot import AndonBot
from hath0r_cli.bots.decision_radar_bot import DecisionRadarBot
from hath0r_cli.bots.fmea_bot import FMEABot
from hath0r_cli.qa import clarity, gates
from hath0r_cli.step_runner import BotRegistry, StepExecutionResult, execute_workflow

REPO = Path(__file__).resolve().parents[2]


def _latest(root: Path, passed: bool) -> None:
    evals = root / ".hath0r" / "evals"
    evals.mkdir(parents=True, exist_ok=True)
    card = {"eval_id": "e1", "task_id": "t1", "passed_gate": passed, "r_task": 0.9 if passed else 0.5, "blocking_reasons": [] if passed else ["Tier 1 failed"], "tiers": {}}
    (evals / "latest.json").write_text(json.dumps(card), encoding="utf-8")


class _Registry(BotRegistry):
    """Registry whose invoke records calls instead of running real bots."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd
        self.calls: list[str] = []

    def invoke(self, bot_id, action, args=None, *, repo=None, dry_run=False, context=None):  # type: ignore[override]
        self.calls.append(action)
        return StepExecutionResult(bot_id=bot_id, action=action, success=True, dry_run=dry_run)


_WF = {"id": "wf", "steps": [{"id": "build", "bot": "x", "action": "build"}, {"id": "merge-pr", "bot": "pr-bot", "action": "merge-pr", "gate": "verified"}]}


# ----------------------------------------------------------------------------- gate (#596/#597)
def test_gate_blocks_merge_without_passing_eval(tmp_path):
    reg = _Registry(tmp_path)
    res = execute_workflow(_WF, reg)
    assert not res.success and res.aborted
    assert reg.calls == ["build"]
    assert "gate 'merge-pr' blocked" in (res.steps[-1].error or "")
    event = json.loads((tmp_path / gates.GATE_LEDGER).read_text(encoding="utf-8").splitlines()[-1])
    assert event == {**event, "step_id": "merge-pr", "verified": False, "ran": False, "escape": False}


def test_gate_lets_verified_merge_run(tmp_path):
    _latest(tmp_path, passed=True)
    reg = _Registry(tmp_path)
    res = execute_workflow(_WF, reg)
    assert res.success and reg.calls == ["build", "merge-pr"]
    event = json.loads((tmp_path / gates.GATE_LEDGER).read_text(encoding="utf-8").splitlines()[-1])
    assert event["verified"] and event["ran"] and not event["escape"]


def test_gate_blocks_on_andon_stop(tmp_path):
    _latest(tmp_path, passed=True)
    AndonBot(cwd=tmp_path).raise_event(source="spc-monitor-bot", reason="out of control", severity="stop")
    assert "andon stop active" in (gates.check_verified(tmp_path) or "")


def test_gate_is_skipped_in_dry_run(tmp_path):
    reg = _Registry(tmp_path)
    res = execute_workflow(_WF, reg, dry_run=True)
    assert res.success and reg.calls == ["build", "merge-pr"]
    assert not (tmp_path / gates.GATE_LEDGER).exists()


def test_escape_rate_needs_enough_samples(tmp_path):
    for _ in range(gates.MIN_GATE_SAMPLES - 1):
        gates.record(tmp_path, workflow_id="wf", step_id="merge-pr", verified=True, ran=True)
    assert gates.escape_rate(tmp_path) is None
    gates.record(tmp_path, workflow_id="wf", step_id="merge-pr", verified=False, ran=True)
    assert gates.escape_rate(tmp_path) == 1 / gates.MIN_GATE_SAMPLES


def test_dependabot_without_checks_is_not_merged(monkeypatch, tmp_path):
    bot = PRBot(cwd=tmp_path)
    monkeypatch.setattr(bot, "check_pr_status", lambda *a, **k: {"author": {"login": "app/dependabot"}, "statusCheckRollup": []})
    res = bot.process_dependabot(7, auto_merge=True)
    assert res["action"] == "blocked" and "No CI checks" in res["reason"]


def test_factories_gate_merge_and_announce():
    eot = yaml.safe_load((REPO / "cfg/factories/end-of-task-factory.yaml").read_text(encoding="utf-8"))
    steps = {s.get("id"): s for s in eot["workflows"][0]["steps"]}
    assert steps["merge-pr"]["gate"] == "verified" and steps["announce-complete"]["gate"] == "verified"
    assert steps["verify-before-pr"]["args"]["skip_tests"] is False and steps["verify-before-pr"]["andon"] == "stop"
    order = [s.get("id") for s in eot["workflows"][0]["steps"]]
    assert order.index("verify-before-pr") < order.index("merge-pr")
    pl = yaml.safe_load((REPO / "cfg/factories/pr-lifecycle-factory.yaml").read_text(encoding="utf-8"))
    doc = next(w for w in pl["workflows"] if w["id"] == "document-merged-prs")
    assert doc["steps"][0]["gate"] == "verified"


# ------------------------------------------------------------------------ clarification (#598)
def test_acceptance_criteria_detection():
    assert clarity.has_acceptance_criteria("## Summary\nx\n\n## Acceptance Criteria\n- [ ] it works\n")
    assert clarity.has_acceptance_criteria("**Acceptance criteria**\n1. ships\n")
    assert not clarity.has_acceptance_criteria("## Acceptance Criteria\n\n## Notes\n- not criteria\n")
    assert not clarity.has_acceptance_criteria("Please fix the thing.")
    assert not clarity.has_acceptance_criteria(None)


def test_clarify_issue_raises_a_decision_and_blocks(tmp_path):
    bot = DecisionRadarBot(cwd=tmp_path)
    res = bot.clarify_issue(issue_number=12, title="Do a thing", body="Please do a thing.")
    assert not res["success"] and res["decision_id"]
    open_items = bot.list_decisions()
    assert any(d.get("decision_id") == res["decision_id"] for d in open_items.get("items", open_items.get("decisions", [])))
    event = json.loads((tmp_path / clarity.CLARITY_LEDGER).read_text(encoding="utf-8").splitlines()[-1])
    assert event["asked"] and not event["unasked"]


def test_clarify_issue_passes_with_criteria(tmp_path):
    res = DecisionRadarBot(cwd=tmp_path).clarify_issue(issue_number=3, body="## Acceptance Criteria\n- [ ] done\n")
    assert res["success"] and res["decision_id"] is None


def test_clarify_issue_non_blocking(tmp_path):
    res = DecisionRadarBot(cwd=tmp_path).clarify_issue(issue_number=4, body="", block=False)
    assert res["success"] and res["decision_id"]


def test_start_of_task_runs_clarify_step():
    sot = yaml.safe_load((REPO / "cfg/factories/start-of-task-factory.yaml").read_text(encoding="utf-8"))
    actions = [s["action"] for s in sot["workflows"][0]["steps"]]
    assert actions.index("verify-issue") < actions.index("clarify-issue") < actions.index("ensure-work-branch")


# ------------------------------------------------------------------------------- FMEA signals
def _sheet(root: Path) -> FMEABot:
    (root / "cfg" / "factories").mkdir(parents=True)
    (root / "cfg" / "factories" / "demo-factory.yaml").write_text(
        yaml.safe_dump({"workflows": [{"id": "w", "steps": [{"id": "run-eval", "bot": "task-evaluator-bot", "action": "run-eval"}, {"id": "announce", "bot": "task-announcer-bot", "action": "announce"}]}]}),
        encoding="utf-8",
    )
    bot = FMEABot(cwd=root)
    bot.init("demo")
    return bot


def test_seeded_signals_measure_escapes(tmp_path):
    bot = _sheet(tmp_path)
    rows = {r["taxonomy"]: r for r in bot.load("demo")["rows"]}
    assert rows["FM-3.1"]["occurrence_signal"] == "gate:escape"
    assert rows["FM-3.2"]["occurrence_signal"] == "gate:escape"
    assert rows["FM-2.2"]["occurrence_signal"] == "clarity:unasked"


def test_manual_occurrence_holds_until_signal_has_samples(tmp_path):
    bot = _sheet(tmp_path)
    row = next(r for r in bot.load("demo")["rows"] if r["taxonomy"] == "FM-3.2")
    upd = bot.update("demo", row["id"], occurrence=3, action="gate: verified on merge")["row"]
    assert upd["occurrence_source"] == "manual" and upd["action_priority"] != "H"
    scored = next(r for r in bot.score("demo")["rows"] if r["id"] == row["id"])
    assert scored["occurrence"] == 3 and scored["action_priority"] != "H"
    for _ in range(gates.MIN_GATE_SAMPLES):
        gates.record(tmp_path, workflow_id="w", step_id="announce", verified=True, ran=True)
    scored = next(r for r in bot.score("demo")["rows"] if r["id"] == row["id"])
    assert scored["occurrence"] == 1 and scored["occurrence_source"] == "data:gate:escape"


def test_clarity_signal_feeds_occurrence(tmp_path):
    bot = _sheet(tmp_path)
    for i in range(clarity.MIN_CLARITY_SAMPLES):
        clarity.record(tmp_path, issue_number=i, has_criteria=i % 2 == 0, asked=i % 4 != 1)
    row = next(r for r in bot.score("demo")["rows"] if r["taxonomy"] == "FM-2.2")
    assert row["occurrence_source"] == "data:clarity:unasked" and row["observed_rate"] == 0.25
