"""FMEA scoring: risk priority number and an AIAG-VDA style action priority.

Severity (S), occurrence (O) and detection (D) are rated 1-10. The action priority below is a
simplified, documented reading of the AIAG-VDA (2019) AP table: severity dominates, then
occurrence, then detection. It is deterministic so ranks are reproducible across runs.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

AP_ORDER = {"H": 3, "M": 2, "L": 1}


def _check(name: str, value: int) -> int:
    v = int(value)
    if not 1 <= v <= 10:
        raise ValueError(f"{name} must be an integer from 1 to 10, got {value}")
    return v


def action_priority(severity: int, occurrence: int, detection: int) -> str:
    """Return ``H``, ``M`` or ``L``."""
    s = _check("severity", severity)
    o = _check("occurrence", occurrence)
    d = _check("detection", detection)
    if s >= 9:
        if o >= 4 or (o >= 2 and d >= 7):
            return "H"
        return "M" if o >= 2 or d >= 7 else "L"
    if s >= 7:
        if o >= 6 or (o >= 4 and d >= 7):
            return "H"
        return "M" if o >= 4 or d >= 7 else "L"
    if s >= 4:
        if o >= 8 and d >= 5:
            return "H"
        return "M" if o >= 6 or (o >= 4 and d >= 7) else "L"
    return "M" if o >= 8 and d >= 7 else "L"


def score_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the row with ``rpn`` and ``action_priority`` filled in."""
    s = _check("severity", row["severity"])
    o = _check("occurrence", row["occurrence"])
    d = _check("detection", row["detection"])
    out = dict(row)
    out["rpn"] = s * o * d
    out["action_priority"] = action_priority(s, o, d)
    return out


def rank_key(row: Mapping[str, Any]) -> tuple[int, int, int]:
    """Sort key: action priority, then severity, then RPN (all descending)."""
    return (-AP_ORDER[str(row["action_priority"])], -int(row["severity"]), -int(row["rpn"]))


def occurrence_from_rate(failure_rate: float) -> int:
    """Map an observed failure rate (0-1) to an occurrence rating on a log-like scale."""
    r = max(0.0, float(failure_rate))
    bands = [(0.5, 10), (0.33, 9), (0.2, 8), (0.1, 7), (0.05, 6), (0.02, 5), (0.01, 4), (0.002, 3), (0.0001, 2)]
    for limit, rating in bands:
        if r >= limit:
            return rating
    return 1
