"""Phase 3 of the industrial QA plan (#580): FMEA (#590), root cause (#591), DMAIC (#592)."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli.bots.dmaic_project_bot import DMAICProjectBot
from hath0r_cli.bots.fmea_bot import MAST_TAXONOMY, FMEABot
from hath0r_cli.bots.root_cause_bot import RootCauseBot
from hath0r_cli.cli import main
from hath0r_cli.qa.fmea import action_priority, occurrence_from_rate, rank_key, score_row
from hath0r_cli.step_runner import SERVICE_BOT_MAP
from tests.fakebot import FakeBot

REPO = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------------------ FMEA maths
@pytest.mark.parametrize(
    "s,o,d,ap",
    [(10, 4, 1, "H"), (9, 2, 7, "H"), (9, 1, 1, "L"), (8, 6, 2, "H"), (8, 4, 3, "M"), (5, 8, 5, "H"), (5, 3, 3, "L"), (2, 8, 7, "M")],
)
def test_action_priority_table(s, o, d, ap):
    assert action_priority(s, o, d) == ap


def test_ratings_must_be_1_to_10():
    with pytest.raises(ValueError):
        score_row({"severity": 11, "occurrence": 1, "detection": 1})


def test_ranking_puts_priority_before_rpn():
    rows = [score_row({"id": "a", "severity": 5, "occurrence": 10, "detection": 10}), score_row({"id": "b", "severity": 10, "occurrence": 4, "detection": 1})]
    assert rows[0]["rpn"] > rows[1]["rpn"]
    assert [r["id"] for r in sorted(rows, key=rank_key)] == ["b", "a"]


def test_occurrence_scale():
    assert occurrence_from_rate(0.0) == 1
    assert occurrence_from_rate(0.03) == 5
    assert occurrence_from_rate(0.6) == 10


# ------------------------------------------------------------------------------- FMEA bot
def _factory(root: Path) -> None:
    (root / "cfg" / "factories").mkdir(parents=True)
    (root / "cfg" / "factories" / "demo-factory.yaml").write_text(
        yaml.safe_dump({"workflows": [{"id": "w", "steps": [{"id": "run-eval", "bot": "task-evaluator-bot", "action": "run-eval"}, {"id": "announce", "bot": "task-announcer-bot", "action": "announce"}]}]}),
        encoding="utf-8",
    )


def _cards(root: Path, passed: list) -> None:
    hist = root / ".hath0r" / "evals" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    for i, ok in enumerate(passed):
        card = {"eval_id": f"e{i}", "evaluated_at": f"2026-11-01T{i:02d}:00:00+00:00", "passed_gate": ok, "r_task": 0.9 if ok else 0.6,
                "tiers": {"deterministic": {"passed": ok}}, "blocking_reasons": [] if ok else ["Tier 1 deterministic gate failed: test_suite"]}
        (hist / f"e{i:02d}.json").write_text(json.dumps(card), encoding="utf-8")


def test_init_seeds_mast_taxonomy_mapped_to_steps(tmp_path):
    _factory(tmp_path)
    bot = FMEABot(cwd=tmp_path)
    res = bot.init("demo")
    assert res["rows"] == len(MAST_TAXONOMY) == 14
    sheet = bot.load("demo")
    steps = {r["taxonomy"]: r["step"] for r in sheet["rows"]}
    assert steps["FM-3.2"] == "run-eval"
    assert steps["FM-3.1"] == "announce"
    with pytest.raises(FileExistsError):
        bot.init("demo")
    with pytest.raises(ValueError, match="kebab-case"):
        bot.init("Bad Name")


def test_score_refreshes_occurrence_from_eval_history(tmp_path):
    _factory(tmp_path)
    _cards(tmp_path, [False] * 6 + [True] * 4)  # 60% failing
    bot = FMEABot(cwd=tmp_path)
    bot.init("demo")
    res = bot.score("demo")
    row = next(r for r in res["rows"] if r["taxonomy"] == "FM-3.2")
    assert row["occurrence"] == 10 and row["occurrence_source"] == "data:tier:deterministic"
    assert row["action_priority"] == "H"
    assert res["rows"][0]["action_priority"] == "H"  # ranked


def test_fix_lowers_the_row(tmp_path):
    _factory(tmp_path)
    _cards(tmp_path, [False] * 6 + [True] * 4)
    bot = FMEABot(cwd=tmp_path)
    bot.init("demo")
    before = next(r for r in bot.score("demo")["rows"] if r["taxonomy"] == "FM-3.2")
    _cards(tmp_path, [True] * 10)  # the fix: every gate passes now
    bot.update("demo", before["id"], detection=2, action="added seeded-defect MSA panel")
    after = next(r for r in bot.score("demo")["rows"] if r["id"] == before["id"])
    assert after["rpn"] < before["rpn"]
    assert after["actions"][0]["action"].startswith("added")


def test_sync_issues_files_only_high_rows_once(tmp_path):
    _factory(tmp_path)
    _cards(tmp_path, [False] * 6 + [True] * 4)
    bot = FMEABot(cwd=tmp_path)
    bot.init("demo")
    high = bot.score("demo")["high"]
    fake = FakeBot({"success": True, "issue_number": 900, "url": "https://github.com/x/y/issues/900"})
    res = bot.sync_issues("demo", issue_bot=fake)
    assert len(res["created"]) == high and res["success"]
    assert all(r["issue"] == 900 for r in bot.load("demo")["rows"] if r["action_priority"] == "H")
    again = bot.sync_issues("demo", issue_bot=fake)
    assert again["created"] == [] and len(again["skipped"]) == high


def test_issue_body_passes_issue_manager_validation(tmp_path):
    from hath0r_cli.bots.issue_manager import IssueManagerBot

    _factory(tmp_path)
    bot = FMEABot(cwd=tmp_path)
    bot.init("demo")
    row = bot.load("demo")["rows"][0]
    val = IssueManagerBot(cwd=tmp_path).validate_issue_data({"title": f"FMEA H: demo {row['id']} x", "body": bot._issue_body("demo", row), "state": "OPEN"})
    assert val["is_valid"], val["findings"]


def test_add_and_report(tmp_path):
    _factory(tmp_path)
    bot = FMEABot(cwd=tmp_path)
    bot.init("demo")
    row = bot.add("demo", step="announce", failure_mode="Wrong channel", effect="Nobody sees it", cause="Config", severity=4, occurrence=2, detection=9)["row"]
    assert row["id"] == "D-15" and row["rpn"] == 72
    rep = bot.report(top=3)
    assert len(rep["top"]) == 3 and "demo" in rep["processes"]


def test_repo_first_studies_exist():
    bot = FMEABot(cwd=REPO)
    for process in ("end-of-task", "pr-lifecycle"):
        sheet = bot.load(process)
        assert len(sheet["rows"]) >= 14
        assert all(r["issue"] for r in sheet["rows"] if r["action_priority"] == "H"), f"{process}: H row without issue"


# -------------------------------------------------------------------------------- RCA bot
def test_classify_and_tag(tmp_path):
    bot = RootCauseBot(cwd=tmp_path)
    assert bot.classify("CHANGELOG not aligned with VERSION") == "method"
    assert bot.classify("docker network timeout") == "machine"
    assert bot.classify("something odd") == "unclassified"
    with pytest.raises(ValueError, match="unknown cause category"):
        bot.tag(source="ci", ref="1", summary="x", category="weather")


def test_pareto_from_failed_gates(tmp_path):
    _cards(tmp_path, [False] * 3 + [True] * 2)
    bot = RootCauseBot(cwd=tmp_path)
    bot.tag(source="ci", ref="run-1", summary="network timeout in CI")
    res = bot.pareto(since_days=None, by="category")
    assert res["total"] == 4
    assert res["table"][0]["count"] == 3  # the three failed evals (test_suite -> unclassified)
    assert res["table"][-1]["cumulative_pct"] == 100.0
    assert res["vital_few"][0] == res["top"]
    assert bot.pareto(since_days=None)["total"] == 4  # auto-tagging is idempotent
    by_gate = bot.pareto(since_days=None, by="gate")
    assert by_gate["top"] == "tier1:deterministic"


def test_five_whys_and_fishbone(tmp_path):
    bot = RootCauseBot(cwd=tmp_path)
    with pytest.raises(ValueError, match="3 to 5"):
        bot.why(7, "gate passed a defect", ["a", "b"], compound=False)
    rec = bot.why(7, "gate passed a defect", ["version check was a score", "partial credit", "no hard gate for version drift"], category="measurement", compound=False)
    assert rec["whys"]["root_cause"] == "no hard gate for version drift"
    assert "no hard gate for version drift" in rec["fishbone"]["measurement"]
    fb = bot.fishbone(7, cause="flaky docker network", category="machine")
    assert fb["fishbone"]["machine"] == ["flaky docker network"]
    assert json.loads((tmp_path / ".hath0r" / "rca" / "7.json").read_text())["whys"]


# ------------------------------------------------------------------------------ DMAIC bot
def _ctq_history(root: Path, values) -> None:
    hist = root / ".hath0r" / "evals" / "history"
    hist.mkdir(parents=True, exist_ok=True)
    start = len(list(hist.glob("*.json")))
    for i, v in enumerate(values, start=start):
        card = {"eval_id": f"c{i:03d}", "evaluated_at": f"2026-11-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00", "passed_gate": True, "r_task": v}
        (hist / f"c{i:03d}.json").write_text(json.dumps(card), encoding="utf-8")


def test_dmaic_full_cycle_refuses_close_until_controlled(tmp_path):
    rng = random.Random(5)
    _ctq_history(tmp_path, [round(0.85 + rng.gauss(0, 0.005), 4) for _ in range(20)])
    bot = DMAICProjectBot(cwd=tmp_path)
    proj = bot.start(42, "r_task", problem="R_task too close to threshold", target=0.9, compound=False)
    assert proj["phase"] == "measure" and proj["baseline"]["n"] == 20
    with pytest.raises(ValueError, match="5 Whys"):
        bot.analyze(42, compound=False)
    RootCauseBot(cwd=tmp_path).why(42, "low R_task", ["a", "b", "tier 4 clamp hid signal"], category="measurement", compound=False)
    assert bot.analyze(42, compound=False)["analysis"]["category"] == "measurement"
    bot.improve(42, "clamp off, raw tier 4 signals", compound=False)
    _ctq_history(tmp_path, [round(0.93 + rng.gauss(0, 0.004), 4) for _ in range(10)])
    refused = bot.close(42, compound=False)
    assert refused["refused"] and "10 of 20" in refused["reason"]
    _ctq_history(tmp_path, [round(0.93 + rng.gauss(0, 0.004), 4) for _ in range(12)])
    ctrl = bot.control(42)["control"]
    assert ctrl["points_after_change"] == 22 and ctrl["improvement"] > 0 and ctrl["target_met"]
    if ctrl["status"] == "in_control":
        closed = bot.close(42, compound=False)
        assert closed["phase"] == "closed"


def test_dmaic_close_refused_when_chart_has_signals(tmp_path):
    _ctq_history(tmp_path, [0.85] * 5)
    bot = DMAICProjectBot(cwd=tmp_path, min_control_points=5)
    bot.start(9, "r_task", compound=False)
    RootCauseBot(cwd=tmp_path).why(9, "p", ["a", "b", "c"], compound=False)
    bot.analyze(9, compound=False)
    bot.improve(9, "change", compound=False)
    _ctq_history(tmp_path, [0.90, 0.91, 0.90, 0.91, 0.90, 0.91, 0.90, 0.99])
    res = bot.close(9, compound=False)
    assert res["refused"] and "out_of_control" in res["reason"]


def test_dmaic_guards(tmp_path):
    bot = DMAICProjectBot(cwd=tmp_path)
    with pytest.raises(ValueError, match="unknown metric"):
        bot.start(1, "bogus", compound=False)
    bot.start(1, "r_task", compound=False)
    with pytest.raises(FileExistsError):
        bot.start(1, "r_task", compound=False)
    with pytest.raises(ValueError, match="analyze before improve"):
        bot.improve(1, "x", compound=False)
    with pytest.raises(FileNotFoundError):
        bot.load(2)


# ------------------------------------------------------------------------------------ CLI
def test_cli_round_trip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _factory(tmp_path)
    _cards(tmp_path, [False] * 2 + [True] * 8)
    r = CliRunner()
    assert r.invoke(main, ["-o", "json", "fmea", "init", "demo"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "fmea", "init", "demo"]).exit_code == 2
    assert json.loads(r.invoke(main, ["-o", "json", "fmea", "score", "demo"]).output)["data"]["rows"]
    assert r.invoke(main, ["-o", "json", "fmea", "update", "demo", "D-01", "--issue", "5"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "fmea", "report"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "fmea", "sync-issues", "demo", "--dry-run"]).exit_code == 0
    assert json.loads(r.invoke(main, ["-o", "json", "rca", "pareto", "--since", "all"]).output)["data"]["total"] == 2
    assert r.invoke(main, ["-o", "json", "rca", "why", "3", "--problem", "p", "--because", "a"]).exit_code == 2
    assert r.invoke(main, ["-o", "json", "rca", "why", "3", "--problem", "p", "--because", "a", "--because", "b", "--because", "c"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "rca", "fishbone", "3"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "dmaic", "start", "3", "--ctq", "r_task"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "dmaic", "status"]).exit_code == 0
    assert r.invoke(main, ["-o", "json", "dmaic", "close", "3"]).exit_code == 2  # no change recorded yet


def test_services_and_template_registered():
    for svc, bot in (("fmea", "fmea-bot"), ("rca", "root-cause-bot"), ("dmaic", "dmaic-project-bot")):
        assert SERVICE_BOT_MAP[svc]["owning_bots"][0] == bot
    tpl = yaml.safe_load((REPO / ".github" / "ISSUE_TEMPLATE" / "dmaic-improvement.yml").read_text())
    ids = {b.get("id") for b in tpl["body"]}
    assert {"problem", "ctq", "baseline", "target", "root_cause", "change", "control_plan"} <= ids


def test_state_writes_stay_inside_their_directory(tmp_path):
    from hath0r_cli.qa.paths import write_state_json

    assert write_state_json(tmp_path, "a.json", {"x": 1}) == Path(os.path.realpath(tmp_path)) / "a.json"
    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    assert not (tmp_path / "a.tmp").exists()
    for bad in ("../x.json", "/etc/passwd", "a/b.json", "A.json", "x.txt", ".json"):
        with pytest.raises(ValueError):
            write_state_json(tmp_path, bad, {})
    rca = RootCauseBot(cwd=tmp_path)
    with pytest.raises(ValueError):
        rca._write_json("../elsewhere.json", {})
