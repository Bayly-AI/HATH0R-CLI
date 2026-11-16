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

from hath0r_cli.qa.msa import (
    DEFAULT_LEVEL_TARGETS,
    DEFAULT_TARGETS,
    attribute_agreement,
    attribute_agreement_by_level,
    bias_study,
    gage_rr_anova,
    gage_rr_by_stratum,
    linearity_study,
    verdict_flip_rate,
)

Measurement = Dict[str, Any]
MeasureFn = Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Any], int], Measurement]

DEFAULT_PANEL = Path("cfg") / "evals" / "msa-panel.yaml"


def variant_python(text: str) -> str:
    """Meaning-preserving rewrite of a Python module (#612 variant operator).

    Each contiguous run of top-level function definitions is emitted in reverse order, separated by
    the usual two blank lines. Functions resolve names at call time, so behaviour is unchanged;
    module-level statements keep their position.
    """
    import ast

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text
    lines = text.splitlines()
    out: List[str] = []
    cursor = 0
    body = tree.body
    i = 0
    while i < len(body):
        node = body[i]
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            i += 1
            continue
        run = [node]
        j = i + 1
        while j < len(body) and isinstance(body[j], (ast.FunctionDef, ast.AsyncFunctionDef)):
            run.append(body[j])
            j += 1
        first = run[0]
        start = (first.decorator_list[0].lineno if first.decorator_list else first.lineno) - 1
        end = run[-1].end_lineno or run[-1].lineno
        out.extend(lines[cursor:start])
        chunks = []
        for n in run:
            s0 = (n.decorator_list[0].lineno if n.decorator_list else n.lineno) - 1
            chunks.append(lines[s0 : (n.end_lineno or n.lineno)])
        for k, chunk in enumerate(reversed(chunks)):
            if k:
                out.extend(["", ""])
            out.extend(chunk)
        cursor = end
        i = j
    out.extend(lines[cursor:])
    return "\n".join(out) + "\n"


def apply_variant(change_dir: Path, ws: Path) -> List[str]:
    """Rewrite the change's files inside ``ws`` in a meaning-preserving form; returns the files changed."""
    touched: List[str] = []
    for src in sorted(p for p in change_dir.rglob("*") if p.is_file()):
        rel = src.relative_to(change_dir)
        target = ws / rel
        if not target.is_file():
            continue
        text = target.read_text(encoding="utf-8")
        if target.suffix == ".py":
            new = variant_python(text)
        elif target.suffix in (".md", ".yaml", ".yml", ".txt"):
            new = text.rstrip("\n") + "\n\n"
        else:
            continue
        if new != text:
            target.write_text(new, encoding="utf-8")
            touched.append(str(rel))
    return touched


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
            ref = p.get("reference")
            if ref is not None and (not isinstance(ref, dict) or "quality" not in ref):
                raise ValueError(f"part '{p.get('id')}' reference needs a quality value")
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
            # copy (not copy2): a fresh mtime makes git see same-size edits. With copy2 an edit that keeps
            # the file size and inherits the base file's mtime is invisible to git status/diff (#612).
            shutil.copytree(src, ws, dirs_exist_ok=True, copy_function=shutil.copy)
            if operator.get("variant"):
                apply_variant(src, ws)

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
                    level = part.get("level")
                    ref = (part.get("reference") or {}).get("quality")
                    rows.append(
                        {
                            "part": part["id"],
                            "operator": operator["id"],
                            "value": m["r_task"],
                            "level": level,
                            "reference": ref,
                            "passed": m["passed"],
                            "borderline": bool(part.get("borderline")),
                        }
                    )
                    verdicts.append({"part": part["id"], "expected": part["expected"], "passed": m["passed"], "level": level})
                    raw.append({"part": part["id"], "operator": operator["id"], "replicate": rep, **m})

        grr = gage_rr_anova(rows, targets=tgt)
        agreement = attribute_agreement(verdicts)
        failures = list(grr["failures"]) + list(agreement["failures"])
        by_level = self._level_analysis(panel, rows, verdicts, tgt) if all(p.get("level") for p in panel["parts"]) else None
        if by_level:
            failures += by_level["failures"]
        study_id = f"msa-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        study: Dict[str, Any] = {
            "schema_version": "hath0r.evals.msa-study/v2" if by_level else "hath0r.evals.msa-study/v1",
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
            "by_level": by_level,
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

    def _level_analysis(
        self,
        panel: Dict[str, Any],
        rows: List[Dict[str, Any]],
        verdicts: List[Dict[str, Any]],
        tgt: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Per-level Gage R&R, bias, linearity, attribute agreement and borderline flips (#612)."""
        lt = dict(DEFAULT_LEVEL_TARGETS)
        lt.update({k: v for k, v in tgt.items() if k in lt})
        grr = gage_rr_by_stratum(rows, targets=tgt)
        agree = attribute_agreement_by_level(verdicts)
        flips = verdict_flip_rate(
            rows,
            threshold=float(tgt.get("min_reward", 0.80)),
            band=float(lt["borderline_band"]),
            max_flip_rate=float(lt["max_flip_rate"]),
        )
        failures: List[str] = []
        for lvl, res in grr.items():
            failures += [f"Level {lvl}: {f}" for f in res.get("failures", [])]
        for lvl, res in agree.items():
            failures += [f"Level {lvl}: {f}" for f in res.get("failures", [])]
        failures += flips["failures"]
        # Bias and linearity are measured on acceptable work (expected pass). Seeded defects are judged by
        # attribute agreement; their reference quality differs by defect type, which would confound a slope.
        expected = {str(p["id"]): p["expected"] for p in panel["parts"]}
        ref_rows = [r for r in rows if r.get("reference") is not None and expected.get(str(r["part"])) == "pass"]
        all_ref = [r for r in rows if r.get("reference") is not None]
        bias = lin = lin_good = lin_all = None
        if ref_rows and len({r["level"] for r in ref_rows}) >= 2:
            bias = bias_study(ref_rows, alpha=float(lt["alpha"]), max_level_bias=float(lt["max_level_bias"]))
            lin = linearity_study(ref_rows, alpha=float(lt["alpha"]))
            good = [r for r in ref_rows if r["reference"] >= 0.9]
            lin_good = linearity_study(good, alpha=float(lt["alpha"])) if len({r["level"] for r in good}) >= 2 else None
            lin_all = linearity_study(all_ref, alpha=float(lt["alpha"]))
            failures += bias["failures"] + lin["failures"]
        return {
            "targets": lt,
            "gage_rr": {k: {kk: v.get(kk) for kk in ("grr_pct", "ndc", "parts", "passed", "failures", "variance_components", "grand_mean")} for k, v in grr.items()},
            "attribute_agreement": agree,
            "bias": bias,
            "linearity": lin,
            "linearity_known_good": lin_good,
            "linearity_all_parts_informational": lin_all,
            "verdict_flips": flips,
            "passed": not failures,
            "failures": failures,
        }

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
