"""Measurement System Analysis (Gage R&R) for the Hath0r eval pipeline.

The eval pipeline is treated as a gauge: ``parts`` are tasks on a fixed panel, ``operators``
are judge configurations, and each part is measured ``r`` times by every operator.

``gage_rr_anova`` implements the AIAG crossed ANOVA method (with interaction pooling when the
part x operator interaction is not significant at alpha = 0.25). ``attribute_agreement``
compares pass/fail verdicts with each part's known truth so seeded defects are proven to fail.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from hath0r_cli.qa.stats import f_sf, least_squares, mean, sample_stdev, t_quantile, t_sf_two_sided

NDC_CAP = 100
"""Reported ndc when gauge variation is zero (a perfectly repeatable, discriminating gauge)."""

DEFAULT_TARGETS: Dict[str, float] = {"max_grr_pct": 10.0, "min_ndc": 5.0}
"""Validated targets (Ray, 2026-11-11): %GRR above 10% or ndc below 5 is a failed study."""


def _cell_means(
    data: Mapping[Tuple[str, str], List[float]],
) -> Tuple[List[str], List[str], int]:
    parts = sorted({p for p, _ in data})
    operators = sorted({o for _, o in data})
    reps = {len(v) for v in data.values()}
    if len(reps) != 1:
        raise ValueError("Gage R&R requires a balanced study: every part/operator cell needs the same replicates")
    for p in parts:
        for o in operators:
            if (p, o) not in data:
                raise ValueError(f"missing measurements for part '{p}' operator '{o}'")
    return parts, operators, reps.pop()


def gage_rr_anova(
    measurements: Iterable[Mapping[str, Any]],
    *,
    targets: Optional[Mapping[str, float]] = None,
    pool_alpha: float = 0.25,
) -> Dict[str, Any]:
    """Compute variance components, %GRR and ndc from ``{"part","operator","value"}`` rows."""
    data: Dict[Tuple[str, str], List[float]] = {}
    for row in measurements:
        key = (str(row["part"]), str(row["operator"]))
        data.setdefault(key, []).append(float(row["value"]))
    if not data:
        raise ValueError("no measurements supplied")

    parts, operators, r = _cell_means(data)
    p, o = len(parts), len(operators)
    if p < 2:
        raise ValueError("Gage R&R needs at least 2 parts")
    if r < 2:
        raise ValueError("Gage R&R needs at least 2 replicates per part/operator")

    grand = sum(sum(v) for v in data.values()) / (p * o * r)
    cell = {k: sum(v) / r for k, v in data.items()}
    part_mean = {pp: sum(cell[(pp, oo)] for oo in operators) / o for pp in parts}
    op_mean = {oo: sum(cell[(pp, oo)] for pp in parts) / p for oo in operators}

    ss_part = o * r * sum((part_mean[pp] - grand) ** 2 for pp in parts)
    ss_op = p * r * sum((op_mean[oo] - grand) ** 2 for oo in operators)
    ss_int = r * sum(
        (cell[(pp, oo)] - part_mean[pp] - op_mean[oo] + grand) ** 2 for pp in parts for oo in operators
    )
    ss_err = sum((y - cell[k]) ** 2 for k, ys in data.items() for y in ys)

    df_part, df_op, df_int, df_err = p - 1, o - 1, (p - 1) * (o - 1), p * o * (r - 1)
    ms_err = ss_err / df_err
    ms_part = ss_part / df_part
    ms_op = ss_op / df_op if df_op else 0.0
    ms_int = ss_int / df_int if df_int else 0.0

    def _p(ms_num: float, df_num: int, ms_den: float, df_den: int) -> Optional[float]:
        if not df_num:
            return None
        if ms_den <= 0:
            return 0.0 if ms_num > 0 else 1.0
        return round(f_sf(ms_num / ms_den, df_num, df_den), 6)

    p_int = _p(ms_int, df_int, ms_err, df_err)
    pooled = df_int > 0 and p_int is not None and p_int > pool_alpha
    if pooled or not df_int:
        ms_resid = (ss_int + ss_err) / (df_int + df_err)
        var_repeat = ms_resid
        var_int = 0.0
        var_op = max(0.0, (ms_op - ms_resid) / (p * r)) if df_op else 0.0
        var_part = max(0.0, (ms_part - ms_resid) / (o * r))
    else:
        var_repeat = ms_err
        var_int = max(0.0, (ms_int - ms_err) / r)
        var_op = max(0.0, (ms_op - ms_int) / (p * r)) if df_op else 0.0
        var_part = max(0.0, (ms_part - ms_int) / (o * r))

    if pooled or not df_int:
        den_ms, den_df = (ss_int + ss_err) / (df_int + df_err), df_int + df_err
    else:
        den_ms, den_df = ms_int, df_int

    var_reprod = var_op + var_int
    var_grr = var_repeat + var_reprod
    var_total = var_grr + var_part

    if var_total <= 0:
        grr_pct, ndc = 0.0, 0
        degenerate = True
    else:
        degenerate = False
        grr_pct = 100.0 * math.sqrt(var_grr / var_total)
        ndc = NDC_CAP if var_grr <= 0 else min(NDC_CAP, int(math.floor(1.41 * math.sqrt(var_part / var_grr))))

    tgt = dict(DEFAULT_TARGETS)
    tgt.update(targets or {})
    failures: List[str] = []
    if degenerate:
        failures.append("No variation at all: the panel cannot show whether the gauge discriminates")
    if grr_pct > tgt["max_grr_pct"]:
        failures.append(f"%GRR {grr_pct:.2f}% exceeds {tgt['max_grr_pct']:.1f}%")
    if ndc < tgt["min_ndc"]:
        failures.append(f"ndc {ndc} is below {int(tgt['min_ndc'])}")

    def _pct(v: float) -> float:
        return round(100.0 * math.sqrt(v / var_total), 3) if var_total > 0 else 0.0

    return {
        "parts": p,
        "operators": o,
        "replicates": r,
        "grand_mean": round(grand, 6),
        "anova": {
            "part": {"ss": ss_part, "df": df_part, "ms": ms_part, "p_value": _p(ms_part, df_part, den_ms, den_df)},
            "operator": {"ss": ss_op, "df": df_op, "ms": ms_op, "p_value": _p(ms_op, df_op, den_ms, den_df)},
            "interaction": {"ss": ss_int, "df": df_int, "ms": ms_int, "p_value": p_int, "pooled": pooled},
            "repeatability": {"ss": ss_err, "df": df_err, "ms": ms_err},
        },
        "variance_components": {
            "repeatability": var_repeat,
            "reproducibility": var_reprod,
            "operator": var_op,
            "interaction": var_int,
            "gage_rr": var_grr,
            "part_to_part": var_part,
            "total": var_total,
        },
        "study_variation_pct": {
            "repeatability": _pct(var_repeat),
            "reproducibility": _pct(var_reprod),
            "gage_rr": round(grr_pct, 3),
            "part_to_part": _pct(var_part),
        },
        "grr_pct": round(grr_pct, 3),
        "ndc": ndc,
        "targets": tgt,
        "passed": not failures,
        "failures": failures,
    }


def attribute_agreement(verdicts: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Compare pass/fail verdicts to known truth.

    Each row needs ``part``, ``expected`` (``"pass"`` or ``"fail"``) and ``passed`` (bool).
    A seeded defect that passes even once is a miss and fails the study.
    """
    rows = list(verdicts)
    if not rows:
        raise ValueError("no verdicts supplied")
    total = len(rows)
    correct = sum(1 for v in rows if bool(v["passed"]) == (str(v["expected"]) == "pass"))
    bad = [v for v in rows if str(v["expected"]) == "fail"]
    good = [v for v in rows if str(v["expected"]) == "pass"]
    misses = sorted({str(v["part"]) for v in bad if bool(v["passed"])})
    false_alarms = sorted({str(v["part"]) for v in good if not bool(v["passed"])})

    by_part: Dict[str, set[bool]] = {}
    for v in rows:
        by_part.setdefault(str(v["part"]), set()).add(bool(v["passed"]))
    inconsistent = sorted(p for p, s in by_part.items() if len(s) > 1)

    failures: List[str] = []
    if misses:
        failures.append(f"Seeded defects passed the gate: {', '.join(misses)}")
    if false_alarms:
        failures.append(f"Known-good parts failed the gate: {', '.join(false_alarms)}")
    if inconsistent:
        failures.append(f"Verdict changed between replicates for: {', '.join(inconsistent)}")

    return {
        "verdicts": total,
        "effectiveness": round(correct / total, 4),
        "miss_rate": round(sum(1 for v in bad if v["passed"]) / len(bad), 4) if bad else 0.0,
        "false_alarm_rate": round(sum(1 for v in good if not v["passed"]) / len(good), 4) if good else 0.0,
        "missed_defects": misses,
        "false_alarms": false_alarms,
        "inconsistent_parts": inconsistent,
        "passed": not failures,
        "failures": failures,
    }


# --------------------------------------------------------------------------------------------
# Linearity and bias across complexity levels (#612). Classic Gage R&R assumes the gauge behaves
# the same over the whole range of parts; these functions test that assumption per level.
# --------------------------------------------------------------------------------------------

DEFAULT_LEVEL_TARGETS: Dict[str, float] = {
    "max_level_bias": 0.02,
    "alpha": 0.05,
    "max_flip_rate": 0.05,
    "borderline_band": 0.05,
}
"""Validated 2026-11-16 (#610): a level's bias may not differ from the pooled bias by more than 0.02 R_task
with significance; the linearity slope interval must contain zero; borderline verdict flips at most 5%."""


def _level_key(level: Any) -> str:
    return str(level)


def _level_order(levels: Iterable[Any]) -> List[str]:
    def _num(v: str) -> Tuple[int, str]:
        digits = "".join(ch for ch in v if ch.isdigit())
        return (int(digits) if digits else 0, v)

    return sorted({_level_key(v) for v in levels}, key=_num)


def level_number(level: Any) -> float:
    """Numeric position of a level label such as ``L3`` or ``9`` (used as the linearity regressor)."""
    digits = "".join(ch for ch in str(level) if ch.isdigit())
    if not digits:
        raise ValueError(f"level '{level}' has no numeric position")
    return float(digits)


def gage_rr_by_stratum(
    rows: Iterable[Mapping[str, Any]],
    *,
    key: str = "level",
    targets: Optional[Mapping[str, float]] = None,
) -> Dict[str, Any]:
    """Run :func:`gage_rr_anova` within each stratum (complexity level).

    Within one level the part-to-part spread is small by construction, so ``ndc`` is reported but only
    %GRR is gated per level.
    """
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(_level_key(row[key]), []).append(row)
    out: Dict[str, Any] = {}
    for lvl in _level_order(groups):
        try:
            res = gage_rr_anova(groups[lvl], targets=targets)
            res["failures"] = [f for f in res["failures"] if f.startswith("%GRR")]
            res["passed"] = not res["failures"]
            out[lvl] = res
        except ValueError as exc:
            out[lvl] = {"passed": False, "failures": [str(exc)], "error": str(exc)}
    return out


def bias_study(
    rows: Iterable[Mapping[str, Any]],
    *,
    alpha: float = 0.05,
    max_level_bias: float = 0.02,
) -> Dict[str, Any]:
    """AIAG bias study per level.

    Each row needs ``level``, ``value`` (measured) and ``reference``. Bias = measured - reference. A
    constant offset across all levels is reported as ``pooled_bias`` (a calibration constant of a gauge
    whose scale differs from the reference scale); a level fails when its bias differs from the pooled
    bias by more than ``max_level_bias`` and that difference is significant at ``alpha``.
    """
    data = [(_level_key(r["level"]), float(r["value"]) - float(r["reference"])) for r in rows]
    if len(data) < 2:
        raise ValueError("a bias study needs at least 2 measurements")
    pooled = mean([b for _, b in data])
    by_level: Dict[str, Any] = {}
    failures: List[str] = []
    for lvl in _level_order(lv for lv, _ in data):
        vals = [b for lv, b in data if lv == lvl]
        n = len(vals)
        m = mean(vals)
        sd = sample_stdev(vals)
        se = sd / math.sqrt(n) if n > 1 else 0.0
        diff = m - pooled
        if n < 2:
            p_val: Optional[float] = None
            ci = None
        elif se == 0:
            p_val = 0.0 if abs(diff) > 1e-12 else 1.0
            ci = [m, m]
        else:
            p_val = round(t_sf_two_sided(diff / se, n - 1), 6)
            half = t_quantile(alpha, n - 1) * se
            ci = [round(m - half, 6), round(m + half, 6)]
        significant = p_val is not None and p_val < alpha
        failed = significant and abs(diff) > max_level_bias
        if failed:
            failures.append(
                f"Level {lvl} bias {m:+.4f} differs from pooled bias {pooled:+.4f} by {diff:+.4f} (p={p_val})"
            )
        by_level[lvl] = {
            "n": n,
            "bias": round(m, 6),
            "sd": round(sd, 6),
            "se": round(se, 6),
            "ci95": ci,
            "diff_from_pooled": round(diff, 6),
            "p_value": p_val,
            "significant": significant,
            "passed": not failed,
        }
    return {
        "pooled_bias": round(pooled, 6),
        "by_level": by_level,
        "max_level_bias": max_level_bias,
        "alpha": alpha,
        "passed": not failures,
        "failures": failures,
    }


def linearity_study(
    rows: Iterable[Mapping[str, Any]],
    *,
    alpha: float = 0.05,
    regressor: str = "level",
) -> Dict[str, Any]:
    """AIAG linearity: regress bias (measured - reference) on the level position (or on ``reference``).

    The study passes when the slope's confidence interval contains zero.
    """
    pts: List[Tuple[float, float]] = []
    for r in rows:
        x = level_number(r["level"]) if regressor == "level" else float(r["reference"])
        pts.append((x, float(r["value"]) - float(r["reference"])))
    n = len(pts)
    if n < 3:
        raise ValueError("a linearity study needs at least 3 measurements")
    xs = [x for x, _ in pts]
    if max(xs) == min(xs):
        raise ValueError("a linearity study needs at least 2 distinct regressor values")
    intercept, slope = least_squares([[1.0, x] for x in xs], [y for _, y in pts])
    resid = [y - (intercept + slope * x) for x, y in pts]
    df = n - 2
    s2 = sum(e * e for e in resid) / df if df > 0 else 0.0
    xbar = mean(xs)
    sxx = sum((x - xbar) ** 2 for x in xs)
    se_slope = math.sqrt(s2 / sxx) if sxx > 0 else 0.0
    se_int = math.sqrt(s2 * (1.0 / n + xbar * xbar / sxx)) if sxx > 0 else 0.0
    tcrit = t_quantile(alpha, df) if df > 0 else float("inf")
    slope_ci = [slope - tcrit * se_slope, slope + tcrit * se_slope]
    if se_slope == 0:
        p_slope = 0.0 if abs(slope) > 1e-12 else 1.0
    else:
        p_slope = t_sf_two_sided(slope / se_slope, df)
    contains_zero = slope_ci[0] <= 0.0 <= slope_ci[1]
    ss_tot = sum((y - mean([b for _, b in pts])) ** 2 for _, y in pts)
    r2 = 1.0 - (sum(e * e for e in resid) / ss_tot) if ss_tot > 0 else 0.0
    failures = [] if contains_zero else [
        f"Linearity slope {slope:+.5f} per {regressor} unit (95% CI {slope_ci[0]:+.5f} to {slope_ci[1]:+.5f}) excludes 0"
    ]
    return {
        "regressor": regressor,
        "n": n,
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "se_slope": round(se_slope, 6),
        "se_intercept": round(se_int, 6),
        "slope_ci95": [round(v, 6) for v in slope_ci],
        "p_slope": round(p_slope, 6),
        "r_squared": round(r2, 4),
        "passed": contains_zero,
        "failures": failures,
    }


def attribute_agreement_by_level(verdicts: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """:func:`attribute_agreement` within each level (rows need ``level``)."""
    groups: Dict[str, List[Mapping[str, Any]]] = {}
    for v in verdicts:
        groups.setdefault(_level_key(v["level"]), []).append(v)
    return {lvl: attribute_agreement(groups[lvl]) for lvl in _level_order(groups)}


def verdict_flip_rate(
    rows: Iterable[Mapping[str, Any]],
    *,
    threshold: float = 0.80,
    band: float = 0.05,
    max_flip_rate: float = 0.05,
) -> Dict[str, Any]:
    """Share of borderline parts whose pass/fail verdict changes across operators or replicates.

    A part is borderline when it is flagged ``borderline`` or its mean measured value lies within
    ``band`` of ``threshold``. Rows need ``part``, ``value`` and ``passed``; ``borderline`` is optional.
    """
    parts: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        p = parts.setdefault(str(r["part"]), {"values": [], "verdicts": set(), "flag": False, "level": r.get("level")})
        p["values"].append(float(r["value"]))
        p["verdicts"].add(bool(r["passed"]))
        p["flag"] = p["flag"] or bool(r.get("borderline"))
    borderline = {k: v for k, v in parts.items() if v["flag"] or abs(mean(v["values"]) - threshold) <= band}
    flipped = sorted(k for k, v in borderline.items() if len(v["verdicts"]) > 1)
    rate = len(flipped) / len(borderline) if borderline else 0.0
    failures = [f"Borderline verdict-flip rate {rate:.1%} exceeds {max_flip_rate:.0%}: {', '.join(flipped)}"] if rate > max_flip_rate else []
    return {
        "threshold": threshold,
        "band": band,
        "borderline_parts": sorted(borderline),
        "flipped_parts": flipped,
        "flip_rate": round(rate, 4),
        "max_flip_rate": max_flip_rate,
        "passed": not failures,
        "failures": failures,
    }
