"""Phase 1 of the industrial QA plan (#580): eval gauge MSA (#584), poka-yoke (#583), Tier 4 clamp (#582)."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli.bots.measurement_system_bot import MeasurementSystemBot
from hath0r_cli.bots.quality import version_drift
from hath0r_cli.bots.taguchi_bot import TaguchiBot, load_responses_file
from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot, judge_fingerprint
from hath0r_cli.cccd import IncompleteExperimentError
from hath0r_cli.cli import main
from hath0r_cli.qa.msa import attribute_agreement, gage_rr_anova
from hath0r_cli.qa.stats import f_sf
from hath0r_cli.step_runner import SERVICE_BOT_MAP

REPO = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------------- statistics
def test_f_sf_matches_table_value():
    # F(2, 10) critical value at alpha = 0.05 is 4.10
    assert f_sf(4.10, 2, 10) == pytest.approx(0.05, abs=0.001)


def _synthetic(part_sd: float, noise_sd: float, op_bias: float = 0.0, seed: int = 7):
    rng = random.Random(seed)
    rows = []
    for p in range(10):
        true = 0.5 + rng.gauss(0, part_sd)
        for o, bias in (("a", 0.0), ("b", op_bias)):
            for _ in range(3):
                rows.append({"part": f"p{p}", "operator": o, "value": true + bias + rng.gauss(0, noise_sd)})
    return rows


def test_gage_rr_good_gauge_passes():
    res = gage_rr_anova(_synthetic(part_sd=0.1, noise_sd=0.002))
    assert res["passed"]
    assert res["grr_pct"] < 10
    assert res["ndc"] >= 5


def test_gage_rr_noisy_gauge_fails():
    res = gage_rr_anova(_synthetic(part_sd=0.01, noise_sd=0.02, op_bias=0.02))
    assert not res["passed"]
    assert res["grr_pct"] > 10
    assert res["variance_components"]["reproducibility"] > 0
    assert any("%GRR" in f for f in res["failures"])


def test_gage_rr_requires_balanced_study():
    rows = _synthetic(0.1, 0.01)
    rows.pop()
    with pytest.raises(ValueError, match="balanced"):
        gage_rr_anova(rows)


def test_gage_rr_flags_zero_variation():
    rows = [{"part": p, "operator": o, "value": 1.0} for p in ("x", "y") for o in ("a", "b") for _ in range(2)]
    res = gage_rr_anova(rows)
    assert not res["passed"]
    assert "No variation" in res["failures"][0]


def test_attribute_agreement_catches_missed_defect_and_inconsistency():
    rows = [
        {"part": "good", "expected": "pass", "passed": True},
        {"part": "good", "expected": "pass", "passed": True},
        {"part": "bad", "expected": "fail", "passed": False},
        {"part": "bad", "expected": "fail", "passed": True},
    ]
    res = attribute_agreement(rows)
    assert not res["passed"]
    assert res["missed_defects"] == ["bad"]
    assert res["inconsistent_parts"] == ["bad"]
    assert res["miss_rate"] == 0.5


# ------------------------------------------------------------------- measurement system bot
def _panel(tmp_path: Path) -> Path:
    panel = {
        "fixtures_root": "fx",
        "parts": [
            {"id": "good-1", "expected": "pass"},
            {"id": "good-2", "expected": "pass"},
            {"id": "bad-1", "expected": "fail"},
        ],
    }
    path = tmp_path / "panel.yaml"
    path.write_text(yaml.safe_dump(panel), encoding="utf-8")
    return path


TRUE_SCORE = {"good-1": 0.95, "good-2": 0.90, "bad-1": 0.60}


def _fake_measure(miss: str = ""):
    rng = random.Random(3)

    def measure(panel, part, operator, rep):
        v = TRUE_SCORE[part["id"]] + rng.gauss(0, 0.0005)
        passed = v >= 0.8 or part["id"] == miss
        return {"r_task": v, "passed": passed}

    return measure


def test_study_passes_and_qualifies_current_judge(tmp_path):
    bot = MeasurementSystemBot(cwd=tmp_path)
    res = bot.run_study(panel_path=_panel(tmp_path), measure=_fake_measure(), compound=False)
    assert res["passed"] and res["success"]
    assert res["schema_version"] == "hath0r.evals.msa-study/v1"
    latest = tmp_path / ".hath0r" / "evals" / "msa" / "latest.json"
    assert latest.is_file()
    assert (tmp_path / ".hath0r" / "evals" / "msa" / f"{res['study_id']}.json").is_file()

    status = TaskEvaluatorBot(cwd=tmp_path).measurement_status()
    assert status["qualified"] is True

    report = bot.report()
    assert report["exists"] and "measurements" not in report
    assert report["qualified_now"]["qualified"] is True


def test_study_fails_when_a_seeded_defect_passes(tmp_path):
    bot = MeasurementSystemBot(cwd=tmp_path)
    res = bot.run_study(panel_path=_panel(tmp_path), measure=_fake_measure(miss="bad-1"), compound=False)
    assert not res["passed"] and not res["success"]
    assert res["attribute_agreement"]["missed_defects"] == ["bad-1"]
    assert TaskEvaluatorBot(cwd=tmp_path).measurement_status()["qualified"] is False


def test_judge_change_disqualifies_gauge(tmp_path):
    bot = MeasurementSystemBot(cwd=tmp_path)
    bot.run_study(panel_path=_panel(tmp_path), measure=_fake_measure(), compound=False)
    cfg_dir = tmp_path / "cfg" / "evals"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "task-eval.json").write_text(json.dumps({"tier4": {"clamp": True}}), encoding="utf-8")
    status = TaskEvaluatorBot(cwd=tmp_path).measurement_status()
    assert status["qualified"] is False


def test_dry_run_writes_nothing(tmp_path):
    bot = MeasurementSystemBot(cwd=tmp_path)
    bot.run_study(panel_path=_panel(tmp_path), measure=_fake_measure(), dry_run=True)
    assert not (tmp_path / ".hath0r" / "evals" / "msa").exists()


@pytest.mark.parametrize(
    "parts,match",
    [
        ([{"id": "a", "expected": "pass"}], "at least 2 parts"),
        ([{"id": "a", "expected": "pass"}, {"id": "a", "expected": "fail"}], "unique"),
        ([{"id": "a", "expected": "pass"}, {"id": "b", "expected": "maybe"}], "expected"),
        ([{"id": "a", "expected": "pass"}, {"id": "b", "expected": "pass"}], "seeded defect"),
    ],
)
def test_panel_validation(tmp_path, parts, match):
    path = tmp_path / "p.yaml"
    path.write_text(yaml.safe_dump({"parts": parts}), encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        MeasurementSystemBot(cwd=tmp_path).load_panel(path)


def test_study_needs_two_replicates(tmp_path):
    with pytest.raises(ValueError, match="2 replicates"):
        MeasurementSystemBot(cwd=tmp_path).run_study(panel_path=_panel(tmp_path), replicates=1)


@pytest.mark.parametrize("part_id,expected", [("good-add-subtract", True), ("defect-missing-version-bump", False), ("defect-swallowed-exception", False)])
def test_canonical_measure_on_real_fixtures(part_id, expected):
    """The real panel is measured by the canonical TaskEvaluatorBot pipeline, not a stub."""
    bot = MeasurementSystemBot(cwd=REPO)
    panel = bot.load_panel()
    part = next(p for p in panel["parts"] if p["id"] == part_id)
    m = bot.canonical_measure(panel, part, panel["operators"][0], 1)
    assert m["passed"] is expected
    assert 0.0 <= m["r_task"] <= 1.0
    assert m["judge_fingerprint"]


def test_repo_panel_has_seeded_defects_for_each_tier():
    panel = MeasurementSystemBot(cwd=REPO).load_panel()
    defects = [p["id"] for p in panel["parts"] if p["expected"] == "fail"]
    assert {"defect-failing-test", "defect-swallowed-exception", "defect-missing-version-bump"} <= set(defects)
    for p in panel["parts"]:
        assert (panel["_fixtures_root"] / p["change"]).is_dir()


def test_msa_cli_report_without_study(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["-o", "json", "evals", "msa", "report"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["state"] == "empty"


def test_msa_cli_invalid_panel_exits_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "p.yaml").write_text(yaml.safe_dump({"parts": [{"id": "a", "expected": "pass"}]}), encoding="utf-8")
    result = CliRunner().invoke(main, ["-o", "json", "evals", "msa", "run", "--panel", "p.yaml"])
    assert result.exit_code == 2
    assert json.loads(result.output)["diagnostics"][0]["code"] == "MSA_STUDY_INVALID"


def test_measurement_system_bot_is_registered():
    assert "measurement-system-bot" in SERVICE_BOT_MAP["evals"]["owning_bots"]
    factory = yaml.safe_load((REPO / "cfg" / "factories" / "msa-study-factory.yaml").read_text())
    assert factory["workflows"][0]["steps"][0]["bot"] == "measurement-system-bot"


# ------------------------------------------------------------------------- tier 4 and judge
def test_tier4_clamp_off_reports_raw_signals(tmp_path):
    bot = TaskEvaluatorBot(cwd=tmp_path)
    raw = bot._evaluate_tier4_goal_alignment(task_id="t-1", issue_number=None, clamp=False)
    legacy = bot._evaluate_tier4_goal_alignment(task_id="t-1", issue_number=None, clamp=True)
    assert raw["clamped"] is False and legacy["clamped"] is True
    # With no focus and nothing compounded the raw score must not be propped up by floors.
    assert raw["score"] < legacy["score"]


def test_default_config_has_clamp_off_and_goal_of_100_percent(tmp_path):
    cfg = TaskEvaluatorBot(cwd=tmp_path).load_config()
    assert cfg["tier4"]["clamp"] is False
    assert cfg["goal"]["r_task"] == 1.0
    repo_cfg = json.loads((REPO / "cfg" / "evals" / "task-eval.json").read_text())
    assert repo_cfg["tier4"]["clamp"] is False


def test_judge_fingerprint_tracks_gauge_settings():
    base = {"judge": {"engine": "x"}, "tier4": {"clamp": False}, "weights": {}, "thresholds": {}}
    same = json.loads(json.dumps(base))
    same["observability"] = {"phoenix_enabled": False}  # not part of the gauge
    changed = json.loads(json.dumps(base))
    changed["tier4"]["clamp"] = True
    assert judge_fingerprint(base) == judge_fingerprint(same)
    assert judge_fingerprint(base) != judge_fingerprint(changed)


# ------------------------------------------------------------------------------ poka-yoke
def test_taguchi_incomplete_experiment_raises_and_partial_skips():
    bot = TaguchiBot()
    with pytest.raises(IncompleteExperimentError, match="missing runs \\[3, 4\\]"):
        bot.analyze(factors=["a", "b"], responses_matrix=[[1.0], [2.0]], array_type="L4")
    res = bot.analyze(factors=["a", "b"], responses_matrix=[[1.0], [2.0], [], [3.0]], array_type="L4", allow_partial=True)
    assert res["partial"] is True
    assert res["missing_runs"] == [3]
    assert res["measured_runs"] == 3
    assert [r["run_id"] for r in res["runs"]] == [1, 2, 4]


def test_taguchi_rejects_too_many_rows():
    with pytest.raises(ValueError, match="only 4 runs"):
        TaguchiBot().analyze(factors=["a"], responses_matrix=[[1.0]] * 5, array_type="L4")


def test_taguchi_level_count_must_match_array_column():
    bot = TaguchiBot()
    with pytest.raises(ValueError, match="tests exactly 2"):
        bot.generate_matrix(array_type="L4", factors=["a"], levels={"a": [1, 2, 3]})
    with pytest.raises(ValueError, match="not in the design"):
        bot.generate_matrix(array_type="L4", factors=["a"], levels={"typo": [1, 2]})


def test_load_responses_file_accepts_list_and_mapping(tmp_path):
    (tmp_path / "r.json").write_text(json.dumps([[1, 2], 3, None]), encoding="utf-8")
    assert load_responses_file(tmp_path / "r.json")["responses"] == [[1.0, 2.0], [3.0], []]
    (tmp_path / "r.yaml").write_text("levels: {a: [1, 2]}\nresponses: [[1], [2]]\n", encoding="utf-8")
    spec = load_responses_file(tmp_path / "r.yaml")
    assert spec["levels"] == {"a": [1, 2]}
    (tmp_path / "bad.yaml").write_text("foo: 1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_responses_file(tmp_path / "bad.yaml")


def test_optimize_taguchi_cli_refuses_incomplete_experiment(tmp_path):
    f = tmp_path / "r.yaml"
    f.write_text("levels: {a: [1, 2], b: [x, y]}\nresponses: [[1.0], [2.0]]\n", encoding="utf-8")
    runner = CliRunner()
    res = runner.invoke(main, ["-o", "json", "optimize", "taguchi", "-a", "L4", "--responses", str(f)])
    assert res.exit_code == 2
    assert json.loads(res.output)["diagnostics"][0]["code"] == "TAGUCHI_INVALID_EXPERIMENT"
    res = runner.invoke(main, ["-o", "json", "optimize", "taguchi", "-a", "L4", "--responses", str(f), "--allow-partial"])
    assert res.exit_code == 0
    analysis = json.loads(res.output)["data"]["analysis"]
    assert analysis["partial"] is True and analysis["missing_runs"] == [3, 4]


def test_version_drift_detects_mismatched_files(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.2.3"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [1.2.4] - 2026-11-11\n", encoding="utf-8")
    drift = version_drift(tmp_path, "1.2.4")
    files = {d["file"] for d in drift}
    assert "pyproject.toml" in files
    assert "CHANGELOG.md" not in files
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.2.4"\n', encoding="utf-8")
    assert version_drift(tmp_path, "1.2.4") == []
