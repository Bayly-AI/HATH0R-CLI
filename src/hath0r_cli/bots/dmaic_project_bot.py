"""DMAICProjectBot: run each quality fix as a Define-Measure-Analyze-Improve-Control project (WS7, #592).

A project is tied to a GitHub issue and one CTQ metric (any ``hath0r spc`` metric). Measure takes
the SPC baseline and capability; Analyze attaches the root-cause record and Pareto; Improve marks
the point where the change landed; Control refuses to close until the CTQ chart shows at least
20 in-control points after the change. Each phase gate compounds a decision memory node.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.qa.paths import write_state_json
from hath0r_cli.qa.spc import MIN_BASELINE_POINTS, chart

PHASES = ("define", "measure", "analyze", "improve", "control", "closed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DMAICProjectBot:
    """Tracks DMAIC projects in ``.hath0r/dmaic/<issue>.json``."""

    cwd: Path = field(default_factory=Path.cwd)
    min_control_points: int = MIN_BASELINE_POINTS

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.dmaic_dir = self.cwd / ".hath0r" / "dmaic"

    def _spc(self):
        from hath0r_cli.bots.spc_monitor_bot import SPCMonitorBot

        return SPCMonitorBot(cwd=self.cwd)

    def _path(self, issue: int) -> Path:
        return self.dmaic_dir / f"{int(issue)}.json"

    def load(self, issue: int) -> Dict[str, Any]:
        path = self._path(issue)
        if not path.is_file():
            raise FileNotFoundError(f"No DMAIC project for #{issue}. Run 'hath0r dmaic start {issue} --ctq <metric>'.")
        return dict(json.loads(path.read_text(encoding="utf-8")))

    def _save(self, proj: Dict[str, Any]) -> None:
        proj["updated_at"] = _now()
        write_state_json(self.dmaic_dir, f"{int(proj['issue'])}.json", proj)

    def _gate_node(self, proj: Dict[str, Any], phase: str, note: str) -> None:
        try:
            from hath0r_cli.bots.memory_manager import MemoryManagerBot

            MemoryManagerBot(cwd=self.cwd).compound_memory(
                node_id=f"decision:dmaic:{proj['issue']}:{phase}",
                node_type="decision",
                label=f"DMAIC #{proj['issue']} entered {phase}",
                content=f"CTQ {proj['ctq']}. {note}".strip(),
                tags=["dmaic", phase, proj["ctq"]],
                source_files=[f".hath0r/dmaic/{proj['issue']}.json"],
                sync_agentgraph=False,
            )
        except Exception as exc:  # the project file is the record
            proj.setdefault("warnings", []).append(f"memory compounding failed at {phase}: {exc}")

    def _series_values(self, ctq: str) -> List[float]:
        return [p["value"] for p in self._spc().series(ctq)]

    # ----------------------------------------------------------------- phases
    def start(self, issue: int, ctq: str, problem: str = "", target: Optional[float] = None, goal: str = "maximize", compound: bool = True) -> Dict[str, Any]:
        """Define the project and take the Measure baseline from SPC."""
        if self._path(issue).is_file():
            raise FileExistsError(f"DMAIC project #{issue} already exists")
        if goal not in ("maximize", "minimize"):
            raise ValueError("goal must be maximize or minimize")
        self._spc().series(ctq)  # validates the metric name
        proj: Dict[str, Any] = {
            "schema_version": "hath0r.dmaic.project/v1",
            "issue": int(issue),
            "ctq": ctq,
            "goal": goal,
            "target": target,
            "problem": problem,
            "phase": "define",
            "phases": [{"phase": "define", "at": _now(), "note": problem}],
            "created_at": _now(),
        }
        self._save(proj)
        if compound:
            self._gate_node(proj, "define", problem)
        return self.measure(issue, compound=compound)

    def measure(self, issue: int, compound: bool = True) -> Dict[str, Any]:
        proj = self.load(issue)
        spc = self._spc()
        c = spc.chart(proj["ctq"])
        baseline: Dict[str, Any] = {"n": c.get("n", 0), "status": c.get("status")}
        if c.get("n", 0) >= 2:
            baseline.update({k: c["baseline"][k] for k in ("center", "sigma", "ucl", "lcl", "points", "sufficient")})
            baseline["mean"] = c["mean"]
        if proj["ctq"] == "r_task":
            cap = spc.capability("r_task")
            baseline["cpk"] = cap.get("cpk")
        proj["baseline"] = baseline
        self._enter(proj, "measure", f"baseline n={baseline['n']} center={baseline.get('center')}", compound)
        return {"success": True, **proj}

    def _enter(self, proj: Dict[str, Any], phase: str, note: str, compound: bool) -> None:
        if PHASES.index(phase) < PHASES.index(proj["phase"]):
            raise ValueError(f"#{proj['issue']} is already in {proj['phase']}")
        proj["phase"] = phase
        proj["phases"].append({"phase": phase, "at": _now(), "note": note})
        self._save(proj)
        if compound:
            self._gate_node(proj, phase, note)
            self._save(proj)

    def analyze(self, issue: int, compound: bool = True) -> Dict[str, Any]:
        """Attach the root-cause record (fishbone / 5 Whys) and the current Pareto."""
        from hath0r_cli.bots.root_cause_bot import RootCauseBot

        proj = self.load(issue)
        rca = RootCauseBot(cwd=self.cwd)
        rec = rca.record(issue)
        if not rec.get("whys"):
            raise ValueError(f"record a 5 Whys first: hath0r rca why {issue} --problem ... --because ... (3 to 5 times)")
        proj["analysis"] = {"root_cause": rec["whys"]["root_cause"], "category": rec["whys"]["category"], "pareto_top": rca.pareto(refresh=False).get("top")}
        self._enter(proj, "analyze", f"root cause: {rec['whys']['root_cause']}", compound)
        return {"success": True, **proj}

    def improve(self, issue: int, change: str, compound: bool = True) -> Dict[str, Any]:
        """Record the change and the CTQ data point where it landed."""
        proj = self.load(issue)
        if proj["phase"] not in ("analyze", "improve"):
            raise ValueError(f"#{issue} must pass analyze before improve (now in {proj['phase']})")
        proj["change"] = {"description": change, "at": _now(), "after_point": len(self._series_values(proj["ctq"]))}
        self._enter(proj, "improve", change, compound)
        return {"success": True, **proj}

    def control(self, issue: int) -> Dict[str, Any]:
        """Chart CTQ points after the change; ready to close with 20 or more and no signals."""
        proj = self.load(issue)
        if "change" not in proj:
            raise ValueError(f"#{issue} has no recorded change; run 'hath0r dmaic improve {issue} --change ...'")
        values = self._series_values(proj["ctq"])
        after = values[int(proj["change"]["after_point"]):]
        ctrl: Dict[str, Any] = {"points_after_change": len(after), "required": self.min_control_points}
        if len(after) >= 2:
            c = chart(after, baseline_points=self.min_control_points)
            ctrl.update({"status": c["status"], "signals": c["signal_indices"], "center": c["baseline"]["center"], "sigma": c["baseline"]["sigma"], "mean": c["mean"]})
            before = proj.get("baseline", {}).get("mean")
            if before is not None:
                delta = c["mean"] - before
                ctrl["improvement"] = delta if proj.get("goal", "maximize") == "maximize" else -delta
            if proj.get("target") is not None:
                t = float(proj["target"])
                ctrl["target_met"] = c["mean"] >= t if proj.get("goal", "maximize") == "maximize" else c["mean"] <= t
        ctrl["ready_to_close"] = len(after) >= self.min_control_points and ctrl.get("status") == "in_control"
        proj["control"] = ctrl
        if proj["phase"] == "improve":
            proj["phase"] = "control"
            proj["phases"].append({"phase": "control", "at": _now(), "note": f"{len(after)} points after change"})
        self._save(proj)
        return {"success": True, **proj}

    def close(self, issue: int, compound: bool = True) -> Dict[str, Any]:
        res = self.control(issue)
        ctrl = res["control"]
        if not ctrl["ready_to_close"]:
            why = f"{ctrl['points_after_change']} of {ctrl['required']} points after the change" if ctrl["points_after_change"] < ctrl["required"] else f"CTQ chart is {ctrl.get('status')}"
            return {"success": False, "issue": int(issue), "refused": True, "reason": f"Cannot close #{issue}: {why}.", "control": ctrl}
        proj = self.load(issue)
        self._enter(proj, "closed", f"closed in control: mean {ctrl.get('mean')}", compound)
        return {"success": True, **proj}

    def status(self, issue: Optional[int] = None) -> Dict[str, Any]:
        if issue is not None:
            return {"success": True, **self.load(issue)}
        projects = []
        for f in sorted(self.dmaic_dir.glob("*.json")) if self.dmaic_dir.is_dir() else []:
            p = json.loads(f.read_text(encoding="utf-8"))
            projects.append({k: p.get(k) for k in ("issue", "ctq", "phase", "target", "problem", "updated_at")})
        return {"success": True, "bot_id": "dmaic-project-bot", "projects": projects}
