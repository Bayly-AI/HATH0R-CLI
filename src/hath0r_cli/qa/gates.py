"""Verification gates for workflow steps that merge or announce (FMEA EOT-12/13, PL-12/13).

A factory step marked ``gate: verified`` only runs when the latest task evaluation passed its gate
(``hath0r evals verify``) and no Andon stop is active (``hath0r andon status``). The check fails
closed: if either check cannot run, the step is blocked.

Each gated step appends one line to ``.hath0r/state/gates/events.jsonl``. ``escape_rate`` reads that
ledger and gives the share of gated steps that ran unverified, which is the FMEA occurrence signal
``gate:escape``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

GATE_LEDGER = Path(".hath0r") / "state" / "gates" / "events.jsonl"
GATE_VERIFIED = "verified"
# Below this many gated runs the escape rate is too noisy to rate occurrence from.
MIN_GATE_SAMPLES = 20


def check_verified(cwd: Path, task_id: Optional[str] = None) -> Optional[str]:
    """Return ``None`` when the step may run, or the reason it is blocked."""
    try:
        from hath0r_cli.bots.andon_bot import AndonBot

        andon = AndonBot(cwd=cwd).status()
        if andon.get("stopped"):
            return f"andon stop active ({andon.get('active_stops', 0)} open)"
    except Exception as exc:  # fail closed
        return f"andon status unavailable: {exc}"
    try:
        from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot

        res = TaskEvaluatorBot(cwd=cwd).verify_evaluated(task_id=task_id, auto_run_if_missing=False)
    except Exception as exc:  # fail closed
        return f"evals verify unavailable: {exc}"
    if not res.get("passed_gate"):
        return res.get("error") or "latest task evaluation did not pass its gate"
    return None


def record(cwd: Path, *, workflow_id: str, step_id: str, verified: bool, ran: bool, reason: Optional[str] = None) -> None:
    """Append one gate decision. ``ran and not verified`` is an escape."""
    path = cwd / GATE_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    entry: Dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow_id,
        "step_id": step_id,
        "verified": verified,
        "ran": ran,
        "escape": ran and not verified,
    }
    if reason:
        entry["reason"] = reason
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def escape_rate(cwd: Path, min_samples: int = MIN_GATE_SAMPLES) -> Optional[float]:
    """Share of gated steps that ran unverified, or ``None`` with too few samples."""
    path = cwd / GATE_LEDGER
    if not path.is_file():
        return None
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if len(events) < min_samples:
        return None
    return sum(1 for e in events if e.get("escape")) / len(events)
