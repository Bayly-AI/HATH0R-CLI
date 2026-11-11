"""Continuous Calibration Loop Coordinator for CCCD Engine."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from hath0r_cli.cccd.dspy_bridge import DSPyCompilerBridge
from hath0r_cli.cccd.l2ws_predictor import l2ws_predictor
from hath0r_cli.cccd.taguchi_optimizer import TaguchiLossOptimizer

CALIBRATION_SPEC = Path("cfg") / "cccd" / "doe-spec.yaml"
L9_LEVELS: Dict[str, List[float]] = {
    "temperature": [0.1, 0.2, 0.5],
    "top_p": [0.9, 0.95, 0.99],
    "guardrail_threshold": [0.8, 0.85, 0.9],
}


class CalibrationUnavailable(ValueError):
    """No measured responses and no measurement command: calibration never runs on invented data (#595)."""


@dataclass
class CCCDCalibrationLoop:
    """Coordinates telemetry sampling, benchmark evaluations, and continuous parameter adaptation."""

    cwd: Path = field(default_factory=Path.cwd)
    state_file: Path = field(default_factory=lambda: Path.cwd() / ".hath0r" / "cccd_state.json")
    taguchi_optimizer: TaguchiLossOptimizer = field(default_factory=TaguchiLossOptimizer)
    dspy_bridge: DSPyCompilerBridge = field(default_factory=DSPyCompilerBridge)

    def __post_init__(self) -> None:
        if self.cwd != Path.cwd() and self.state_file == Path.cwd() / ".hath0r" / "cccd_state.json":
            self.state_file = self.cwd / ".hath0r" / "cccd_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> Dict[str, Any]:
        """Load CCCD engine state from .hath0r/cccd_state.json."""
        if not self.state_file.exists():
            return {
                "active_calibration": False,
                "last_run_timestamp": None,
                "total_calibration_runs": 0,
                "current_parameters": {
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "top_p": 0.95,
                    "retry_count": 3,
                    "guardrail_threshold": 0.85,
                },
                "drift_metrics": {},
                "history": [],
            }
        with open(self.state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cast(Dict[str, Any], data) if isinstance(data, dict) else {}

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save CCCD engine state to .hath0r/cccd_state.json."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _spec(self, spec: Optional[Path] = None) -> Dict[str, Any]:
        import yaml

        path = spec or (self.cwd / CALIBRATION_SPEC)
        if not path.is_file():
            return {}
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return data if isinstance(data, dict) else {}

    def measure_responses(self, measure_cmd: str, replicates: int = 3) -> List[List[float]]:
        """Run ``measure_cmd`` for every L9 run (point as JSON on stdin), ``replicates`` times each."""
        from hath0r_cli.bots.doe_bot import shell_measure

        measure = shell_measure(measure_cmd)
        runs = self.taguchi_optimizer.bot.generate_matrix(array_type="L9", factors=list(L9_LEVELS), levels=L9_LEVELS)["matrix"]
        return [[measure({k: float(v) for k, v in run.items() if k != "run_id"}) for _ in range(max(1, replicates))] for run in runs]

    @staticmethod
    def _drift(history: List[Dict[str, Any]], entry: Dict[str, Any]) -> Dict[str, Any]:
        """Drift against the previous measured calibration; nothing before the first one."""
        prev = next((h for h in reversed(history) if h.get("responses_source") == "measured" and "mean_response" in h), None)
        if prev is None:
            return {"baseline_run_id": None}
        return {
            "baseline_run_id": prev.get("run_id"),
            "mean_response_drift": round(float(entry["mean_response"]) - float(prev["mean_response"]), 6),
            "snr_drift_db": round(float(entry["mean_snr_db"]) - float(prev.get("mean_snr_db", 0.0)), 6),
            "quality_loss_drift": round(float(entry["quality_loss"]) - float(prev.get("quality_loss", 0.0)), 6),
        }

    def run_calibration(
        self,
        dataset: Optional[List[Dict[str, Any]]] = None,
        iterations: int = 3,
        signature_name: str = "default_agent_signature",
        responses_matrix: Optional[List[List[float]]] = None,
        measure_cmd: Optional[str] = None,
        spec: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Calibrate on measured L9 responses with Taguchi OATS and the DSPy compiler.

        Responses come from ``responses_matrix`` or from a measurement command (``measure_cmd``, or
        ``measure_cmd`` in ``cfg/cccd/doe-spec.yaml``) run once per replicate for each of the 9 runs.
        With neither, ``CalibrationUnavailable`` is raised: nothing is simulated (#583, #595). Drift is
        measured against the previous calibration.
        """
        cfg = self._spec(spec)
        maximize = str(cfg.get("goal", "maximize")).lower() != "minimize"
        if not responses_matrix:
            cmd = measure_cmd or cfg.get("measure_cmd")
            if not cmd:
                raise CalibrationUnavailable(
                    f"no measured responses: set measure_cmd in {CALIBRATION_SPEC}, pass --measure-cmd, or pass --responses"
                )
            responses_matrix = self.measure_responses(str(cmd), replicates=int(cfg.get("replicates", 3)))

        state = self.load_state()

        # Load Princeton L2WS Warm-Start parameters
        warmstart = l2ws_predictor.predict_warmstart(signature_name)
        if warmstart.get("warmstart_parameters"):
            state["current_parameters"].update(warmstart["warmstart_parameters"])

        sample_dataset = dataset or [
            {"input": "Search codebase for vector index", "expected_output": "kb_index.py"},
            {"input": "Validate governance branch rules", "expected_output": "branch.py"},
            {"input": "Check doctor diagnostic report", "expected_output": "doctor.py"},
            {"input": "Parse CLI option parameters", "expected_output": "cli.py"},
        ]

        # 1. DSPy Prompt Compilation
        dspy_res = self.dspy_bridge.compile_signature(
            signature_name=signature_name,
            dataset=sample_dataset,
            max_bootstrapped_demos=min(4, len(sample_dataset)),
        )

        # 2. Taguchi Robust Parameter Optimization on measured responses
        taguchi_res = self.taguchi_optimizer.optimize_parameters(
            factors=list(L9_LEVELS),
            levels=L9_LEVELS,
            responses_matrix=responses_matrix,
            array_type="L9",
            criterion="larger_is_better" if maximize else "smaller_is_better",
            target_m=float(cfg.get("target", 1.0 if maximize else 0.0)),
            sensitivity_k=0.01,
        )

        optimal_params = taguchi_res["optimal_parameters"]
        state["current_parameters"].update(optimal_params)
        state["last_run_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state["total_calibration_runs"] += 1
        values = [float(v) for row in responses_matrix for v in row]

        calibration_entry = {
            "run_id": state["total_calibration_runs"],
            "timestamp": state["last_run_timestamp"],
            "iterations": iterations,
            "signature_compiled": signature_name,
            "optimal_parameters": optimal_params,
            "mean_snr_db": taguchi_res["mean_snr_db"],
            "quality_loss": taguchi_res["mean_quality_loss"],
            "mean_response": round(sum(values) / len(values), 6),
            "responses_source": "measured",
        }
        state["drift_metrics"] = self._drift(state.get("history") or [], calibration_entry)
        # 3. Log to MLflow experiment tracking if available
        mlflow_run_id = self._log_to_mlflow(
            signature_name=signature_name,
            iterations=iterations,
            optimal_params=optimal_params,
            taguchi_res=taguchi_res,
            drift_metrics=state["drift_metrics"],
            calibration_run=state["total_calibration_runs"],
        )
        if mlflow_run_id:
            calibration_entry["mlflow_run_id"] = mlflow_run_id

        state.setdefault("history", []).append(calibration_entry)
        self.save_state(state)
        l2ws_predictor.save_warmstart(signature_name, optimal_params, taguchi_res["mean_quality_loss"])

        return {
            "success": True,
            "calibration_id": state["total_calibration_runs"],
            "timestamp": state["last_run_timestamp"],
            "dspy_compilation": dspy_res,
            "taguchi_optimization": taguchi_res,
            "responses_source": "measured",
            "updated_parameters": state["current_parameters"],
            "drift_metrics": state["drift_metrics"],
            "mlflow_run_id": mlflow_run_id,
        }

    def _log_to_mlflow(
        self,
        signature_name: str,
        iterations: int,
        optimal_params: Dict[str, Any],
        taguchi_res: Dict[str, Any],
        drift_metrics: Dict[str, Any],
        calibration_run: int,
    ) -> Optional[str]:
        """Optionally record CCCD calibration metrics, Taguchi parameters, and S/N ratios to MLflow."""
        try:
            from hath0r_cli.bots.mlflow_manager_bot import mlflow_manager_bot

            params = {
                "signature_name": signature_name,
                "iterations": str(iterations),
                **{k: str(v) for k, v in optimal_params.items()},
            }
            metrics = {
                "mean_snr_db": float(taguchi_res.get("mean_snr_db", 0.0)),
                "quality_loss": float(taguchi_res.get("mean_quality_loss", 0.0)),
                **{k: float(v) for k, v in drift_metrics.items() if k.endswith("_drift") or k.endswith("_drift_db")},
            }
            tags = {
                "engine": "cccd",
                "calibration_run": str(calibration_run),
            }
            return mlflow_manager_bot.log_run(
                experiment_name="cccd-calibration",
                run_name=f"calibration_run_{calibration_run}",
                params=params,
                metrics=metrics,
                tags=tags,
                group="hath0r",
            )
        except Exception:
            return None

    def check_calibration_freshness(self, max_age_hours: float = 4.0) -> Dict[str, Any]:
        """Check if CCCD calibration was run within the last max_age_hours (default 4.0h)."""
        state = self.load_state()
        last_ts = state.get("last_run_timestamp") or state.get("last_run")

        if not last_ts:
            return {
                "is_fresh": False,
                "stale": True,
                "age_hours": None,
                "last_run_timestamp": None,
                "max_age_hours": max_age_hours,
                "message": "CCCD calibration has never been run on this repository. Calibration is required.",
            }

        try:
            from datetime import datetime, timezone

            if last_ts.endswith("Z"):
                dt_last = datetime.fromisoformat(last_ts[:-1]).replace(tzinfo=timezone.utc)
            else:
                dt_last = datetime.fromisoformat(last_ts)
                if dt_last.tzinfo is None:
                    dt_last = dt_last.replace(tzinfo=timezone.utc)

            dt_now = datetime.now(timezone.utc)
            age_seconds = (dt_now - dt_last).total_seconds()
            age_hours = round(max(0.0, age_seconds / 3600.0), 2)
            stale = age_hours > max_age_hours

            return {
                "is_fresh": not stale,
                "stale": stale,
                "age_hours": age_hours,
                "last_run_timestamp": last_ts,
                "max_age_hours": max_age_hours,
                "message": (
                    f"CCCD calibration is stale ({age_hours:.1f}h ago > {max_age_hours}h limit)."
                    if stale
                    else f"CCCD calibration is fresh ({age_hours:.1f}h ago)."
                ),
            }
        except Exception as err:
            return {
                "is_fresh": False,
                "stale": True,
                "age_hours": None,
                "last_run_timestamp": last_ts,
                "max_age_hours": max_age_hours,
                "error": str(err),
                "message": f"Unable to verify calibration freshness timestamp: {err}. Calibration recommended.",
            }

    def ensure_calibrated(
        self,
        max_age_hours: float = 4.0,
        trigger_source: str = "pre_task",
        iterations: int = 3,
        signature_name: str = "default_agent_signature",
    ) -> Dict[str, Any]:
        """Check 4-hour agent calibration freshness and automatically run calibration if expired (> max_age_hours)."""
        freshness = self.check_calibration_freshness(max_age_hours=max_age_hours)
        if freshness.get("is_fresh"):
            return {
                "success": True,
                "is_fresh": True,
                "auto_calibrated": False,
                "trigger_source": trigger_source,
                "age_hours": freshness.get("age_hours", 0.0),
                "max_age_hours": max_age_hours,
                "last_run_timestamp": freshness.get("last_run_timestamp"),
                "action_taken": "verified_fresh",
            }

        try:
            cal_res = self.run_calibration(iterations=iterations, signature_name=signature_name)
        except CalibrationUnavailable as err:
            # Stale and nothing to measure with: report it honestly instead of inventing a calibration.
            return {
                "success": True,
                "is_fresh": False,
                "auto_calibrated": False,
                "trigger_source": trigger_source,
                "age_hours": freshness.get("age_hours"),
                "max_age_hours": max_age_hours,
                "last_run_timestamp": freshness.get("last_run_timestamp"),
                "action_taken": "no_measurement_source",
                "message": str(err),
            }
        return {
            "success": bool(cal_res.get("success", True)),
            "is_fresh": True,
            "auto_calibrated": True,
            "trigger_source": trigger_source,
            "previous_age_hours": freshness.get("age_hours"),
            "age_hours": 0.0,
            "max_age_hours": max_age_hours,
            "calibration_id": cal_res.get("calibration_id"),
            "timestamp": cal_res.get("timestamp"),
            "updated_parameters": cal_res.get("updated_parameters", {}),
            "action_taken": "auto_calibrated_expired_state",
        }

    def get_status(self, max_age_hours: float = 4.0) -> Dict[str, Any]:
        """Inspect current calibration status, parameter values, drift metrics, and 4h freshness."""
        state = self.load_state()
        compiled = self.dspy_bridge.list_compiled_signatures()
        freshness = self.check_calibration_freshness(max_age_hours=max_age_hours)
        return {
            "success": True,
            "state": state,
            "freshness": freshness,
            "compiled_signatures_count": len(compiled),
            "compiled_signatures": [s.get("signature_name") for s in compiled if "signature_name" in s],
        }
