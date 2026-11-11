"""Sequential design of experiments: screening designs, main-effects ANOVA and quadratic RSM.

Designs use coded units (-1, 0, +1, +/- alpha). ``decode`` maps them to natural units from each
factor's ``[low, high]`` range. ``main_effects_anova`` works for any number of levels, so it
analyses both 2-level fractions and Taguchi arrays (the screening step stays in ``TaguchiBot``).
"""

from __future__ import annotations

import itertools
import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from hath0r_cli.qa.stats import f_sf, least_squares, mean, solve_linear

# Standard minimum-aberration generators (Montgomery, Design and Analysis of Experiments, table 8.14).
FRACTION_GENERATORS: Dict[tuple[int, int], List[str]] = {
    (3, 1): ["AB"],
    (4, 1): ["ABC"],
    (5, 1): ["ABCD"],
    (5, 2): ["AB", "AC"],
    (6, 1): ["ABCDE"],
    (6, 2): ["ABC", "BCD"],
    (6, 3): ["AB", "AC", "BC"],
    (7, 1): ["ABCDEF"],
    (7, 2): ["ABCD", "ABDE"],
    (7, 3): ["ABC", "BCD", "ACD"],
    (7, 4): ["AB", "AC", "BC", "ABC"],
}


def fractional_factorial(factors: Sequence[str], fraction: int = 0) -> List[Dict[str, int]]:
    """2^(k-p) design in standard order; ``fraction`` is p (0 = full factorial)."""
    k = len(factors)
    if k < 2:
        raise ValueError("a factorial design needs at least 2 factors")
    if fraction < 0 or fraction >= k:
        raise ValueError("fraction p must satisfy 0 <= p < k")
    base_k = k - fraction
    gens: List[str] = []
    if fraction:
        if (k, fraction) not in FRACTION_GENERATORS:
            raise ValueError(f"no standard generators for a 2^({k}-{fraction}) design")
        gens = FRACTION_GENERATORS[(k, fraction)]
    letters = "ABCDEFGHIJ"
    runs: List[Dict[str, int]] = []
    for combo in itertools.product((-1, 1), repeat=base_k):
        levels = list(reversed(combo))  # standard (Yates) order: first factor alternates fastest
        coded = {letters[i]: levels[i] for i in range(base_k)}
        for g in gens:
            coded[letters[len(coded)]] = math.prod(coded[ch] for ch in g)
        runs.append({factors[i]: coded[letters[i]] for i in range(k)})
    return runs


def central_composite(factors: Sequence[str], *, center_points: int = 4, alpha: Optional[float] = None) -> List[Dict[str, float]]:
    """Rotatable central composite design (alpha = (2^k)^(1/4) unless given)."""
    k = len(factors)
    if k < 2:
        raise ValueError("a central composite design needs at least 2 factors")
    a = alpha if alpha is not None else (2**k) ** 0.25
    runs: List[Dict[str, float]] = [dict(r) for r in fractional_factorial(factors)]  # type: ignore[misc]
    for f in factors:
        for sign in (-1, 1):
            runs.append({g: (sign * a if g == f else 0.0) for g in factors})
    runs.extend({f: 0.0 for f in factors} for _ in range(center_points))
    return runs


def box_behnken(factors: Sequence[str], *, center_points: int = 3) -> List[Dict[str, float]]:
    """Box-Behnken design for 3 or more factors (edge midpoints plus centre points)."""
    k = len(factors)
    if k < 3:
        raise ValueError("a Box-Behnken design needs at least 3 factors")
    runs: List[Dict[str, float]] = []
    for i, j in itertools.combinations(range(k), 2):
        for si, sj in itertools.product((-1, 1), repeat=2):
            run = {f: 0.0 for f in factors}
            run[factors[i]], run[factors[j]] = float(si), float(sj)
            runs.append(run)
    runs.extend({f: 0.0 for f in factors} for _ in range(center_points))
    return runs


def decode(run: Mapping[str, float], ranges: Mapping[str, Sequence[float]]) -> Dict[str, float]:
    """Map coded values to natural units using each factor's ``[low, high]``."""
    out: Dict[str, float] = {}
    for f, c in run.items():
        lo, hi = float(ranges[f][0]), float(ranges[f][1])
        out[f] = (lo + hi) / 2.0 + float(c) * (hi - lo) / 2.0
    return out


def encode(point: Mapping[str, float], ranges: Mapping[str, Sequence[float]]) -> Dict[str, float]:
    """Map natural units back to coded units."""
    out: Dict[str, float] = {}
    for f, v in point.items():
        lo, hi = float(ranges[f][0]), float(ranges[f][1])
        out[f] = (float(v) - (lo + hi) / 2.0) / ((hi - lo) / 2.0)
    return out


def main_effects_anova(
    runs: Sequence[Mapping[str, Any]],
    responses: Sequence[Sequence[float]],
    *,
    alpha: float = 0.05,
) -> Dict[str, Any]:
    """Main-effects ANOVA with pure error from replicates; any number of levels per factor."""
    if len(runs) != len(responses) or not runs:
        raise ValueError("runs and responses must be non-empty and the same length")
    reps = {len(r) for r in responses}
    if min(reps) < 2:
        raise ValueError("every run needs at least 2 replicates to estimate pure error")
    all_y = [y for ys in responses for y in ys]
    grand = mean(all_y)
    ss_err = sum((y - mean(ys)) ** 2 for ys in responses for y in ys)
    df_err = sum(len(ys) - 1 for ys in responses)
    ms_err = ss_err / df_err
    factors = [f for f in runs[0] if f != "run_id"]
    results: Dict[str, Any] = {}
    for f in factors:
        groups: Dict[Any, List[float]] = {}
        for run, ys in zip(runs, responses):
            groups.setdefault(run[f], []).extend(ys)
        if len(groups) < 2:
            continue
        ss = sum(len(v) * (mean(v) - grand) ** 2 for v in groups.values())
        df = len(groups) - 1
        f_val = (ss / df) / ms_err if ms_err > 0 else math.inf if ss > 0 else 0.0
        p = f_sf(f_val, df, df_err) if df_err > 0 else None
        level_means = {str(k): round(mean(v), 6) for k, v in groups.items()}
        results[f] = {
            "ss": ss,
            "df": df,
            "f": f_val,
            "p_value": p,
            "significant": p is not None and p < alpha,
            "level_means": level_means,
        }
    return {
        "grand_mean": grand,
        "error": {"ss": ss_err, "df": df_err, "ms": ms_err},
        "alpha": alpha,
        "factors": results,
        "significant_factors": [f for f, r in results.items() if r["significant"]],
    }


def _quad_terms(x: Sequence[float]) -> List[float]:
    k = len(x)
    row = [1.0] + list(x) + [v * v for v in x]
    row += [x[i] * x[j] for i in range(k) for j in range(i + 1, k)]
    return row


def fit_quadratic(runs: Sequence[Mapping[str, float]], y: Sequence[float], factors: Sequence[str]) -> Dict[str, Any]:
    """Fit y = b0 + sum(bi xi) + sum(bii xi^2) + sum(bij xi xj) in coded units."""
    xs = [[float(r[f]) for f in factors] for r in runs]
    rows = [_quad_terms(x) for x in xs]
    if len(rows) <= len(rows[0]):
        raise ValueError(f"a quadratic model in {len(factors)} factors needs more than {len(rows[0])} runs")
    beta = least_squares(rows, list(y))
    fitted = [sum(b * t for b, t in zip(beta, row)) for row in rows]
    resid = [yy - ff for yy, ff in zip(y, fitted)]
    df_res = len(rows) - len(beta)
    sigma = math.sqrt(sum(e * e for e in resid) / df_res) if df_res > 0 else 0.0
    ss_tot = sum((yy - mean(list(y))) ** 2 for yy in y)
    r2 = 1.0 - sum(e * e for e in resid) / ss_tot if ss_tot > 0 else 1.0
    return {"factors": list(factors), "coefficients": beta, "sigma": sigma, "r_squared": r2, "df_residual": df_res}


def predict(model: Mapping[str, Any], coded: Mapping[str, float]) -> float:
    x = [float(coded[f]) for f in model["factors"]]
    return float(sum(float(b) * t for b, t in zip(model["coefficients"], _quad_terms(x))))


def optimize_quadratic(model: Mapping[str, Any], *, goal: str = "maximize", bound: float = 1.0) -> Dict[str, Any]:
    """Best predicted point inside the coded cube [-bound, bound]^k.

    Tries the stationary point first; otherwise searches a grid (21 levels per factor for up to
    3 factors, 9 levels beyond that).
    """
    if goal not in ("maximize", "minimize"):
        raise ValueError("goal must be 'maximize' or 'minimize'")
    factors = list(model["factors"])
    k = len(factors)
    b = model["coefficients"]
    lin = b[1 : 1 + k]
    sq = b[1 + k : 1 + 2 * k]
    cross = b[1 + 2 * k :]
    hess = [[0.0] * k for _ in range(k)]
    idx = 0
    for i in range(k):
        hess[i][i] = 2 * sq[i]
        for j in range(i + 1, k):
            hess[i][j] = hess[j][i] = cross[idx]
            idx += 1
    sign = 1 if goal == "maximize" else -1
    candidates: List[Dict[str, float]] = []
    try:
        stat = solve_linear(hess, [-v for v in lin])
        if all(abs(v) <= bound + 1e-9 for v in stat):
            candidates.append({f: stat[i] for i, f in enumerate(factors)})
    except ValueError:
        pass
    steps = 21 if k <= 3 else 9
    grid = [(-bound + 2 * bound * i / (steps - 1)) for i in range(steps)]
    for combo in itertools.product(grid, repeat=k):
        candidates.append({f: combo[i] for i, f in enumerate(factors)})
    best = max(candidates, key=lambda c: sign * predict(model, c))
    return {"goal": goal, "coded": best, "predicted": predict(model, best)}


def confirmation(
    model: Mapping[str, Any],
    coded: Mapping[str, float],
    observed: Sequence[float],
    *,
    z: float = 2.0,
) -> Dict[str, Any]:
    """Check a confirmation run against the predicted mean +/- z * residual sigma (approx. 95%)."""
    if not observed:
        raise ValueError("a confirmation run needs at least one observation")
    pred = predict(model, coded)
    half = z * float(model.get("sigma", 0.0))
    obs = mean(list(observed))
    return {
        "predicted": pred,
        "interval": [pred - half, pred + half],
        "observed_mean": obs,
        "confirmed": (pred - half) <= obs <= (pred + half) if half > 0 else math.isclose(obs, pred, rel_tol=1e-6),
    }
