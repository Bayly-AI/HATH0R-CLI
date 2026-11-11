"""MeasurementSystemBot: Gage R&R study of the Hath0r eval pipeline (WS1, #584).

The bot treats ``TaskEvaluatorBot`` as a gauge. It replays a fixed panel of parts (small fixture
repositories with a known-good or seeded-defect change) through the canonical ``hath0r evals``
pipeline, several times per judge configuration (operator), and reports:

* repeatability, reproducibility, %GRR and number of distinct categories (ndc) on ``R_task``
* attribute agreement on the pass/fail verdict, so every seeded defect is proven to fail

Validated targets (2026-11-11): %GRR <= 10%, ndc >= 5, zero missed defects. Anything else is a
failed study, and scorecards carry ``measurement_qualified: false`` until a study passes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from hath0r_cli.qa.msa import DEFAULT_TARGETS, attribute_agreement, gage_rr_anova

Measurement = Dict[str, Any]
MeasureFn = Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any], int], Measurement]

DEFAULT_PANEL = Path("cfg") / "evals" / "msa-panel.yaml"


def _git(cwd: Path, *args: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "hath0r-msa",
        "GIT_AUTHOR_EMAIL": "msa@hath0r.local",
        "GIT_COMMITTER_NAME": "hath0r-msa",
        "GIT_COMMITTER_EMAIL": "msa@hath0r.local",
    }
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env)


@dataclass
class MeasurementSystemBot:
    """Runs and reports Gage R&R studies against the canonical eval pipeline."""

    cwd: Path = field(default_factory=Path.cwd)

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.msa_dir = self.cwd / ".hath0r" / "evals" / "msa"

    # ------------------------------------------------------------------ panel
    def load_panel(self, panel_path: Optional[Path] = None) -> Dict[str, Any]:
        """Load and validate the MSA panel definition."""
        path = Path(panel_path) if panel_path else self.cwd / DEFAULT_PANEL
        if not path.is_absolute():
            path = self.cwd / path
        if not path.is_file():
            raise FileNotFoundError(f"MSA panel not found: {path}")
        panel = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        parts = panel.get("parts") or []
        if len(parts) < 2:
            raise ValueError("an MSA panel needs at least 2 parts")
        ids = [str(p.get("id")) for p in parts]
        if len(set(ids)) != len(ids):
            raise ValueError("MSA panel part ids must be unique")
        for p in parts:
            if p.get("expected") not in ("pass", "fail"):
                raise ValueError(f"part '{p.get('id')}' needs expected: pass|fail")
        if not any(p["expected"] == "fail" for p in parts):
            raise ValueError("an MSA panel needs at least one seeded defect (expected: fail)")
        panel.setdefault("operators", [{"id": "operator-a"}, {"id": "operator-b"}])
        root = Path(panel.get("fixtures_root", "msa-fixtures"))
        panel["_fixtures_root"] = root if root.is_absolute() else path.parent / root
        panel["_path"] = str(path)
        return panel

    # ---------------------------------------------------------------- measure
    def _prepare_workspace(self, panel: Dict[str, Any], part: Dict[str, Any], operator: Dict[str, Any], ws: Path) -> None:
        root: Path = panel["_fixtures_root"]
        base = root / str(part.get("base", "base"))
        if not base.is_dir():
            raise FileNotFoundError(f"fixture base not found: {base}")
        shutil.copytree(base, ws, dirs_exist_ok=True)

        # The gauge under study is this repository's eval configuration plus the operator's overrides.
        eval_cfg: Dict[str, Any] = {}
        own_cfg = self.cwd / "cfg" / "evals" / "task-eval.json"
        if own_cfg.is_file():
            eval_cfg = json.loads(own_cfg.read_text(encoding="utf-8"))
        for section, values in (operator.get("config") or {}).items():
            if isinstance(values, dict):
                eval_cfg.setdefault(section, {}).update(values)
            else:
                eval_cfg[section] = values
        (ws / "cfg" / "evals").mkdir(parents=True, exist_ok=True)
        (ws / "cfg" / "evals" / "task-eval.json").write_text(json.dumps(eval_cfg, indent=2), encoding="utf-8")

        _git(ws, "init", "-q", "-b", "development")
        _git(ws, "add", "-A")
        _git(ws, "commit", "-q", "-m", "msa fixture base")
        _git(ws, "checkout", "-q", "-b", f"feature/1-{part['id']}")

        from hath0r_cli.bots.memory_manager import MemoryManagerBot

        mbot = MemoryManagerBot(cwd=ws)
        mbot.init_memory()
        focus = str(part.get("focus") or part["id"])
        mbot.session_start(focus=focus, task_id=str(part["id"]))
        mbot.session_write(summary=focus, focus=focus)
        mbot.compound_memory(
            node_id=f"episode:{part['id']}",
            node_type="episode",
            label=focus,
            content=str(part.get("description") or focus),
            tags=["msa", str(part["id"])],
        )
        mbot.sync_file_hashes(dry_run=False)

        change = part.get("change")
        if change:
            src = root / str(change)
            if not src.is_dir():
                raise FileNotFoundError(f"fixture change not found: {src}")
            shutil.copytree(src, ws, dirs_exist_ok=True)

    def canonical_measure(self, panel: Dict[str, Any], part: Dict[str, Any], operator: Dict[str, Any], replicate: int) -> Measurement:
        """Measure one part once with the canonical ``TaskEvaluatorBot`` pipeline in a fresh workspace."""
        from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

        tmp = Path(tempfile.mkdtemp(prefix="hath0r-msa-"))
        ws = tmp / "repo"
        try:
            self._prepare_workspace(panel, part, operator, ws)
            res = TaskEvaluatorBot(cwd=ws).evaluate_task(
                task_id=str(part["id"]),
                compound_node=False,
                sync_observability=False,
            )
            return {
                "r_task": float(res["r_task"]),
                "passed": bool(res["passed_gate"]),
                "tier_scores": res.get("tier_scores", {}),
                "blocking_reasons": res.get("blocking_reasons", []),
                "judge_fingerprint": (res.get("judge") or {}).get("fingerprint"),
            }
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ------------------------------------------------------------------ study
    def run_study(
        self,
        *,
        panel_path: Optional[Path] = None,
        replicates: int = 3,
        measure: Optional[MeasureFn] = None,
        targets: Optional[Dict[str, float]] = None,
        dry_run: bool = False,
        compound: bool = True,
    ) -> Dict[str, Any]:
        """Run a crossed Gage R&R study and persist ``.hath0r/evals/msa/<study_id>.json``."""
        if replicates < 2:
            raise ValueError("a Gage R&R study needs at least 2 replicates")
        panel = self.load_panel(panel_path)
        measure_fn = measure or self.canonical_measure
        tgt = dict(DEFAULT_TARGETS)
        tgt.update(panel.get("targets") or {})
        tgt.update(targets or {})

        from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot, judge_fingerprint

        fingerprint = judge_fingerprint(TaskEvaluatorBot(cwd=self.cwd).load_config())
        rows: List[Dict[str, Any]] = []
        verdicts: List[Dict[str, Any]] = []
        raw: List[Dict[str, Any]] = []
        for part in panel["parts"]:
            for operator in panel["operators"]:
                for rep in range(1, replicates + 1):
                    m = measure_fn(panel, part, operator, rep)
                    rows.append({"part": part["id"], "operator": operator["id"], "value": m["r_task"]})
                    verdicts.append({"part": part["id"], "expected": part["expected"], "passed": m["passed"]})
                    raw.append({"part": part["id"], "operator": operator["id"], "replicate": rep, **m})

        grr = gage_rr_anova(rows, targets=tgt)
        agreement = attribute_agreement(verdicts)
        failures = list(grr["failures"]) + list(agreement["failures"])
        study_id = f"msa-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        study: Dict[str, Any] = {
            "schema_version": "hath0r.evals.msa-study/v1",
            "study_id": study_id,
            "run_at": datetime.now(timezone.utc).isoformat(),
            "panel": panel["_path"],
            "parts": len(panel["parts"]),
            "operators": [o["id"] for o in panel["operators"]],
            "replicates": replicates,
            "judge_fingerprint": fingerprint,
            "targets": tgt,
            "gage_rr": grr,
            "attribute_agreement": agreement,
            "passed": not failures,
            "failures": failures,
            "measurements": raw,
        }
        if not dry_run:
            self.msa_dir.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(study, indent=2, default=str)
            for target in (self.msa_dir / f"{study_id}.json", self.msa_dir / "latest.json"):
                tmp = target.with_suffix(".tmp")
                tmp.write_text(payload, encoding="utf-8")
                os.replace(tmp, target)
            if compound:
                self._compound(study)
        return {**study, "success": bool(study["passed"])}

    def _compound(self, study: Dict[str, Any]) -> None:
        try:
            from hath0r_cli.bots.memory_manager import MemoryManagerBot

            g = study["gage_rr"]
            MemoryManagerBot(cwd=self.cwd).compound_memory(
                node_id=f"msa:{study['study_id']}",
                node_type="fact",
                label=f"Gage R&R {study['study_id']} ({'PASS' if study['passed'] else 'FAIL'})",
                content=(
                    f"Eval gauge study: %GRR={g['grr_pct']}%, ndc={g['ndc']}, "
                    f"missed defects={study['attribute_agreement']['missed_defects']}, "
                    f"judge={study['judge_fingerprint']}."
                ),
                tags=["msa", "cr-task-eval-001", "passed" if study["passed"] else "failed"],
                source_files=[".hath0r/evals/msa/latest.json"],
            )
        except Exception as exc:  # memory is best-effort; the study file is the record
            study.setdefault("warnings", []).append(f"memory compounding failed: {exc}")

    def report(self) -> Dict[str, Any]:
        """Return the latest study without the raw measurements."""
        latest = self.msa_dir / "latest.json"
        if not latest.is_file():
            return {"success": False, "exists": False, "message": "No MSA study yet. Run 'hath0r evals msa run'."}
        study = json.loads(latest.read_text(encoding="utf-8"))
        study.pop("measurements", None)
        from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

        study["qualified_now"] = TaskEvaluatorBot(cwd=self.cwd).measurement_status()
        return {"success": True, "exists": True, **study}

    def status(self) -> Dict[str, Any]:
        rep = self.report()
        return {"success": True, "bot_id": "measurement-system-bot", "has_study": rep.get("exists", False)}
