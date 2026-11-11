"""Clarification signal for FMEA EOT-07 / PL-07 ("fails to ask for clarification").

``has_acceptance_criteria`` decides whether an issue body states what done looks like: an
``Acceptance`` heading (or ``Acceptance Criteria:`` label) followed by at least one bullet or
checkbox. ``record`` appends one line per checked task to ``.hath0r/state/clarity/events.jsonl``,
and ``unasked_rate`` is the share of checked tasks that lacked criteria and went ahead without a
decision being raised. That rate is the FMEA occurrence signal ``clarity:unasked``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

CLARITY_LEDGER = Path(".hath0r") / "state" / "clarity" / "events.jsonl"
MIN_CLARITY_SAMPLES = 20

_HEADING = re.compile(r"^\s*(?:#{1,6}\s*|\*\*)?acceptance(?:\s+criteria)?\b.*$", re.IGNORECASE | re.MULTILINE)
_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^\s*#{1,6}\s+\S", re.MULTILINE)


def has_acceptance_criteria(body: Optional[str]) -> bool:
    """True when the body has an acceptance section with at least one listed item."""
    text = body or ""
    match = _HEADING.search(text)
    if not match:
        return False
    rest = text[match.end():]
    nxt = _NEXT_HEADING.search(rest)
    section = rest[: nxt.start()] if nxt else rest
    return bool(_ITEM.search(section))


def record(cwd: Path, *, issue_number: Optional[int], has_criteria: bool, asked: bool, decision_id: Optional[str] = None) -> None:
    path = cwd / CLARITY_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    entry: Dict[str, Any] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "issue_number": issue_number,
        "has_criteria": has_criteria,
        "asked": asked,
        "unasked": (not has_criteria) and not asked,
    }
    if decision_id:
        entry["decision_id"] = decision_id
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def unasked_rate(cwd: Path, min_samples: int = MIN_CLARITY_SAMPLES) -> Optional[float]:
    path = cwd / CLARITY_LEDGER
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
    return sum(1 for e in events if e.get("unasked")) / len(events)
