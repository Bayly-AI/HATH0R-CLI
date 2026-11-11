"""Phase 4 of the industrial QA plan (#580): sequential design of experiments (#593)."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli.bots import doe_bot as doe_mod
from hath0r_cli.bots.doe_bot import DoEBot, shell_measure
from hath0r_cli.cli import main
from hath0r_cli.qa.doe import (
    box_behnken,
    central_composite,
    confirmation,
    decode,
    encode,
    fit_quadratic,
    fractional_factorial,
    main_effects_anova,
    optimize_quadratic,
    predict,
)
from hath0r_cli.step_runner import SERVICE_BOT_MAP

REPO = Path(__file__).resolve().parents[2]
RANGES = {"temperature": [0.1, 0.7], "top_p": [0.85, 0.99], "guardrail_threshold": [0.75, 0.95]}


def _response(point, rng=None):
    """A smooth surface peaking at temperature 0.3, top_p 0.95; guardrail_threshold has no effect."""
    t, p = point["temperature"], point["top_p"]
    noise = rng.gauss(0, 0.002) if rng else 0.0
    return 0.98 - 2.0 * (t - 0.3) ** 2 - 20.0 * (p - 0.95) ** 2 + noise


def _measure(seed=7):
    rng = random.Random(seed)
    return lambda point: _response(point, rng)


@pytest.fixture
def bot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(doe_mod.DoEBot, "_compound_optimum", lambda self, study: None)
    return DoEBot(cwd=tmp_path, log_mlflow=False)


# ---------------------------------------------------------------------------- designs
def test_full_and_fractional_factorial_sizes():
    assert len(fractional_factorial(["a", "b", "c"])) == 8
    half = fractional_factorial(["a", "b", "c", "d"], 1)
    assert len(half) == 8
    assert all(set(r.values()) <= {-1, 1} for r in half)
    for f in "abcd":  # balanced columns
        assert sum(r[f] for r in half) == 0


def test_rsm_designs_have_axial_and_center_points():
    ccd = central_composite(["a", "b"], center_points=4)
    assert len(ccd) == 4 + 4 + 4
    assert sum(1 for r in ccd if all(v == 0 for v in r.values())) == 4
    bbd = box_behnken(["a", "b", "c"], center_points=3)
    assert len(bbd) == 12 + 3


def test_encode_decode_round_trip():
    point = {"temperature": 0.4, "top_p": 0.9}
    rng = {k: RANGES[k] for k in point}
    assert decode(encode(point, rng), rng) == pytest.approx(point)


def test_anova_finds_the_active_factor():
    runs = fractional_factorial(["a", "b"])
    r = random.Random(1)
    ys = [[5.0 + 2.0 * run["a"] + r.gauss(0, 0.1) for _ in range(3)] for run in runs]
    anova = main_effects_anova(runs, ys, alpha=0.05)
    assert anova["significant_factors"] == ["a"]


def test_quadratic_fit_recovers_the_optimum():
    runs = central_composite(["x", "y"], center_points=3)
    y = [1.0 - (r["x"] - 0.3) ** 2 - 2 * (r["y"] + 0.2) ** 2 for r in runs]
    model = fit_quadratic(runs, y, ["x", "y"])
    opt = optimize_quadratic(model, goal="maximize")
    assert opt["coded"]["x"] == pytest.approx(0.3, abs=1e-3)
    assert opt["coded"]["y"] == pytest.approx(-0.2, abs=1e-3)
    assert predict(model, opt["coded"]) == pytest.approx(1.0, abs=1e-6)
    assert confirmation(model, opt["coded"], [1.0, 1.0])["confirmed"]


# ------------------------------------------------------------------------------- bot
def test_screen_without_responses_returns_the_design(bot):
    res = bot.screen(RANGES)
    assert res["status"] == "awaiting_responses"
    assert len(res["design"]) == 8
    assert Path(res["path"]).is_file()


def test_screen_rejects_wrong_response_count_and_bad_ranges(bot):
    with pytest.raises(ValueError):
        bot.screen(RANGES, responses=[[1.0, 1.0]])
    with pytest.raises(ValueError):
        bot.screen({"a": [1.0, 0.5]})
    with pytest.raises(ValueError):
        bot.screen(RANGES, measure=_measure(), replicates=1)


def test_screen_measures_and_flags_significant_factors(bot):
    res = bot.screen(RANGES, measure=_measure(), replicates=3)
    assert res["status"] == "analysed"
    assert "guardrail_threshold" not in res["significant_factors"]
    assert "top_p" in res["significant_factors"]


def test_rsm_limits_and_optimum(bot):
    with pytest.raises(ValueError):
        bot.rsm({**RANGES, "extra": [0, 1]})
    with pytest.raises(ValueError):
        bot.rsm(RANGES, design="nope")
    sub = {k: RANGES[k] for k in ("temperature", "top_p")}
    res = bot.rsm(sub, measure=_measure(), goal="maximize")
    assert res["optimum"]["natural"]["temperature"] == pytest.approx(0.3, abs=0.03)
    assert res["optimum"]["natural"]["top_p"] == pytest.approx(0.95, abs=0.01)
    lo, hi = res["optimum"]["interval"]
    assert lo <= res["optimum"]["predicted"] <= hi
    bbd = bot.rsm(RANGES, design="bbd")
    assert bbd["status"] == "awaiting_responses"


def test_confirm_needs_an_analysed_rsm_and_reports_outcome(bot):
    screen = bot.screen(RANGES)
    with pytest.raises(ValueError):
        bot.confirm(screen["study_id"], [0.9])
    sub = {k: RANGES[k] for k in ("temperature", "top_p")}
    surface = bot.rsm(sub, measure=_measure())
    good = bot.confirm(surface["study_id"], [surface["optimum"]["predicted"]] * 3)
    assert good["success"] and good["confirmation"]["confirmed"]
    bad = bot.confirm(surface["study_id"], [0.1, 0.1, 0.1])
    assert not bad["success"]
    with pytest.raises(FileNotFoundError):
        bot.load("doe-rsm-20260101-000000-abcdef")
    for bad in ("../../etc/passwd", "doe-rsm-missing", "doe-rsm-20260101-000000-abcdef/../x"):
        with pytest.raises(ValueError):
            bot.load(bad)


def test_sequential_screens_fits_and_confirms(bot):
    res = bot.sequential(RANGES, _measure(), replicates=3)
    assert res["confirmed"] is True
    assert set(res["kept_factors"]) >= {"temperature", "top_p"}
    assert res["optimum"]["natural"]["temperature"] == pytest.approx(0.3, abs=0.05)
    assert bot.status()["studies"]


def test_bayes_needs_a_measurement_and_falls_back_without_optuna(bot, monkeypatch):
    with pytest.raises(ValueError):
        bot.bayes(RANGES)
    monkeypatch.setattr(doe_mod, "optuna_available", lambda: False)
    sub = {k: RANGES[k] for k in ("temperature", "top_p")}
    res = bot.bayes(sub, measure=_measure())
    assert res["kind"] == "rsm"
    assert "optuna not installed" in res["fallback"]


def test_shell_measure_reads_last_number_and_reports_failures(tmp_path):
    ok = tmp_path / "m.py"
    ok.write_text("import json,sys\np=json.load(sys.stdin)\nprint('log')\nprint(p['x']*2)\n")
    assert shell_measure(f"{sys.executable} {ok}")({"x": 1.5}) == pytest.approx(3.0)
    bad = tmp_path / "b.py"
    bad.write_text("import sys\nsys.exit(3)\n")
    with pytest.raises(RuntimeError):
        shell_measure(f"{sys.executable} {bad}")({"x": 1})
    silent = tmp_path / "s.py"
    silent.write_text("pass\n")
    with pytest.raises(RuntimeError):
        shell_measure(f"{sys.executable} {silent}")({"x": 1})


def _measure_script(tmp_path):
    script = tmp_path / "measure.py"
    script.write_text(
        "import json,sys\np=json.load(sys.stdin)\n"
        "print(0.98 - 2.0*(p['temperature']-0.3)**2 - 20.0*(p['top_p']-0.95)**2)\n"
    )
    return f"{sys.executable} {script}"


def test_calibrate_sequential_uses_the_spec_measure_cmd_and_refuses_without(bot, tmp_path):
    spec = tmp_path / "spec.yaml"
    spec.write_text(yaml.safe_dump({"factors": {k: RANGES[k] for k in ("temperature", "top_p")}, "replicates": 2}))
    with pytest.raises(ValueError, match="no measurement command"):
        bot.calibrate_sequential(str(spec))
    spec.write_text(yaml.safe_dump({"factors": {k: RANGES[k] for k in ("temperature", "top_p")}, "replicates": 2, "measure_cmd": _measure_script(tmp_path)}))
    res = bot.calibrate_sequential("spec.yaml")
    assert res["optimum"]["natural"]["top_p"] == pytest.approx(0.95, abs=0.01)


# ------------------------------------------------------------------------------- CLI
def _invoke(args):
    return CliRunner().invoke(main, ["-o", "json", *args])


@pytest.fixture
def cli_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(doe_mod.DoEBot, "_mlflow", lambda *a, **k: None)
    monkeypatch.setattr(doe_mod.DoEBot, "_compound_optimum", lambda self, study: None)
    return tmp_path


def test_cli_screen_prints_design_then_analyses_spec_responses(cli_dir):
    res = _invoke(["optimize", "screen", "--factor", "temperature=0.1:0.7", "--factor", "top_p=0.85:0.99"])
    assert res.exit_code == 0, res.output
    out = json.loads(res.output)
    data = out.get("data", out)
    assert data["status"] == "awaiting_responses"
    rows = [[_response(run)] * 2 for run in data["design"]]
    spec = cli_dir / "s.yaml"
    spec.write_text(yaml.safe_dump({"factors": {"temperature": [0.1, 0.7], "top_p": [0.85, 0.99]}, "responses": rows}))
    res = _invoke(["optimize", "screen", "--spec", str(spec)])
    assert res.exit_code == 0, res.output


def test_cli_rejects_bad_factor_and_bad_response_count(cli_dir):
    res = _invoke(["optimize", "screen", "--factor", "temperature"])
    assert res.exit_code == 2
    assert "DOE_INVALID_INPUT" in res.output
    spec = cli_dir / "s.yaml"
    spec.write_text(yaml.safe_dump({"factors": {"a": [0, 1], "b": [0, 1]}, "responses": [[1.0]]}))
    assert _invoke(["optimize", "rsm", "--spec", str(spec)]).exit_code == 2


def test_cli_rsm_and_confirm_with_measure_cmd(cli_dir):
    cmd = _measure_script(cli_dir)
    res = _invoke(["optimize", "rsm", "--factor", "temperature=0.1:0.7", "--factor", "top_p=0.85:0.99", "--measure-cmd", cmd])
    assert res.exit_code == 0, res.output
    out = json.loads(res.output)
    data = out.get("data", out)
    pred = data["optimum"]["predicted"]
    res = _invoke(["optimize", "confirm", data["study_id"], "--observed", f"{pred},{pred}"])
    assert res.exit_code == 0, res.output
    res = _invoke(["optimize", "confirm", data["study_id"], "--observed", "0.1,0.1"])
    assert res.exit_code != 0


def test_cli_cccd_sequential_refuses_without_spec_or_measure(cli_dir):
    res = _invoke(["cccd", "calibrate", "--strategy", "sequential"])
    assert res.exit_code == 2
    spec = cli_dir / "s.yaml"
    spec.write_text(yaml.safe_dump({"factors": {"temperature": [0.1, 0.7], "top_p": [0.85, 0.99]}}))
    res = _invoke(["cccd", "calibrate", "--strategy", "sequential", "--spec", str(spec)])
    assert res.exit_code == 2
    assert "no measurement command" in res.output


def test_cli_cccd_sequential_runs_end_to_end(cli_dir):
    spec = cli_dir / "s.yaml"
    spec.write_text(yaml.safe_dump({"factors": {"temperature": [0.1, 0.7], "top_p": [0.85, 0.99]}, "replicates": 2}))
    res = _invoke(["cccd", "calibrate", "--strategy", "sequential", "--spec", str(spec), "--measure-cmd", _measure_script(cli_dir)])
    assert res.exit_code == 0, res.output


# -------------------------------------------------------------------------- wiring
def test_doe_bot_is_wired_into_the_optimize_service_and_factory():
    assert "doe-bot" in SERVICE_BOT_MAP["optimize"]["owning_bots"]
    factory = yaml.safe_load((REPO / "cfg/factories/cccd-4h-calibration-factory.yaml").read_text())
    steps = {s["id"]: s for wf in factory["workflows"] for s in wf["steps"]}
    assert steps["sequential"]["bot"] == "doe-bot"
    assert "measure_cmd" not in steps["sequential"]["args"]
    spec = yaml.safe_load((REPO / "cfg/cccd/doe-spec.yaml").read_text())
    assert spec["measure_cmd"] is None
    assert set(spec["factors"]) == set(RANGES)
    contract = json.loads((REPO / "contracts/hath0r-doe-study-v1.schema.json").read_text())
    assert contract["title"] == "hath0r.optimize.doe-study/v1"
    for d, name in [("strategies", "doe-strategy"), ("procedures", "doe-procedure"), ("playbooks", "doe-playbook"), ("runbooks", "doe-runbook"), ("workflows", "sequential-doe-workflow"), ("bot-specs", "doe-bot-spec")]:
        assert (REPO / "docs/governance" / d / f"{name}.md").is_file()


def test_mcp_doe_tool(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from hath0r_cli.server.mcp_server import create_mcp_server

    tool = create_mcp_server()._tool_manager._tools["hath0r_optimize_doe"].fn
    assert tool(action="screen")["code"] == "DOE_INVALID_INPUT"
    assert tool(action="nope", factors={"a": [0, 1]})["code"] == "DOE_INVALID_INPUT"
    assert tool(action="confirm")["code"] == "DOE_INVALID_INPUT"
    design = tool(action="screen", factors={"a": [0, 1], "b": [0, 1]})
    assert design["status"] == "awaiting_responses"
    rsm = tool(action="rsm", factors={"a": [0, 1], "b": [0, 1]})
    assert rsm["status"] == "awaiting_responses"
    assert tool(action="status")["bot_id"] == "doe-bot"
