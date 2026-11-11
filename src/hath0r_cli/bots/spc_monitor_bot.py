"""SPCMonitorBot: statistical process control over Hath0r's own quality signals (WS2/WS3, #586, #587).

Watches the eval history (``.hath0r/evals/history/*.json``) and the FinOps token ledgers with
I-MR, EWMA and CUSUM charts plus Western Electric rules, and reports process capability
(Cpk/Ppk) of ``R_task`` against the eval threshold.

Validated decision (2026-11-11): signals and low Cpk are **warnings** by default. Set
``capability.mode: block`` in ``thresholds.json`` to make them blocking later.

#608: eval metrics are charted only from history scored by the current judge (same
``judge.fingerprint``), since points from another gauge are not comparable. The default mode is
``auto``: warnings until a metric has a sufficient baseline from that gauge, blocking after.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hath0r_cli.qa.spc import MIN_BASELINE_POINTS, baseline, capability, chart

DEFAULT_CAPABILITY: Dict[str, Any] = {
    "mode": "auto",
    "min_cpk_warn": 1.33,
    "baseline_points": MIN_BASELINE_POINTS,
    "ewma_lambda": 0.2,
}
"""Seeded into ``thresholds.json`` under ``capability``. ``mode`` is ``warn``, ``block`` or ``auto``."""
CAPABILITY_MODES = ("warn", "block", "auto")

EVAL_METRICS = {
    "r_task": ("r_task",),
    "deterministic": ("tier_scores", "deterministic"),
    "trajectory": ("tier_scores", "trajectory"),
    "adversarial": ("tier_scores", "adversarial"),
    "goal_alignment": ("tier_scores", "goal_alignment"),
    "eval_duration_ms": ("duration_ms",),
}
TOKEN_METRICS = ("total_tokens", "cost_usd", "latency_ms")
TOKEN_LEDGERS = (
    Path(".hath0r") / "state" / "finops" / "token_ledger.jsonl",
    Path(".hath0r") / "finops" / "token_telemetry.jsonl",
)
METRICS: Tuple[str, ...] = tuple(EVAL_METRICS) + TOKEN_METRICS


def _dig(obj: Any, path: Tuple[str, ...]) -> Optional[float]:
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    try:
        return float(obj)
    except (TypeError, ValueError):
        return None


@dataclass
class SPCMonitorBot:
    """Charts Hath0r quality and cost signals and reports capability."""

    cwd: Path = field(default_factory=Path.cwd)

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.spc_dir = self.cwd / ".hath0r" / "spc"

    # ------------------------------------------------------------------ config
    def settings(self) -> Dict[str, Any]:
        cfg = dict(DEFAULT_CAPABILITY)
        t_path = self.cwd / "thresholds.json"
        if t_path.is_file():
            try:
                loaded = json.loads(t_path.read_text(encoding="utf-8"))
                cfg.update(loaded.get("capability") or {})
            except (OSError, json.JSONDecodeError):
                pass
        if cfg.get("mode") not in CAPABILITY_MODES:
            cfg["mode"] = "warn"
        return cfg

    def _current_fingerprint(self) -> Optional[str]:
        try:
            from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot, judge_fingerprint

            return judge_fingerprint(TaskEvaluatorBot(cwd=self.cwd).load_config())
        except Exception:  # without a fingerprint every point is from an unknown gauge
            return None

    def _eval_lsl(self) -> float:
        from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

        return float(TaskEvaluatorBot(cwd=self.cwd).load_config().get("thresholds", {}).get("min_reward", 0.8))

    # ------------------------------------------------------------------ data
    def series(self, metric: str, all_gauges: bool = False) -> List[Dict[str, Any]]:
        """Return ``[{"t", "value", "id"}]`` for a metric, oldest first.

        Eval metrics only include scorecards whose ``judge.fingerprint`` matches the current judge,
        unless ``all_gauges`` is set (#608).
        """
        if metric not in METRICS:
            raise ValueError(f"unknown metric '{metric}'. Choose one of: {', '.join(METRICS)}")
        points: List[Dict[str, Any]] = []
        if metric in EVAL_METRICS:
            hist = self.cwd / ".hath0r" / "evals" / "history"
            fingerprint = None if all_gauges else self._current_fingerprint()
            for f in sorted(hist.glob("*.json")) if hist.is_dir() else []:
                try:
                    card = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if not all_gauges and (card.get("judge") or {}).get("fingerprint") != fingerprint:
                    continue
                v = _dig(card, EVAL_METRICS[metric])
                if v is not None:
                    points.append({"t": str(card.get("evaluated_at", "")), "value": v, "id": card.get("eval_id", f.stem)})
        else:
            for rel in TOKEN_LEDGERS:
                path = self.cwd / rel
                if not path.is_file():
                    continue
                for line in path.read_text(encoding="utf-8").splitlines():
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    v = _dig(rec, (metric,))
                    if v is not None:
                        points.append({"t": str(rec.get("timestamp", "")), "value": v, "id": rec.get("id")})
        points.sort(key=lambda p: p["t"])
        return points

    # --------------------------------------------------------------- baseline
    def _baselines(self) -> Dict[str, Any]:
        path = self.spc_dir / "baselines.json"
        if path.is_file():
            try:
                return dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _write(self, name: str, payload: Dict[str, Any]) -> Path:
        self.spc_dir.mkdir(parents=True, exist_ok=True)
        target = self.spc_dir / name
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, target)
        return target

    def baseline(
        self, metric: str = "r_task", points: Optional[int] = None, recent: bool = False, dry_run: bool = False
    ) -> Dict[str, Any]:
        """Freeze phase 1 control limits from the first (or, with ``recent``, the last) ``points`` observations.

        Use ``recent`` after a deliberate process change (for example the Tier 4 clamp going off) so the
        limits describe the process as it runs now.
        """
        cfg = self.settings()
        n = int(points or cfg["baseline_points"])
        pts = self.series(metric)
        if recent:
            pts = pts[-n:]
        values = [p["value"] for p in pts]
        if len(values) < 2:
            return {"success": False, "metric": metric, "error": f"need at least 2 points, have {len(values)}"}
        base = baseline(values, points=n)
        base.update(
            {
                "metric": metric,
                "frozen_at": datetime.now(timezone.utc).isoformat(),
                "window": "recent" if recent else "first",
                "from_id": pts[0]["id"],
                "to_id": pts[min(n, len(pts)) - 1]["id"],
            }
        )
        if not dry_run:
            all_b = self._baselines()
            all_b[metric] = base
            self._write("baselines.json", all_b)
        return {"success": True, **base, "warning": None if base["sufficient"] else f"only {base['points']} points; limits are provisional"}

    # ------------------------------------------------------------------ charts
    def chart(self, metric: str = "r_task", lam: Optional[float] = None) -> Dict[str, Any]:
        cfg = self.settings()
        pts = self.series(metric)
        values = [p["value"] for p in pts]
        frozen = self._baselines().get(metric)
        n_base = int(cfg["baseline_points"])
        goal = None
        if metric == "r_task":
            from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

            goal = float(TaskEvaluatorBot(cwd=self.cwd).load_config().get("goal", {}).get("r_task", 1.0))
        res = chart(values, baseline_points=n_base, lam=float(lam if lam is not None else cfg["ewma_lambda"]), goal=goal, frozen=frozen)
        res.update({"metric": metric, "points": pts, "baseline_frozen": bool(frozen), "schema_version": "hath0r.spc.chart/v1"})
        return {"success": True, **res}

    def capability(self, metric: str = "r_task", lsl: Optional[float] = None, usl: Optional[float] = None) -> Dict[str, Any]:
        values = [p["value"] for p in self.series(metric)]
        if lsl is None and usl is None:
            if metric != "r_task":
                return {"success": False, "metric": metric, "error": "give --lsl and/or --usl for this metric"}
            lsl = self._eval_lsl()
        res = capability(values, lsl=lsl, usl=usl)
        cfg = self.settings()
        res.update({"metric": metric, "min_cpk_warn": cfg["min_cpk_warn"]})
        cpk = res.get("cpk")
        res["capable"] = cpk is not None and cpk >= float(cfg["min_cpk_warn"])
        return {"success": True, **res}

    # ------------------------------------------------------------------ status
    def status(self, metrics: Optional[List[str]] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Summarize every metric; warnings in ``warn`` mode, blocking failures in ``block`` mode."""
        cfg = self.settings()
        summary: Dict[str, Any] = {}
        warnings: List[str] = []
        # Warnings backed by a sufficient baseline; in ``auto`` mode only these block.
        established: List[str] = []
        n_base = int(cfg["baseline_points"])
        for m in metrics or list(METRICS):
            c = self.chart(m)
            if c.get("n", 0) < 2:
                summary[m] = {"status": "insufficient_data", "n": c.get("n", 0)}
                continue
            summary[m] = {
                "status": c["status"],
                "n": c["n"],
                "center": round(c["baseline"]["center"], 6),
                "ucl": round(c["baseline"]["ucl"], 6),
                "lcl": round(c["baseline"]["lcl"], 6),
                "latest": c["latest"],
                "signals": len(c["signal_indices"]),
                "last_signal_index": c["signal_indices"][-1] if c["signal_indices"] else None,
            }
            if c["signal_indices"]:
                msg = f"{m}: {len(c['signal_indices'])} out-of-control signal(s), latest at point {c['signal_indices'][-1] + 1} of {c['n']}"
                warnings.append(msg)
                if c["baseline"].get("sufficient"):
                    established.append(msg)
        cap = self.capability("r_task")
        if cap.get("n", 0) >= 2 and not cap["capable"]:
            msg = f"r_task Cpk {cap['cpk']:.2f} is below {cfg['min_cpk_warn']} against LSL {cap['lsl']}"
            warnings.append(msg)
            if cap.get("n", 0) >= n_base:
                established.append(msg)
        blocking = bool(warnings) if cfg["mode"] == "block" else (cfg["mode"] == "auto" and bool(established))
        out: Dict[str, Any] = {
            "schema_version": "hath0r.spc.status/v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": cfg["mode"],
            "metrics": summary,
            "capability": {k: cap.get(k) for k in ("n", "mean", "lsl", "usl", "cp", "cpk", "pp", "ppk", "capable", "min_cpk_warn")},
            "warnings": warnings,
            "blocking_warnings": warnings if cfg["mode"] == "block" else (established if cfg["mode"] == "auto" else []),
            "blocking": blocking,
        }
        if not dry_run:
            self._write("latest.json", out)
        return {"success": not blocking, **out}

    def gate(self) -> Dict[str, Any]:
        """Workflow step: never fails in ``warn`` mode; fails on any signal in ``block`` mode, and in ``auto``
        mode on signals backed by a sufficient same-gauge baseline."""
        res = self.status()
        if res["blocking"]:
            try:
                from hath0r_cli.bots.andon_bot import AndonBot

                AndonBot(cwd=self.cwd).raise_event(
                    source="spc-monitor-bot", severity="stop", reason="; ".join(res["blocking_warnings"]), details={"mode": res["mode"]}
                )
            except Exception as exc:  # andon is best-effort; the gate result is the record
                res.setdefault("andon_error", str(exc))
        return res
