"""Tests for complexity levels, the MFRM engine, item banks and JudgeCalibrationBot (#611-#615)."""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pytest
import yaml

from hath0r_cli.bots import judge_calibration_bot as jcb
from hath0r_cli.bots.judge_calibration_bot import (
    CallLedger,
    JudgeCalibrationBot,
    JudgeError,
    agreement_with_truth,
    build_judge,
)
from hath0r_cli.qa import rasch
from hath0r_cli.qa.complexity import ChangeMetrics, classify, cohen_kappa, is_test_path, metrics_from_changes
from hath0r_cli.qa.judge_items import CODE_CRITERIA, code_items, items_for, jev_items
from hath0r_cli.qa.msa import bias_study, gage_rr_by_stratum, linearity_study, verdict_flip_rate
from hath0r_cli.qa.stats import benjamini_hochberg, normal_sf_two_sided, t_quantile, t_sf_two_sided

REPO = Path(__file__).resolve().parents[2]
LEVELS = ["L1", "L2", "L3", "L4", "L5"]


# ----------------------------------------------------------------------------- stats
def test_t_distribution_and_quantile_round_trip():
    assert t_sf_two_sided(0.0, 10) == pytest.approx(1.0)
    assert t_sf_two_sided(2.228, 10) == pytest.approx(0.05, abs=1e-3)
    assert t_quantile(0.05, 10) == pytest.approx(2.228, abs=1e-3)
    assert normal_sf_two_sided(1.959964) == pytest.approx(0.05, abs=1e-6)


def test_benjamini_hochberg_step_up():
    assert benjamini_hochberg([0.001, 0.008, 0.039, 0.041, 0.6], q=0.05) == [True, True, False, False, False]
    assert benjamini_hochberg([0.01, 0.02, 0.03, 0.04], q=0.05) == [True, True, True, True]
    assert benjamini_hochberg([], q=0.05) == []


# ----------------------------------------------------------------------------- complexity
def test_classifier_levels():
    assert classify(metrics_from_changes({"README.md": ["x"]})) == "L1"
    assert classify(metrics_from_changes({"src/pkg/calc.py": ["def f():", "    return 1"], "tests/test_calc.py": ["def test_f(): pass"]})) == "L2"
    many = {"src/pkg/rules.py": [f"def r{i}():" for i in range(4)]}
    assert classify(metrics_from_changes(many)) == "L3"
    cross = {"src/pkg/a/x.py": ["def a():"], "src/pkg/b/y.py": ["def b():"]}
    assert classify(metrics_from_changes(cross)) == "L4"
    system = {**cross, "contracts/order.schema.json": ["{}"]}
    assert classify(metrics_from_changes(system)) == "L5"
    assert classify(ChangeMetrics(source_files=["a.py"], added_lines=700, modules=["a"])) == "L5"


def test_classifier_ignores_hath0r_state_and_detects_tests():
    m = metrics_from_changes({".hath0r/memory/graph.json": ["{}"], "CLAUDE.md": ["x"]})
    assert m.files == [] and classify(m) == "L1"
    assert is_test_path("tests/test_a.py") and is_test_path("pkg/a_test.py") and is_test_path("src/x/tests/helpers.py")
    assert not is_test_path(".pytest_cache/v/cache/nodeids") and not is_test_path("src/latest.py")


def test_cohen_kappa():
    a = ["L1", "L2", "L3", "L4", "L5"] * 4
    assert cohen_kappa(a, a)["kappa"] == 1.0
    b = ["L1", "L2", "L3", "L5", "L4"] * 4
    res = cohen_kappa(a, b)
    assert 0.0 < res["kappa"] < 1.0 and res["weighted_kappa"] > res["kappa"]
    assert res["disagreements"][:2] == [3, 4]
    with pytest.raises(ValueError):
        cohen_kappa(["L1"], [])


def test_complexity_levels_yaml_is_valid():
    doc = yaml.safe_load((REPO / "cfg/evals/complexity-levels.yaml").read_text())
    assert [lv["id"] for lv in doc["code"]["levels"]] == LEVELS
    assert [lv["id"] for lv in doc["mhc"]["levels"]] == [str(i) for i in range(6, 13)]
    assert {c["id"] for c in doc["rubrics"]["code"]["criteria"]} == set(CODE_CRITERIA)


# ----------------------------------------------------------------------------- level-stratified MSA
def _msa_rows(level_bias):
    rows = []
    for li, lvl in enumerate(LEVELS):
        for p in range(6):
            ref = 0.80 + 0.03 * p
            for op in ("a", "b"):
                for rep in range(3):
                    noise = ((p * 7 + rep * 3 + (op == "b")) % 5 - 2) * 0.001
                    rows.append({"part": f"{lvl}-{p}", "level": lvl, "operator": op, "replicate": rep, "value": ref + level_bias[li] + noise, "reference": ref})
    return rows


def test_bias_and_linearity_detect_level_drift():
    flat = _msa_rows([0.0] * 5)
    assert bias_study(flat)["passed"] and linearity_study(flat)["passed"]
    drift = _msa_rows([0.0, 0.01, 0.02, 0.03, 0.06])
    b = bias_study(drift)
    assert not b["passed"] and "L5" in " ".join(b["failures"])
    lin = linearity_study(drift)
    assert not lin["passed"] and lin["slope"] > 0


def test_gage_rr_by_stratum_and_flips():
    rows = _msa_rows([0.0] * 5)
    by = gage_rr_by_stratum(rows)
    assert set(by) == set(LEVELS) and all(v["passed"] for v in by.values())
    flips = verdict_flip_rate([{"part": "p", "value": m, "passed": m >= 0.80} for m in (0.79, 0.81, 0.80)])
    assert flips["flipped_parts"] == ["p"] and not flips["passed"]


# ----------------------------------------------------------------------------- MFRM
SIM_JUDGES = {"truth": 0.0, "a": 0.3, "b": -0.2, "c": 0.0}
SIM_PSI = {("a", "L5"): -0.6, ("b", "L1"): 0.5}


@pytest.fixture(scope="module")
def sim_result():
    rows = rasch.simulate(parts_per_level=120, levels=LEVELS, judges=SIM_JUDGES, psi=SIM_PSI, replicates=1, seed=11)
    t0 = time.monotonic()
    res = rasch.calibrate(rows, anchors=["truth"])
    return res, time.monotonic() - t0, rows


def test_mfrm_recovers_judge_severity(sim_result):
    res, _, _ = sim_result
    judges = res["fit"]["judges"]
    # severities are centred, so compare differences; C_j also absorbs the judge's mean psi
    mean_psi = {j: sum(SIM_PSI.get((j, lvl), 0.0) for lvl in LEVELS) / len(LEVELS) for j in ("a", "b")}
    expected = (SIM_JUDGES["a"] + mean_psi["a"]) - (SIM_JUDGES["b"] + mean_psi["b"])
    assert judges["a"]["measure"] - judges["b"]["measure"] == pytest.approx(expected, abs=0.12)
    assert res["fit"]["converged"]
    assert all(0.7 < j["infit"] < 1.3 for j in judges.values() if j["infit"] is not None)


def test_mfrm_recovers_bias_relative_to_truth_minus_judge_mean(sim_result):
    res, _, _ = sim_result
    cells = res["bias"]["cells"]
    for j in ("a", "b", "c"):
        true = {lvl: SIM_PSI.get((j, lvl), 0.0) for lvl in LEVELS}
        mu = sum(true.values()) / len(true)  # C_j absorbs the judge's mean psi
        for lvl in LEVELS:
            assert cells[j][lvl]["psi"] == pytest.approx(true[lvl] - mu, abs=0.25), (j, lvl)
    assert res["bias"]["reference"] == "anchors:truth"
    assert res["bias"]["swings"]["a"]["most_lenient"]["level"] == "L5"


def test_decisions_remove_biased_cells_and_certify_fair_ones(sim_result):
    res, _, _ = sim_result
    d = res["decisions"]
    assert d["a"]["L5"]["status"] == "removed_bias"
    assert d["b"]["L1"]["status"] == "removed_bias"
    assert all(d["c"][lvl]["status"] in ("certified", "not_certified") for lvl in LEVELS)
    assert "truth" not in d  # anchors are the reference, not judged
    statuses = {s for lv in d.values() for s in (c["status"] for c in lv.values())}
    assert statuses <= set(rasch.STATUSES)


def test_mfrm_performance(sim_result):
    _, elapsed, rows = sim_result
    assert len(rows) == 120 * 5 * 4 * 3
    assert elapsed < 30


def test_mfrm_noise_is_removed():
    rows = rasch.simulate(parts_per_level=40, levels=["L1", "L2"], judges={"truth": 0.0, "fair": 0.0}, replicates=2, seed=3)
    import random

    rng = random.Random(5)
    for r in list(rows):
        if r["judge"] == "fair":
            rows.append({**r, "judge": "noisy", "rating": rng.randrange(0, 5)})
    res = rasch.calibrate(rows, anchors=["truth"])
    assert {c["status"] for c in res["decisions"]["noisy"].values()} == {"removed_noise"}


def test_mfrm_rejects_bad_designs():
    with pytest.raises(rasch.RaschError):
        rasch.fit_mfrm([{"part": "p", "judge": "j", "criterion": "c"}])
    with pytest.raises(rasch.RaschError):
        rasch.fit_mfrm([{"part": "p", "judge": "j", "criterion": "c", "rating": 1.5}])
    disconnected = [
        {"part": "p1", "judge": "j1", "criterion": "c1", "rating": 1},
        {"part": "p1", "judge": "j1", "criterion": "c1", "rating": 2},
        {"part": "p2", "judge": "j2", "criterion": "c2", "rating": 0},
        {"part": "p2", "judge": "j2", "criterion": "c2", "rating": 1},
    ]
    assert not rasch.check_connected(disconnected)
    with pytest.raises(rasch.RaschError, match="disconnected"):
        rasch.fit_mfrm(disconnected)
    with pytest.raises(rasch.RaschError):
        rasch.fit_mfrm([{"part": "p", "judge": "j", "criterion": "c", "rating": 0}] * 3)


def test_extreme_cells_are_not_certified():
    rows = rasch.simulate(parts_per_level=30, levels=["R1", "R2"], judges={"truth": 0.0, "j": 0.0}, criteria={"decision": 0.0}, thresholds=(-1.0, 0.0, 1.0), replicates=2, seed=4)
    for r in rows:
        if r["judge"] == "j" and r["level"] == "R1":
            r["rating"] = 0
    res = rasch.calibrate(rows, anchors=["truth"])
    cell = res["bias"]["cells"]["j"]["R1"]
    assert cell["psi"] is None and cell["extreme_cell"] == "lowest"
    assert res["decisions"]["j"]["R1"]["status"] == "not_certified"


def test_repeatability_flags_deterministic_judges():
    rows = [{"part": p, "judge": "j", "criterion": "c", "replicate": r, "rating": 2} for p in ("a", "b") for r in (1, 2)]
    assert rasch.repeatability(rows)["j"]["deterministic"] is True


# ----------------------------------------------------------------------------- item banks
def test_item_banks_are_deterministic_and_levelled():
    a, b = code_items(10), code_items(10)
    assert [i["diff"] for i in a] == [i["diff"] for i in b]
    assert {i["level"] for i in a} == set(LEVELS)
    assert all(set(i["truth"]) == set(CODE_CRITERIA) for i in a)
    j = jev_items(12)
    assert {i["truth"]["decision"] for i in j} <= {0, 1, 2, 3}
    assert {i["level"] for i in j} == {"R1", "R2", "R3", "R4", "R5"}
    with pytest.raises(ValueError):
        items_for("nope", 1)


def test_generated_code_items_match_their_level():
    agree = 0
    items = code_items(20)
    for it in items:
        changes, cur = {}, None
        for ln in it["diff"].splitlines():
            if ln.startswith("+++ b/"):
                cur = ln[6:]
                changes[cur] = []
            elif cur and ln.startswith("+") and not ln.startswith("+++"):
                changes[cur].append(ln[1:])
        agree += classify(metrics_from_changes(changes)) == it["level"]
    assert agree / len(items) >= 0.9


# ----------------------------------------------------------------------------- bot
def _panel(tmp_path: Path, **extra) -> Path:
    panel = {
        "design": {"banks": ["code"], "per_level": {"code": 20}, "replicates": 2, "seed": 1},
        "budget": {"max_usd": 0},
        "judges": [
            {"id": "truth", "kind": "truth", "anchor": True, "banks": ["code", "jev"]},
            {"id": "fair", "kind": "stub", "noise": 0.4, "banks": ["code", "jev"]},
            {"id": "lenient", "kind": "stub", "noise": 0.4, "severity": {"L5": -1.0}, "banks": ["code"]},
        ],
        **extra,
    }
    p = tmp_path / "panel.yaml"
    p.write_text(yaml.safe_dump(panel))
    return p


def test_bot_runs_saves_registry_and_ledger(tmp_path):
    bot = JudgeCalibrationBot(cwd=tmp_path)
    study = bot.run_study(panel_path=_panel(tmp_path))
    assert study["complete"] and study["banks"]["code"]["summary"]["judges"] == 2
    assert (tmp_path / ".hath0r/evals/judges/latest.json").is_file()
    rows = (tmp_path / f".hath0r/evals/judges/{study['study_id']}.ratings.jsonl").read_text().splitlines()
    assert len(rows) == 3 * 20 * 5 * 2 * 4
    reg = bot.registry()["judges"]
    assert "fair" in reg and reg["fair"]["banks"]["code"]["calibration_id"] == study["study_id"]
    assert bot.is_certified("never", "L1")["certified"] is False
    lvl = reg["fair"]["banks"]["code"]["certified_levels"]
    if lvl:
        assert bot.is_certified("fair", lvl[0])["certified"] is True
    assert bot.report()["exists"] and bot.status()["has_study"]
    acc = study["banks"]["code"]["agreement_with_truth"]
    assert acc["truth"]["L1"]["exact"] == 1.0
    assert acc["lenient"]["L5"]["mean_error"] > 0.5


def test_bot_budget_cap_stops_and_marks_incomplete(tmp_path, monkeypatch):
    calls = {"n": 0}

    def fake_rate(self, item, replicate):
        calls["n"] += 1
        return {"ratings": dict(item["truth"]), "usage": {"input_tokens": 1_000_000, "output_tokens": 0}}

    monkeypatch.setattr(jcb.AnthropicJudge, "rate", fake_rate)
    panel = _panel(tmp_path, budget={"max_usd": 2.5}, prices_usd_per_mtok={"m": {"input": 1.0, "output": 1.0}})
    doc = yaml.safe_load(panel.read_text())
    doc["judges"].append({"id": "paid", "kind": "anthropic", "model": "m", "banks": ["code"]})
    panel.write_text(yaml.safe_dump(doc))
    study = JudgeCalibrationBot(cwd=tmp_path).run_study(panel_path=panel, judges=["paid"])
    assert not study["complete"] and "budget cap" in study["stopped_reason"]
    assert calls["n"] <= 3 + 6  # stops promptly (in-flight calls may finish)
    led = study["ledger"]
    assert led["valid"] and led["entries"] >= 3


def test_bot_resume_skips_finished_ratings(tmp_path):
    bot = JudgeCalibrationBot(cwd=tmp_path)
    first = bot.run_study(panel_path=_panel(tmp_path))
    ratings = tmp_path / f".hath0r/evals/judges/{first['study_id']}.ratings.jsonl"
    before = len(ratings.read_text().splitlines())
    again = bot.run_study(panel_path=_panel(tmp_path), resume=ratings)
    assert again["study_id"] == first["study_id"]
    assert len(ratings.read_text().splitlines()) == before
    assert again["banks"]["code"]["ratings"] == before


def test_ledger_detects_tampering(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = CallLedger(path)
    for i in range(3):
        led.append({"i": i})
    assert CallLedger.verify(path) == {"valid": True, "entries": 3}
    lines = path.read_text().splitlines()
    rec = json.loads(lines[1])
    rec["i"] = 99
    lines[1] = json.dumps(rec, sort_keys=True)
    path.write_text("\n".join(lines) + "\n")
    assert CallLedger.verify(path)["valid"] is False
    assert CallLedger(path).prev == json.loads(lines[-1])["entry_hash"]


def test_import_judge_reads_csv(tmp_path):
    item = code_items(1, levels=["L2"])[0]
    csv_path = tmp_path / "rater.csv"
    csv_path.write_text("judge,item,criterion,rating,replicate\n" + "".join(f"rater-1,{item['id']},{c},3,1\n" for c in CODE_CRITERIA))
    j = build_judge({"id": "rater-1", "kind": "import", "path": str(csv_path), "anchor": True})
    assert j.rate(item, 1)["ratings"] == {c: 3 for c in CODE_CRITERIA}
    with pytest.raises(JudgeError):
        j.rate(item, 2)
    with pytest.raises(ValueError):
        build_judge({"id": "x", "kind": "telepathy"})


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_live_adapters_parse_replies(monkeypatch):
    sent = []

    def fake_urlopen(req, timeout=0):
        sent.append((req.full_url, json.loads(req.data), dict(req.headers)))
        if "anthropic" in req.full_url:
            body = {"model": "claude-x", "content": [{"type": "text", "text": 'Sure: {"correctness": 3, "test_adequacy": 2, "goal_alignment": 4, "safety": 4}'}], "usage": {"input_tokens": 900, "output_tokens": 30}}
        elif "11434" in req.full_url:
            body = {"response": '{"decision": "deny"}', "prompt_eval_count": 200, "eval_count": 8}
        else:
            body = {"decision": "confirm", "confidence": 0.8}
        return _Resp(json.dumps(body).encode())

    monkeypatch.setattr(jcb.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("JEV_API_KEY", "test-key")
    code = code_items(1, levels=["L2"])[0]
    jev = jev_items(1, levels=["R4"])[0]
    out = build_judge({"id": "c", "kind": "anthropic", "model": "claude-x", "temperature": 0}).rate(code, 1)
    assert out["ratings"] == {"correctness": 3, "test_adequacy": 2, "goal_alignment": 4, "safety": 4}
    assert out["usage"]["input_tokens"] == 900
    assert sent[-1][1]["temperature"] == 0.0 and "Goal:" in sent[-1][1]["messages"][0]["content"]
    assert build_judge({"id": "o", "kind": "ollama", "model": "m", "banks": ["jev"]}).rate(jev, 1)["ratings"] == {"decision": 3}
    assert build_judge({"id": "j", "kind": "jev", "banks": ["jev"]}).rate(jev, 1)["ratings"] == {"decision": 2}
    assert sent[-1][1]["reversibility"] == jev["request"]["reversibility"]
    sys1 = build_judge({"id": "j1", "kind": "jev", "protocol": "systemone", "banks": ["jev"]})
    sys1.rate(jev, 1)
    assert sent[-1][1]["model"] == "jev-latest" and "state" in sent[-1][1]


def test_live_adapters_fail_loudly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(JudgeError, match="ANTHROPIC_API_KEY"):
        build_judge({"id": "c", "kind": "anthropic", "model": "m"}).rate(code_items(1, levels=["L2"])[0], 1)
    with pytest.raises(JudgeError):
        jcb._ratings_from_reply("code", {"correctness": 9})
    with pytest.raises(JudgeError):
        jcb._ratings_from_reply("jev", {"decision": "maybe"})
    with pytest.raises(JudgeError):
        jcb._parse_json_object("no json here")


def test_agreement_with_truth():
    rows = [{"judge": "j", "level": "L1", "rating": r, "truth": 2} for r in (2, 3, 0)]
    a = agreement_with_truth(rows)["j"]["L1"]
    assert a["exact"] == pytest.approx(1 / 3, abs=1e-3) and a["within_one"] == pytest.approx(2 / 3, abs=1e-3)


def test_repo_judge_panel_loads():
    panel = JudgeCalibrationBot(cwd=REPO).load_panel()
    ids = {j["id"] for j in panel["judges"]}
    assert {"truth", "jev"} <= ids
    assert panel["budget"]["max_usd"] > 0 and panel["gates"]["removal_psi"] == 0.20
    for spec in panel["judges"]:
        if spec.get("kind") != "import":
            build_judge(spec)


# ----------------------------------------------------------------------------- scorecards and SPC (#616)
def test_judge_calibration_status_and_fingerprint(tmp_path):
    from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot, judge_fingerprint

    ev = TaskEvaluatorBot(cwd=tmp_path)
    assert ev.judge_calibration_status({"judge": {"model": None}}, "L3")["required"] is False
    cfg = {"judge": {"model": "claude-opus-5-5"}, "judge_calibration": {"judge_id": "claude-opus", "enforce": True}}
    st = ev.judge_calibration_status(cfg, "L3")
    assert st["required"] and st["enforced"] and not st["certified"] and "never calibrated" in st["reason"]
    reg = tmp_path / ".hath0r/evals/judges/registry.json"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"judges": {"claude-opus": {"banks": {"code": {"calibration_id": "judges-x", "levels": {"L3": "certified", "L5": "removed_bias"}, "certified_levels": ["L3"]}}}}}))
    assert ev.judge_calibration_status(cfg, "L3")["certified"] is True
    assert ev.judge_calibration_status(cfg, "L5")["certified"] is False
    pinned = {**cfg, "judge_calibration": {**cfg["judge_calibration"], "calibration_id": "judges-x"}}
    assert judge_fingerprint(pinned) != judge_fingerprint(cfg)
    det = {"judge": {"model": None}, "judge_calibration": {"calibration_id": "judges-x"}}
    assert judge_fingerprint(det) == judge_fingerprint({"judge": {"model": None}})


def test_level_status_reads_stratified_study(tmp_path):
    from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

    ev = TaskEvaluatorBot(cwd=tmp_path)
    assert ev._level_status("L2")["qualified"] is False
    msa = tmp_path / ".hath0r/evals/msa/latest.json"
    msa.parent.mkdir(parents=True)
    msa.write_text(json.dumps({"by_level": {"gage_rr": {"L2": {"passed": True}, "L4": {"passed": True}}, "attribute_agreement": {"L2": {"passed": True}, "L4": {"passed": True}}, "bias": {"by_level": {"L2": {"passed": True}, "L4": {"passed": False}}}}}))
    assert ev._level_status("L2")["qualified"] is True
    l4 = ev._level_status("L4")
    assert l4["qualified"] is False and "bias" in l4["reason"]


def test_spc_level_and_judge_severity_series(tmp_path):
    from hath0r_cli.bots.spc_monitor_bot import SPCMonitorBot

    hist = tmp_path / ".hath0r/evals/history"
    hist.mkdir(parents=True)
    for i, lvl in enumerate(["L2", "L3", "L3"]):
        (hist / f"eval-{i}.json").write_text(json.dumps({"eval_id": f"e{i}", "evaluated_at": f"2026-11-1{i}", "r_task": 0.9 + i / 100, "complexity": {"level": lvl}, "judge": {"fingerprint": "fp"}}))
    jdir = tmp_path / ".hath0r/evals/judges"
    jdir.mkdir(parents=True)
    for i, psi in enumerate([0.1, -0.3]):
        (jdir / f"judges-{i}.json").write_text(json.dumps({"study_id": f"judges-{i}", "created_at": f"2026-11-1{i}", "banks": {"code": {"bias": {"cells": {"opus": {"L4": {"psi": psi}}}}}}}))
    bot = SPCMonitorBot(cwd=tmp_path)
    bot._current_fingerprint = lambda: "fp"  # type: ignore[method-assign]
    assert [p["id"] for p in bot.series("r_task@L3")] == ["e1", "e2"]
    assert len(bot.series("r_task")) == 3
    assert [p["value"] for p in bot.series("judge_severity@opus:L4")] == [0.1, -0.3]
    with pytest.raises(ValueError):
        bot.series("total_tokens@L3")
    with pytest.raises(ValueError):
        bot.series("judge_severity@opus")


def test_study_matches_contract(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    study = JudgeCalibrationBot(cwd=tmp_path).run_study(panel_path=_panel(tmp_path), dry_run=True)
    schema = json.loads((REPO / "contracts/hath0r-judge-calibration-v1.schema.json").read_text())
    jsonschema.validate(json.loads(json.dumps(study, default=str)), schema)


def test_judge_calibration_factory_and_config():
    factory = yaml.safe_load((REPO / "cfg/factories/judge-calibration-factory.yaml").read_text())
    assert factory["bots"][0]["id"] == "judge-calibration-bot"
    cfg = json.loads((REPO / "cfg/evals/task-eval.json").read_text())
    assert cfg["judge_calibration"]["enforce"] is True
