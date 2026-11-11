"""DoEBot: sequential design of experiments after Taguchi screening (WS8, #593).

1. Screen with a 2-level fractional factorial (or a Taguchi array via ``TaguchiBot``), 3+ replicates.
2. Keep the factors significant at p < 0.05.
3. Fit a response surface (central composite or Box-Behnken) on those 2-3 factors, or run Bayesian
   optimization when the optional ``optuna`` extra is installed (``pip install hath0r-cli[doe]``).
4. Confirm: measure at the predicted optimum and check it lands inside the prediction interval.

Every study is saved to ``.hath0r/optimize/<study_id>.json``; each confirmed optimum is compounded
as a fact node, and design points are logged to MLflow when it is reachable. Responses always come
from a measurement: nothing here simulates data.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

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
from hath0r_cli.qa.stats import mean

MeasureFn = Callable[[Dict[str, float]], float]
Ranges = Mapping[str, Sequence[float]]


STUDY_ID_RE = re.compile(r"doe-(screen|rsm|bayes)-\d{8}-\d{6}-[0-9a-f]{6}")


def _check_ranges(ranges: Ranges) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {}
    for f, r in ranges.items():
        if len(r) != 2 or float(r[0]) >= float(r[1]):
            raise ValueError(f"factor '{f}' needs a [low, high] range with low < high")
        out[str(f)] = [float(r[0]), float(r[1])]
    if len(out) < 2:
        raise ValueError("a designed experiment needs at least 2 factors")
    return out


def optuna_available() -> bool:
    try:
        import optuna  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class DoEBot:
    """Screening, response surface, Bayesian optimization and confirmation studies."""

    cwd: Path = field(default_factory=Path.cwd)
    log_mlflow: bool = True

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.study_dir = self.cwd / ".hath0r" / "optimize"

    # ----------------------------------------------------------------- storage
    def _save(self, study: Dict[str, Any]) -> Dict[str, Any]:
        self.study_dir.mkdir(parents=True, exist_ok=True)
        path = self.study_dir / f"{study['study_id']}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(study, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, path)
        study["path"] = str(path)
        return study

    def load(self, study_id: str) -> Dict[str, Any]:
        if not STUDY_ID_RE.fullmatch(str(study_id)):
            raise ValueError(f"not a DoE study id: '{study_id}' (expected doe-<kind>-<date>-<time>-<hex>)")
        path = self.study_dir / f"{study_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"no DoE study '{study_id}' in {self.study_dir}")
        return dict(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _new(kind: str, **extra: Any) -> Dict[str, Any]:
        return {
            "schema_version": "hath0r.optimize.doe-study/v1",
            "study_id": f"doe-{kind}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
            "kind": kind,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }

    def _mlflow(self, study: Dict[str, Any], runs: Sequence[Mapping[str, Any]], responses: Sequence[Sequence[float]]) -> None:
        if not self.log_mlflow:
            return
        try:
            from hath0r_cli.bots.mlflow_manager_bot import mlflow_manager_bot

            for i, (run, ys) in enumerate(zip(runs, responses), start=1):
                mlflow_manager_bot.log_run(
                    experiment_name="hath0r-doe",
                    run_name=f"{study['study_id']}-run{i}",
                    params={k: str(v) for k, v in run.items()},
                    metrics={"mean_response": float(mean(list(ys)))},
                    tags={"study_id": study["study_id"], "kind": study["kind"]},
                    group="hath0r",
                )
        except Exception as exc:  # MLflow is optional; the study file is the record
            study.setdefault("warnings", []).append(f"mlflow logging skipped: {exc}")

    @staticmethod
    def _measure_all(runs: Sequence[Mapping[str, float]], measure: MeasureFn, replicates: int) -> List[List[float]]:
        return [[float(measure(dict(r))) for _ in range(replicates)] for r in runs]

    # ------------------------------------------------------------------ screen
    def screen(
        self,
        ranges: Ranges,
        *,
        responses: Optional[Sequence[Sequence[float]]] = None,
        measure: Optional[MeasureFn] = None,
        fraction: int = 0,
        replicates: int = 3,
        alpha: float = 0.05,
        save: bool = True,
    ) -> Dict[str, Any]:
        """2-level (fractional) factorial screen. Without responses, returns the design to run."""
        rng = _check_ranges(ranges)
        coded = fractional_factorial(list(rng), fraction)
        natural = [decode(r, rng) for r in coded]
        study = self._new("screen", factors=rng, fraction=fraction, design=natural, coded_design=coded, alpha=alpha)
        if responses is None and measure is not None:
            if replicates < 2:
                raise ValueError("screening needs at least 2 replicates per run to estimate pure error")
            responses = self._measure_all(natural, measure, replicates)
        if responses is None:
            study["status"] = "awaiting_responses"
            return {"success": True, **(self._save(study) if save else study)}
        if len(responses) != len(coded):
            raise ValueError(f"the design has {len(coded)} runs but {len(responses)} response rows were given")
        anova = main_effects_anova(coded, [list(map(float, ys)) for ys in responses], alpha=alpha)
        study.update({"status": "analysed", "responses": [list(map(float, ys)) for ys in responses], "anova": anova, "significant_factors": anova["significant_factors"]})
        self._mlflow(study, natural, responses)
        return {"success": True, **(self._save(study) if save else study)}

    # --------------------------------------------------------------------- rsm
    def rsm(
        self,
        ranges: Ranges,
        *,
        responses: Optional[Sequence[Sequence[float]]] = None,
        measure: Optional[MeasureFn] = None,
        design: str = "ccd",
        replicates: int = 1,
        center_points: Optional[int] = None,
        goal: str = "maximize",
        save: bool = True,
    ) -> Dict[str, Any]:
        """Central composite or Box-Behnken design, quadratic fit and predicted optimum."""
        rng = _check_ranges(ranges)
        if len(rng) > 3:
            raise ValueError("response surfaces are for the 2 or 3 factors that survived screening")
        factors = list(rng)
        if design == "ccd":
            coded = central_composite(factors, center_points=4 if center_points is None else center_points)
        elif design == "bbd":
            coded = box_behnken(factors, center_points=3 if center_points is None else center_points)
        else:
            raise ValueError("design must be ccd or bbd")
        natural = [decode(r, rng) for r in coded]
        study = self._new("rsm", factors=rng, design_type=design, design=natural, coded_design=coded, goal=goal)
        if responses is None and measure is not None:
            responses = self._measure_all(natural, measure, max(1, replicates))
        if responses is None:
            study["status"] = "awaiting_responses"
            return {"success": True, **(self._save(study) if save else study)}
        if len(responses) != len(coded):
            raise ValueError(f"the design has {len(coded)} runs but {len(responses)} response rows were given")
        y = [mean(list(map(float, ys))) for ys in responses]
        model = fit_quadratic(coded, y, factors)
        opt = optimize_quadratic(model, goal=goal, bound=1.0)
        study.update({
            "status": "analysed",
            "responses": [list(map(float, ys)) for ys in responses],
            "model": model,
            "optimum": {"coded": opt["coded"], "natural": decode(opt["coded"], rng), "predicted": opt["predicted"],
                        "interval": [opt["predicted"] - 2 * model["sigma"], opt["predicted"] + 2 * model["sigma"]]},
        })
        self._mlflow(study, natural, responses)
        return {"success": True, **(self._save(study) if save else study)}

    # ------------------------------------------------------------------- bayes
    def bayes(self, ranges: Ranges, *, measure: Optional[MeasureFn] = None, n_trials: int = 30, goal: str = "maximize", seed: int = 0, save: bool = True) -> Dict[str, Any]:
        """Bayesian optimization (TPE) with the optional optuna extra; falls back to a CCD response surface."""
        rng = _check_ranges(ranges)
        if measure is None:
            raise ValueError("Bayesian optimization measures as it goes: supply a measurement (--measure-cmd)")
        if not optuna_available():
            res = self.rsm(rng, measure=measure, goal=goal, save=save)
            res["fallback"] = "rsm (optuna not installed: pip install 'hath0r-cli[doe]')"
            return res
        import optuna

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        sampler = optuna.samplers.TPESampler(seed=seed)
        st = optuna.create_study(direction=goal, sampler=sampler)

        def objective(trial: Any) -> float:
            point = {f: trial.suggest_float(f, lo, hi) for f, (lo, hi) in rng.items()}
            return float(measure(point))

        st.optimize(objective, n_trials=n_trials)
        trials = [{"params": t.params, "value": t.value} for t in st.trials]
        study = self._new("bayes", factors=rng, goal=goal, n_trials=n_trials, trials=trials, status="analysed",
                          optimum={"natural": st.best_params, "coded": encode(st.best_params, rng), "predicted": st.best_value})
        self._mlflow(study, [t["params"] for t in trials], [[t["value"]] for t in trials])
        return {"success": True, **(self._save(study) if save else study)}

    # ----------------------------------------------------------------- confirm
    def confirm(self, study_id: str, observed: Sequence[float], compound: bool = True) -> Dict[str, Any]:
        """Check observations at the predicted optimum against the model's interval (rsm studies)."""
        study = self.load(study_id)
        if study.get("kind") != "rsm" or "model" not in study:
            raise ValueError("confirmation needs an analysed rsm study (its model gives the prediction interval)")
        res = confirmation(study["model"], study["optimum"]["coded"], [float(v) for v in observed])
        study["confirmation"] = {**res, "observed": [float(v) for v in observed], "at": datetime.now(timezone.utc).isoformat()}
        self._save(study)
        if res["confirmed"] and compound:
            self._compound_optimum(study)
        return {"success": bool(res["confirmed"]), **study}

    def _compound_optimum(self, study: Dict[str, Any]) -> None:
        try:
            from hath0r_cli.bots.memory_manager import MemoryManagerBot

            MemoryManagerBot(cwd=self.cwd).compound_memory(
                node_id=f"fact:doe:{study['study_id']}",
                node_type="fact",
                label=f"Confirmed optimum {study['study_id']}",
                content=f"Optimum {study['optimum']['natural']} predicted {study['optimum']['predicted']:.4g}, confirmed mean {study['confirmation']['observed_mean']:.4g}.",
                tags=["doe", "optimum", "confirmed"],
                source_files=[f".hath0r/optimize/{study['study_id']}.json"],
                sync_agentgraph=False,
            )
        except Exception as exc:  # the study file is the record
            study.setdefault("warnings", []).append(f"memory compounding failed: {exc}")

    # -------------------------------------------------------------- sequential
    def sequential(
        self,
        ranges: Ranges,
        measure: MeasureFn,
        *,
        replicates: int = 3,
        fraction: int = 0,
        goal: str = "maximize",
        confirm_replicates: int = 3,
        alpha: float = 0.05,
        use_bayes: bool = False,
        compound: bool = True,
    ) -> Dict[str, Any]:
        """Screen, keep significant factors (at most 3), fit a surface, then confirm at the optimum."""
        rng = _check_ranges(ranges)
        screen = self.screen(rng, measure=measure, fraction=fraction, replicates=replicates, alpha=alpha)
        factors = screen["anova"]["factors"]
        keep = list(screen["significant_factors"])
        if len(keep) < 2:  # a surface needs 2 factors: add the strongest of the rest by F
            ranked = sorted(factors, key=lambda f: -float(factors[f]["f"]))
            keep = (keep + [f for f in ranked if f not in keep])[:2]
        keep = sorted(keep, key=lambda f: -float(factors[f]["f"]))[:3]
        sub = {f: rng[f] for f in keep}
        fixed_levels = {f: (lo + hi) / 2.0 for f, (lo, hi) in rng.items() if f not in sub}

        def measure_sub(point: Dict[str, float]) -> float:
            return float(measure({**fixed_levels, **point}))

        if use_bayes and optuna_available():
            stage2 = self.bayes(sub, measure=measure_sub, goal=goal)
            return {"success": True, "screen": screen["study_id"], "optimize": stage2["study_id"], "kept_factors": keep, "fixed_levels": fixed_levels, "optimum": stage2["optimum"], "confirmed": None}
        surface = self.rsm(sub, measure=measure_sub, goal=goal)
        best = surface["optimum"]["natural"]
        observed = [measure_sub(dict(best)) for _ in range(max(1, confirm_replicates))]
        conf = self.confirm(surface["study_id"], observed, compound=compound)
        return {
            "success": conf["success"],
            "schema_version": "hath0r.optimize.sequential/v1",
            "screen": screen["study_id"],
            "rsm": surface["study_id"],
            "kept_factors": keep,
            "fixed_levels": fixed_levels,
            "optimum": {**surface["optimum"], "natural": {**fixed_levels, **best}},
            "confirmation": conf["confirmation"],
            "confirmed": conf["confirmation"]["confirmed"],
        }

    def calibrate_sequential(self, spec: str, measure_cmd: Optional[str] = None) -> Dict[str, Any]:
        """Factory step: run ``sequential`` from a spec file and a measurement command.

        ``measure_cmd`` defaults to the spec's ``measure_cmd``. With neither set the step refuses:
        nothing is ever simulated.
        """
        import yaml

        path = Path(spec) if Path(spec).is_absolute() else self.cwd / spec
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        cmd = measure_cmd or data.get("measure_cmd")
        if not cmd:
            raise ValueError(f"no measurement command: set measure_cmd in {spec} or pass --measure-cmd")
        return self.sequential(data.get("factors") or {}, shell_measure(str(cmd)), goal=data.get("goal", "maximize"), replicates=int(data.get("replicates", 3)))

    def predict_at(self, study_id: str, point: Mapping[str, float]) -> float:
        study = self.load(study_id)
        return predict(study["model"], encode(point, study["factors"]))

    def status(self) -> Dict[str, Any]:
        studies = sorted(p.stem for p in self.study_dir.glob("doe-*.json")) if self.study_dir.is_dir() else []
        return {"success": True, "bot_id": "doe-bot", "studies": studies, "optuna_available": optuna_available()}


def shell_measure(cmd: str, timeout: float = 600.0) -> MeasureFn:
    """A measurement that runs ``cmd`` with the point as JSON on stdin and reads one number from stdout."""
    import shlex
    import subprocess

    argv = shlex.split(cmd)

    def measure(point: Dict[str, float]) -> float:
        res = subprocess.run(argv, input=json.dumps(point), capture_output=True, text=True, timeout=timeout, check=False)
        if res.returncode != 0:
            raise RuntimeError(f"measure command failed ({res.returncode}): {res.stderr.strip()[:200]}")
        lines = [ln for ln in res.stdout.strip().splitlines() if ln.strip()]
        if not lines:
            raise RuntimeError("measure command printed no number")
        return float(lines[-1])

    return measure
