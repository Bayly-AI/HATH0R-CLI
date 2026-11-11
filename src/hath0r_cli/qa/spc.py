"""Statistical Process Control charts and process capability.

Follows the NIST/SEMATECH e-Handbook of Statistical Methods (section 6.3):

* I-MR chart: sigma estimated as MR-bar / d2 (d2 = 1.128 for moving ranges of two)
* EWMA chart: z_i = lambda * x_i + (1 - lambda) * z_{i-1}, time-varying limits
* Tabular CUSUM: k = 0.5 sigma, h = 5 sigma
* Western Electric rules 1-4 on the individuals chart
* Cp / Cpk (within sigma) and Pp / Ppk (overall sigma), one- or two-sided specs
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

from hath0r_cli.qa.stats import mean, sample_stdev

D2_N2 = 1.128
MIN_BASELINE_POINTS = 20
CPK_CAP = 99.0


def _sigma_within(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mrs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    return mean(mrs) / D2_N2


def baseline(values: Sequence[float], *, points: int = MIN_BASELINE_POINTS) -> Dict[str, Any]:
    """Phase 1 limits from the first ``points`` observations."""
    base = list(values[:points])
    if len(base) < 2:
        raise ValueError("a baseline needs at least 2 observations")
    center = mean(base)
    sigma = _sigma_within(base)
    return {
        "points": len(base),
        "sufficient": len(base) >= MIN_BASELINE_POINTS,
        "center": center,
        "sigma": sigma,
        "ucl": center + 3 * sigma,
        "lcl": center - 3 * sigma,
    }


def western_electric(values: Sequence[float], center: float, sigma: float) -> List[Dict[str, Any]]:
    """Return rule violations as ``{"index", "rule", "description"}`` (index = last point of the run)."""
    if sigma <= 0:
        return [
            {"index": i, "rule": 1, "description": "Point differs from a zero-variation baseline"}
            for i, x in enumerate(values)
            if not math.isclose(x, center, abs_tol=1e-12)
        ]
    z = [(x - center) / sigma for x in values]
    out: List[Dict[str, Any]] = []
    for i, zi in enumerate(z):
        if abs(zi) > 3:
            out.append({"index": i, "rule": 1, "description": "One point beyond 3 sigma"})
        if i >= 2:
            w = z[i - 2 : i + 1]
            for side in (1, -1):
                if sum(1 for v in w if v * side > 2) >= 2 and zi * side > 2:
                    out.append({"index": i, "rule": 2, "description": "2 of 3 points beyond 2 sigma on one side"})
        if i >= 4:
            w = z[i - 4 : i + 1]
            for side in (1, -1):
                if sum(1 for v in w if v * side > 1) >= 4 and zi * side > 1:
                    out.append({"index": i, "rule": 3, "description": "4 of 5 points beyond 1 sigma on one side"})
        if i >= 7:
            w = z[i - 7 : i + 1]
            if all(v > 0 for v in w) or all(v < 0 for v in w):
                out.append({"index": i, "rule": 4, "description": "8 points in a row on one side of the center"})
    return out


def ewma(
    values: Sequence[float],
    *,
    center: float,
    sigma: float,
    lam: float = 0.2,
    k: float = 3.0,
) -> Dict[str, Any]:
    """EWMA statistic with exact time-varying limits; flags points outside the limits."""
    if not 0 < lam <= 1:
        raise ValueError("lambda must be in (0, 1]")
    z_prev = center
    points: List[Dict[str, Any]] = []
    signals: List[int] = []
    for i, x in enumerate(values, start=1):
        z = lam * x + (1 - lam) * z_prev
        width = k * sigma * math.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * i)))
        ucl, lcl = center + width, center - width
        out = (z > ucl or z < lcl) if sigma > 0 else not math.isclose(z, center, abs_tol=1e-12)
        if out:
            signals.append(i - 1)
        points.append({"index": i - 1, "x": x, "ewma": z, "ucl": ucl, "lcl": lcl, "signal": out})
        z_prev = z
    return {"lambda": lam, "k": k, "points": points, "signals": signals}


def cusum(
    values: Sequence[float],
    *,
    center: float,
    sigma: float,
    k_sigma: float = 0.5,
    h_sigma: float = 5.0,
) -> Dict[str, Any]:
    """Tabular CUSUM (upper and lower) with reference value k and decision interval h."""
    k, h = k_sigma * sigma, h_sigma * sigma
    c_hi = c_lo = 0.0
    points: List[Dict[str, Any]] = []
    signals: List[int] = []
    for i, x in enumerate(values):
        c_hi = max(0.0, x - (center + k) + c_hi)
        c_lo = max(0.0, (center - k) - x + c_lo)
        out = (c_hi > h or c_lo > h) if sigma > 0 else not math.isclose(x, center, abs_tol=1e-12)
        if out:
            signals.append(i)
        points.append({"index": i, "x": x, "c_plus": c_hi, "c_minus": c_lo, "signal": out})
    return {"k": k, "h": h, "points": points, "signals": signals}


def chart(
    values: Sequence[float],
    *,
    baseline_points: int = MIN_BASELINE_POINTS,
    lam: float = 0.2,
    goal: Optional[float] = None,
    frozen: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build I-MR, EWMA and CUSUM views of one metric and summarize the signals.

    ``frozen`` is a saved phase 1 baseline (``center``, ``sigma``, ``points``); without it the limits
    come from the first ``baseline_points`` observations.
    """
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return {"status": "insufficient_data", "n": len(vals), "signals": [], "in_control": None}
    if frozen:
        c, sg = float(frozen["center"]), float(frozen["sigma"])
        pts = int(frozen.get("points", MIN_BASELINE_POINTS))
        base = {"points": pts, "sufficient": pts >= MIN_BASELINE_POINTS, "center": c, "sigma": sg, "ucl": c + 3 * sg, "lcl": c - 3 * sg}
    else:
        base = baseline(vals, points=baseline_points)
    rules = western_electric(vals, base["center"], base["sigma"])
    ew = ewma(vals, center=base["center"], sigma=base["sigma"], lam=lam)
    cu = cusum(vals, center=base["center"], sigma=base["sigma"])
    signal_idx = sorted({r["index"] for r in rules} | set(ew["signals"]) | set(cu["signals"]))
    status = "in_control" if not signal_idx else "out_of_control"
    if not base["sufficient"]:
        status = f"provisional_{status}"
    out: Dict[str, Any] = {
        "status": status,
        "n": len(vals),
        "baseline": base,
        "latest": vals[-1],
        "mean": mean(vals),
        "western_electric": rules,
        "ewma": ew,
        "cusum": cu,
        "signal_indices": signal_idx,
        "in_control": not signal_idx,
    }
    if goal is not None:
        out["goal"] = goal
        out["gap_to_goal"] = goal - base["center"]
    return out


def capability(
    values: Sequence[float],
    *,
    lsl: Optional[float] = None,
    usl: Optional[float] = None,
) -> Dict[str, Any]:
    """Cp/Cpk from within sigma and Pp/Ppk from overall sigma; supports one-sided specs."""
    if lsl is None and usl is None:
        raise ValueError("capability needs at least one spec limit")
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return {"status": "insufficient_data", "n": len(vals)}
    mu = mean(vals)
    s_within = _sigma_within(vals)
    s_overall = sample_stdev(vals)

    def _idx(sigma: float) -> Dict[str, Optional[float]]:
        if sigma <= 0:
            inside = (lsl is None or mu >= lsl) and (usl is None or mu <= usl)
            v = CPK_CAP if inside else -CPK_CAP
            return {"cp": v if lsl is not None and usl is not None else None, "cpk": v}
        cpu = (usl - mu) / (3 * sigma) if usl is not None else None
        cpl = (mu - lsl) / (3 * sigma) if lsl is not None else None
        cp = (usl - lsl) / (6 * sigma) if usl is not None and lsl is not None else None
        cpk = min(x for x in (cpu, cpl) if x is not None)
        return {"cp": cp, "cpk": max(-CPK_CAP, min(CPK_CAP, cpk))}

    within, overall = _idx(s_within), _idx(s_overall)
    return {
        "n": len(vals),
        "mean": mu,
        "lsl": lsl,
        "usl": usl,
        "sigma_within": s_within,
        "sigma_overall": s_overall,
        "cp": within["cp"],
        "cpk": within["cpk"],
        "pp": overall["cp"],
        "ppk": overall["cpk"],
    }
