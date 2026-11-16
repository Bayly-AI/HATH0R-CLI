"""Many-Facet Rasch Model (MFRM) for LLM judge calibration (#613, epic #610).

Rating-scale model with facets part (B_n), criterion (D_i), judge (C_j) and Andrich thresholds (F_k):

    ln(P_nijk / P_nij(k-1)) = B_n - D_i - C_j - F_k

The judge x level interaction (psi_jl, "bias" in FACETS terms) is estimated in a second stage with the
main parameters held fixed, as FACETS bias/interaction analysis does:

    ln(P_nijk / P_nij(k-1)) = B_n - D_i - C_j - psi_{j,level(n)} - F_k

Positive C_j and psi mean harsher (lower ratings). Estimation is joint maximum likelihood (JMLE) with
Newton-Raphson steps per element. Standard errors for psi are reported both model-based and clustered
by part (criteria and replicates of one part are not independent). Fit is infit / outfit mean-square
with Wilson-Hilferty ZSTD. Everything is dependency-free, like ``qa/stats.py``.

Decision rules (cut-offs validated 2026-11-16, #610), applied per judge per level, first match wins:

* ``not_certified``: every rating in the cell is in one extreme category (psi not estimable)
* ``removed_noise``: infit or outfit MnSq > 1.5 at the level (with at least 30 ratings), or the judge's
  ratings alone separate parts by less than their own error (judge-alone separation G < 1, "noise
  exceeds signal"; applied only when the judge gives each part at least 6 ratings)
* ``not_certified``: clustered SE of psi > 0.10 logits, too few parts at the level, or no anchor rating
  at the level
* ``removed_bias``: psi significant after Benjamini-Hochberg (q 0.05) and abs(psi) >= 0.20 logits
* ``certified``: none of the above

Noise is checked before precision because misfit is visible from the ratings themselves, while a
bias verdict needs a precise psi.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from hath0r_cli.qa.stats import benjamini_hochberg, normal_sf_two_sided

DEFAULT_GATES: Dict[str, float] = {
    "max_se": 0.10,
    "max_mnsq": 1.5,
    "removal_psi": 0.20,
    "bh_q": 0.05,
    "min_parts_per_level": 15,
    "min_judge_separation": 1.0,
    "min_ratings_per_part_for_separation": 6,
    "min_ratings_for_fit": 30,
}
"""Validated by Ray on 2026-11-16 (#610)."""

STATUSES = ("certified", "not_certified", "removed_noise", "removed_bias")


class RaschError(ValueError):
    """The ratings cannot be fitted (bad categories, disconnected design, nothing to estimate)."""


# ------------------------------------------------------------------------------------ probabilities
def category_probs(theta: float, thresholds: Sequence[float]) -> List[float]:
    """Rating-scale category probabilities for logit ``theta`` and thresholds F_1..F_M (F_0 = 0)."""
    logits = [0.0]
    acc = 0.0
    for f in thresholds:
        acc += theta - f
        logits.append(acc)
    top = max(logits)
    ex = [math.exp(v - top) for v in logits]
    s = sum(ex)
    return [e / s for e in ex]


def _moments(probs: Sequence[float]) -> Tuple[float, float, float]:
    """Expected value, variance and 4th central moment of a category distribution."""
    e = sum(k * p for k, p in enumerate(probs))
    v = sum((k - e) ** 2 * p for k, p in enumerate(probs))
    c = sum((k - e) ** 4 * p for k, p in enumerate(probs))
    return e, v, c


# ---------------------------------------------------------------------------------------- helpers
def _validate(rows: List[Mapping[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        for key in ("part", "judge", "criterion", "rating"):
            if key not in r:
                raise RaschError(f"rating row is missing '{key}'")
        rating = r["rating"]
        if rating is None:
            continue
        if not float(rating).is_integer() or int(rating) < 0:
            raise RaschError(f"ratings must be non-negative integers, got {rating!r}")
        out.append(
            {
                "part": str(r["part"]),
                "judge": str(r["judge"]),
                "criterion": str(r["criterion"]),
                "level": str(r.get("level", "all")),
                "replicate": r.get("replicate", 1),
                "rating": int(rating),
            }
        )
    if not out:
        raise RaschError("no ratings supplied")
    m = max(r["rating"] for r in out)
    if m < 1:
        raise RaschError("only one rating category was used; nothing to estimate")
    return out, m


def check_connected(rows: Iterable[Mapping[str, Any]]) -> bool:
    """True when parts, judges and criteria form one connected network (a common scale is possible)."""
    adj: Dict[str, set] = defaultdict(set)
    for r in rows:
        nodes = (f"p:{r['part']}", f"j:{r['judge']}", f"c:{r['criterion']}")
        for a in nodes:
            for b in nodes:
                if a != b:
                    adj[a].add(b)
    if not adj:
        return False
    start = next(iter(adj))
    seen = {start}
    stack = [start]
    while stack:
        for nb in adj[stack.pop()]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return len(seen) == len(adj)


def _extreme_parts(rows: List[Dict[str, Any]], m: int) -> List[str]:
    scores: Dict[str, List[int]] = defaultdict(list)
    for r in rows:
        scores[r["part"]].append(r["rating"])
    return sorted(p for p, v in scores.items() if all(x == 0 for x in v) or all(x == m for x in v))


def _wh_zstd(mnsq: float, q: float) -> Optional[float]:
    """Wilson-Hilferty cube-root transform of a mean-square to an approximate unit normal."""
    if q <= 0 or mnsq <= 0:
        return None
    return round(float((mnsq ** (1.0 / 3.0) - 1.0) * (3.0 / q) + q / 3.0), 3)


def _fit(resid: List[Tuple[float, float, float]]) -> Dict[str, Optional[float]]:
    """Infit / outfit mean-squares and ZSTD from ``(x - E, V, C)`` triples."""
    n = len(resid)
    if n == 0:
        return {"infit": None, "outfit": None, "infit_zstd": None, "outfit_zstd": None, "n": 0}
    sum_v = sum(v for _, v, _ in resid)
    infit = sum(y * y for y, _, _ in resid) / sum_v if sum_v > 0 else None
    zs = [y * y / v for y, v, _ in resid if v > 0]
    outfit = sum(zs) / len(zs) if zs else None
    q_in = math.sqrt(max(0.0, sum(c - v * v for _, v, c in resid)) / (sum_v * sum_v)) if sum_v > 0 else 0.0
    q_out = math.sqrt(max(0.0, sum(c / (v * v) for _, v, c in resid if v > 0) / (n * n) - 1.0 / n))
    return {
        "infit": round(infit, 4) if infit is not None else None,
        "outfit": round(outfit, 4) if outfit is not None else None,
        "infit_zstd": _wh_zstd(infit, q_in) if infit is not None else None,
        "outfit_zstd": _wh_zstd(outfit, q_out) if outfit is not None else None,
        "n": n,
    }


def separation(measures: Sequence[float], ses: Sequence[float]) -> Dict[str, Optional[float]]:
    """Separation G, reliability and strata (4G + 1) / 3 for a set of measures and their SEs."""
    vals = [(m, s) for m, s in zip(measures, ses) if s is not None and math.isfinite(m)]
    if len(vals) < 2:
        return {"separation": None, "reliability": None, "strata": None, "rmse": None, "sd": None}
    mu = sum(m for m, _ in vals) / len(vals)
    sd2 = sum((m - mu) ** 2 for m, _ in vals) / (len(vals) - 1)
    rmse2 = sum(s * s for _, s in vals) / len(vals)
    true2 = max(0.0, sd2 - rmse2)
    g = math.sqrt(true2 / rmse2) if rmse2 > 0 else float("inf")
    rel = true2 / sd2 if sd2 > 0 else 0.0
    return {
        "separation": round(g, 4) if math.isfinite(g) else None,
        "reliability": round(rel, 4),
        "strata": round((4 * g + 1) / 3, 4) if math.isfinite(g) else None,
        "rmse": round(math.sqrt(rmse2), 4),
        "sd": round(math.sqrt(sd2), 4),
    }


# ---------------------------------------------------------------------------------------- the model
def fit_mfrm(
    ratings: Iterable[Mapping[str, Any]],
    *,
    max_iter: int = 500,
    tol: float = 1e-5,
    max_step: float = 1.0,
) -> Dict[str, Any]:
    """Fit the main rating-scale MFRM (parts, criteria, judges, thresholds) by JMLE.

    Rows: ``{part, level, judge, criterion, replicate, rating}``. Parts with extreme scores (all
    lowest or all highest category) have no finite JMLE measure; they are excluded from estimation
    and listed in ``extreme_parts``.
    """
    rows, m = _validate(list(ratings))
    if not check_connected(rows):
        raise RaschError("the rating design is disconnected: parts, judges and criteria do not share one scale")
    extreme = _extreme_parts(rows, m)
    est = [r for r in rows if r["part"] not in set(extreme)]
    if not est:
        raise RaschError("every part has an extreme score; nothing to estimate")
    counts = [0] * (m + 1)
    for r in est:
        counts[r["rating"]] += 1
    unused = [k for k, c in enumerate(counts) if c == 0]
    if unused and 0 < min(unused) < m:
        raise RaschError(f"rating categories {unused} were never used; collapse the scale before fitting")

    parts = sorted({r["part"] for r in est})
    crit = sorted({r["criterion"] for r in est})
    judges = sorted({r["judge"] for r in est})
    B = dict.fromkeys(parts, 0.0)
    D = dict.fromkeys(crit, 0.0)
    C = dict.fromkeys(judges, 0.0)
    F = [0.0] * m

    def theta(r: Mapping[str, Any]) -> float:
        return B[r["part"]] - D[r["criterion"]] - C[r["judge"]]

    converged = False
    it = 0
    for it in range(1, max_iter + 1):
        biggest = 0.0
        # one Newton step per facet, in turn
        for facet, params, sign in (("part", B, 1.0), ("criterion", D, -1.0), ("judge", C, -1.0)):
            score: Dict[str, float] = defaultdict(float)
            info: Dict[str, float] = defaultdict(float)
            for r in est:
                e, v, _ = _moments(category_probs(theta(r), F))
                score[r[facet]] += r["rating"] - e
                info[r[facet]] += v
            for key in params:
                if info[key] > 0:
                    step = sign * score[key] / info[key]
                    step = max(-max_step, min(max_step, step))
                    params[key] += step
                    biggest = max(biggest, abs(step))
            if facet in ("criterion", "judge"):
                mu = sum(params.values()) / len(params)
                for key in params:
                    params[key] -= mu
        # thresholds
        ge_obs = [0.0] * (m + 1)
        ge_exp = [0.0] * (m + 1)
        ge_inf = [0.0] * (m + 1)
        for r in est:
            probs = category_probs(theta(r), F)
            tail = 0.0
            for k in range(m, 0, -1):
                tail += probs[k]
                ge_exp[k] += tail
                ge_inf[k] += tail * (1 - tail)
                if r["rating"] >= k:
                    ge_obs[k] += 1
        for k in range(1, m + 1):
            if ge_inf[k] > 0:
                step = (ge_exp[k] - ge_obs[k]) / ge_inf[k]
                step = max(-max_step, min(max_step, step))
                F[k - 1] += step
                biggest = max(biggest, abs(step))
        mu_f = sum(F) / m
        F = [f - mu_f for f in F]
        if biggest < tol:
            converged = True
            break

    # standard errors and fit per element
    info_by: Dict[Tuple[str, str], float] = defaultdict(float)
    resid_by: Dict[Tuple[str, str], List[Tuple[float, float, float]]] = defaultdict(list)
    for r in est:
        e, v, c = _moments(category_probs(theta(r), F))
        for facet in ("part", "criterion", "judge"):
            info_by[(facet, r[facet])] += v
            resid_by[(facet, r[facet])].append((r["rating"] - e, v, c))
        resid_by[("all", "all")].append((r["rating"] - e, v, c))

    def _elements(facet: str, params: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for key, val in params.items():
            inf = info_by[(facet, key)]
            out[key] = {"measure": round(val, 4), "se": round(1 / math.sqrt(inf), 4) if inf > 0 else None, **_fit(resid_by[(facet, key)])}
        return out

    part_el = _elements("part", B)
    part_levels = {}
    for r in rows:
        part_levels[r["part"]] = r["level"]
    return {
        "model": "rating-scale MFRM (JMLE)",
        "categories": m + 1,
        "category_counts": counts,
        "iterations": it,
        "converged": converged,
        "n_ratings": len(est),
        "extreme_parts": extreme,
        "thresholds": [round(f, 4) for f in F],
        "parts": part_el,
        "part_levels": part_levels,
        "criteria": _elements("criterion", D),
        "judges": _elements("judge", C),
        "global_fit": _fit(resid_by[("all", "all")]),
        "part_separation": separation([v["measure"] for v in part_el.values()], [v["se"] for v in part_el.values()]),
        "_params": {"B": B, "D": D, "C": C, "F": F},
        "_rows": est,
    }


def _cell_newton(obs: List[Tuple[float, int]], F: Sequence[float], max_iter: int = 100, tol: float = 1e-6) -> float:
    """psi for one cell: ``obs`` is ``(theta without psi, rating)``; psi enters as theta - psi."""
    psi = 0.0
    for _ in range(max_iter):
        score = 0.0
        info = 0.0
        for t, x in obs:
            e, v, _ = _moments(category_probs(t - psi, F))
            score += x - e
            info += v
        if info <= 0:
            break
        step = -score / info
        step = max(-1.0, min(1.0, step))
        psi += step
        if abs(step) < tol:
            break
    return psi


def bias_interaction(fit: Mapping[str, Any], *, by: str = "level", anchors: Sequence[str] = ()) -> Dict[str, Any]:
    """Judge x ``by`` interaction (psi) with main parameters fixed (FACETS bias analysis).

    Returns one cell per judge and level with psi, model SE, part-clustered SE, z (clustered), p, fit,
    the number of ratings and distinct parts, plus each judge's swing (max psi - min psi).

    Identification: every part sits in one level, so a lean shared by *all* judges at a level is
    absorbed into that level's part measures. Without anchors, psi is relative to the panel average at
    each level. With ``anchors`` (reference judges, normally human raters), psi is re-expressed relative
    to the anchors' mean at the same level, which is the "human" reference the expert suggested; its SE
    combines both clustered SEs.
    """
    P = fit["_params"]
    B, D, C, F = P["B"], P["D"], P["C"], P["F"]
    cells: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for r in fit["_rows"]:
        cells[(r["judge"], r[by])].append(r)
    out: Dict[str, Dict[str, Any]] = {}
    top = len(F)
    for (j, lvl), obs in sorted(cells.items()):
        vals = {r["rating"] for r in obs}
        if vals <= {0} or vals <= {top}:
            # every rating in one extreme category: psi has no finite estimate
            out.setdefault(j, {})[lvl] = {
                "psi": None, "se_model": None, "se_clustered": None, "z": None, "p_value": None,
                "n_ratings": len(obs), "n_parts": len({r["part"] for r in obs}), "infit": None, "outfit": None,
                "extreme_cell": "lowest" if vals <= {0} else "highest",
            }
            continue
        base = [(B[r["part"]] - D[r["criterion"]] - C[j], r["rating"]) for r in obs]
        psi = _cell_newton(base, F)
        info = 0.0
        resid: List[Tuple[float, float, float]] = []
        by_part: Dict[str, float] = defaultdict(float)
        for (t, x), r in zip(base, obs):
            e, v, c = _moments(category_probs(t - psi, F))
            info += v
            resid.append((x - e, v, c))
            by_part[r["part"]] += x - e
        se_model = 1 / math.sqrt(info) if info > 0 else None
        g = len(by_part)
        if info > 0 and g > 1:
            meat = sum(u * u for u in by_part.values()) * g / (g - 1)
            se_cl = math.sqrt(meat) / info
            # never report a clustered SE below the model SE: clustering can only add uncertainty here
            se_cl = max(se_cl, se_model or 0.0)
        else:
            se_cl = None
        z = psi / se_cl if se_cl else None
        out.setdefault(j, {})[lvl] = {
            "psi": round(psi, 4),
            "se_model": round(se_model, 4) if se_model else None,
            "se_clustered": round(se_cl, 4) if se_cl else None,
            "z": round(z, 3) if z is not None else None,
            "p_value": round(normal_sf_two_sided(z), 6) if z is not None else None,
            "n_ratings": len(obs),
            "n_parts": g,
            **{k: v for k, v in _fit(resid).items() if k != "n"},
        }
    reference = "panel_average"
    anchor_set = [a for a in anchors if a in out]
    for a in anchor_set:
        for c in out[a].values():
            c["anchor"] = True
    if anchor_set:
        reference = "anchors:" + ",".join(anchor_set)
        for lvl in sorted({lvl for lv in out.values() for lvl in lv}):
            ref_cells = [out[a][lvl] for a in anchor_set if lvl in out[a] and out[a][lvl]["psi"] is not None]
            if not ref_cells:
                for j, lv in out.items():
                    if lvl in lv and j not in anchor_set:
                        lv[lvl]["no_anchor_reference"] = True
                continue
            ref_psi = sum(c["psi"] for c in ref_cells) / len(ref_cells)
            ref_se = math.sqrt(sum((c["se_clustered"] or 0) ** 2 for c in ref_cells)) / len(ref_cells)
            for j, lv in out.items():
                if lvl not in lv:
                    continue
                c = lv[lvl]
                c["psi_raw"] = c["psi"]
                if j in anchor_set:
                    c["anchor"] = True
                    continue
                if c["psi"] is None:
                    continue
                c["psi"] = round(c["psi"] - ref_psi, 4)
                if c["se_clustered"]:
                    c["se_clustered"] = round(math.sqrt(c["se_clustered"] ** 2 + ref_se**2), 4)
                    z = c["psi"] / c["se_clustered"]
                    c["z"] = round(z, 3)
                    c["p_value"] = round(normal_sf_two_sided(z), 6)
    swings: Dict[str, Dict[str, Any]] = {}
    for j, lv in out.items():
        finite = [(c["psi"], lvl, c["se_clustered"]) for lvl, c in lv.items() if c["psi"] is not None]
        if not finite:
            continue
        hi = max(finite)
        lo = min(finite)
        se = math.sqrt((hi[2] or 0) ** 2 + (lo[2] or 0) ** 2)
        swings[j] = {
            "harshest": {"level": hi[1], "psi": hi[0]},
            "most_lenient": {"level": lo[1], "psi": lo[0]},
            "swing": round(hi[0] - lo[0], 4),
            "z": round((hi[0] - lo[0]) / se, 3) if se > 0 else None,
        }
    return {"by": by, "reference": reference, "anchors": anchor_set, "cells": out, "swings": swings}


def judge_alone_separation(fit: Mapping[str, Any]) -> Dict[str, Dict[str, Optional[float]]]:
    """Separation of parts using only one judge's ratings (other parameters fixed)."""
    P = fit["_params"]
    D, C, F = P["D"], P["C"], P["F"]
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for j in sorted({r["judge"] for r in fit["_rows"]}):
        per_part: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        for r in fit["_rows"]:
            if r["judge"] == j:
                per_part[r["part"]].append((-D[r["criterion"]] - C[j], r["rating"]))
        measures: List[float] = []
        ses: List[float] = []
        for obs in per_part.values():
            xs = [x for _, x in obs]
            if all(x == 0 for x in xs) or all(x == len(F) for x in xs):
                continue
            b = -_cell_newton([(off, x) for off, x in obs], F)  # psi enters negatively, b = -psi
            info = sum(_moments(category_probs(off + b, F))[1] for off, _ in obs)
            if info > 0:
                measures.append(b)
                ses.append(1 / math.sqrt(info))
        out[j] = {**separation(measures, ses), "ratings_per_part": round(sum(len(o) for o in per_part.values()) / len(per_part), 2) if per_part else 0.0}
    return out


def repeatability(ratings: Iterable[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Within-judge agreement across replicates: share of (part, criterion) cells with identical ratings."""
    cells: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
    for r in ratings:
        if r.get("rating") is not None:
            cells[(str(r["judge"]), str(r["part"]), str(r["criterion"]))].append(int(r["rating"]))
    out: Dict[str, Dict[str, Any]] = {}
    for (j, _, _), vals in cells.items():
        d = out.setdefault(j, {"cells": 0, "identical": 0, "replicated_cells": 0, "mean_abs_diff": 0.0})
        d["cells"] += 1
        if len(vals) > 1:
            d["replicated_cells"] += 1
            d["identical"] += int(len(set(vals)) == 1)
            mu = sum(vals) / len(vals)
            d["mean_abs_diff"] += sum(abs(v - mu) for v in vals) / len(vals)
    for d in out.values():
        rc = d["replicated_cells"]
        d["exact_agreement"] = round(d["identical"] / rc, 4) if rc else None
        d["mean_abs_diff"] = round(d["mean_abs_diff"] / rc, 4) if rc else None
        d["deterministic"] = bool(rc) and d["identical"] == rc
    return out


def decide(
    bias: Mapping[str, Any],
    alone: Mapping[str, Mapping[str, Optional[float]]],
    *,
    gates: Optional[Mapping[str, float]] = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Apply the validated decision rules to every judge x level cell."""
    g = dict(DEFAULT_GATES)
    g.update(gates or {})
    flat: List[Tuple[str, str, Dict[str, Any]]] = [
        (j, lvl, c) for j, lv in bias["cells"].items() for lvl, c in lv.items() if not c.get("anchor")
    ]
    pvals = [c["p_value"] if c["p_value"] is not None else 1.0 for _, _, c in flat]
    rejected = benjamini_hochberg(pvals, q=g["bh_q"])
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for (j, lvl, c), rej in zip(flat, rejected):
        reasons: List[str] = []
        se = c["se_clustered"]
        ja = alone.get(j) or {}
        # judge-alone separation only means something when one judge gives each part enough ratings
        sep = ja.get("separation") if (ja.get("ratings_per_part") or 0) >= g["min_ratings_per_part_for_separation"] else None
        noisy_fit = c["n_ratings"] >= g["min_ratings_for_fit"] and ((c["infit"] or 0) > g["max_mnsq"] or (c["outfit"] or 0) > g["max_mnsq"])
        if c.get("extreme_cell"):
            status = "not_certified"
            reasons.append(f"every rating in the {c['extreme_cell']} category; bias is not estimable (see agreement with truth)")
        elif noisy_fit or (sep is not None and sep < g["min_judge_separation"]):
            # noise exceeds signal: misfit, or the judge alone cannot separate parts better than its own error
            status = "removed_noise"
            reasons.append(f"infit {c['infit']}, outfit {c['outfit']} (max {g['max_mnsq']}); judge-alone separation {sep} (min {g['min_judge_separation']})")
        elif se is None or se > g["max_se"] or c["n_parts"] < g["min_parts_per_level"]:
            status = "not_certified"
            reasons.append(f"clustered SE {se} > {g['max_se']}" if se is None or se > g["max_se"] else f"{c['n_parts']} parts < {int(g['min_parts_per_level'])}")
        elif c.get("no_anchor_reference"):
            status = "not_certified"
            reasons.append("no anchor rating at this level to measure bias against")
        elif rej and abs(c["psi"]) >= g["removal_psi"]:
            status = "removed_bias"
            reasons.append(f"psi {c['psi']:+.3f} logits (BH-significant) >= {g['removal_psi']}")
        else:
            status = "certified"
        out.setdefault(j, {})[lvl] = {"status": status, "reasons": reasons, "bh_significant": bool(rej), "psi": c["psi"], "se_clustered": se}
    return out


def calibrate(
    ratings: Iterable[Mapping[str, Any]],
    *,
    gates: Optional[Mapping[str, float]] = None,
    anchors: Sequence[str] = (),
) -> Dict[str, Any]:
    """Full Study B analysis: main model, judge x level bias, judge-alone separation, repeatability, decisions."""
    rows = list(ratings)
    fit = fit_mfrm(rows)
    bias = bias_interaction(fit, anchors=anchors)
    alone = judge_alone_separation(fit)
    decisions = decide(bias, alone, gates=gates)
    public = {k: v for k, v in fit.items() if not k.startswith("_")}
    return {
        "fit": public,
        "bias": bias,
        "judge_alone_separation": alone,
        "repeatability": repeatability(rows),
        "decisions": decisions,
        "gates": {**DEFAULT_GATES, **(gates or {})},
    }


def simulate(
    *,
    parts_per_level: int,
    levels: Sequence[str],
    judges: Mapping[str, float],
    psi: Optional[Mapping[Tuple[str, str], float]] = None,
    criteria: Mapping[str, float] = None,  # type: ignore[assignment]
    thresholds: Sequence[float] = (-1.5, -0.5, 0.5, 1.5),
    replicates: int = 1,
    part_sd: float = 1.0,
    seed: int = 7,
) -> List[Dict[str, Any]]:
    """Simulate ratings from known parameters (used by tests and the pilot sizing)."""
    import random

    rng = random.Random(seed)
    crit = dict(criteria or {"correctness": 0.0, "tests": 0.3, "goal": -0.3})
    rows: List[Dict[str, Any]] = []
    for lvl in levels:
        for n in range(parts_per_level):
            b = rng.gauss(0.0, part_sd)
            pid = f"{lvl}-p{n}"
            for j, c in judges.items():
                bias = (psi or {}).get((j, lvl), 0.0)
                for ci, d in crit.items():
                    for rep in range(1, replicates + 1):
                        probs = category_probs(b - d - c - bias, thresholds)
                        u = rng.random()
                        acc = 0.0
                        x = len(probs) - 1
                        for k, p in enumerate(probs):
                            acc += p
                            if u <= acc:
                                x = k
                                break
                        rows.append({"part": pid, "level": lvl, "judge": j, "criterion": ci, "replicate": rep, "rating": x})
    return rows
