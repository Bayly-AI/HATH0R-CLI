"""Taguchi Robust Parameter Optimization Bot for HATH0R CLI."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class TaguchiBot:
    """Design of Experiments (DoE) & Robust Parameter Optimization Bot."""

    cwd: Path = field(default_factory=Path.cwd)

    # Standard Orthogonal Array Templates
    L4_TEMPLATE: Sequence[Sequence[int]] = (
        (1, 1, 1),
        (1, 2, 2),
        (2, 1, 2),
        (2, 2, 1),
    )

    L8_TEMPLATE: Sequence[Sequence[int]] = (
        (1, 1, 1, 1, 1, 1, 1),
        (1, 1, 1, 2, 2, 2, 2),
        (1, 2, 2, 1, 1, 2, 2),
        (1, 2, 2, 2, 2, 1, 1),
        (2, 1, 2, 1, 2, 1, 2),
        (2, 1, 2, 2, 1, 2, 1),
        (2, 2, 1, 1, 2, 2, 1),
        (2, 2, 1, 2, 1, 1, 2),
    )

    L9_TEMPLATE: Sequence[Sequence[int]] = (
        (1, 1, 1, 1),
        (1, 2, 2, 2),
        (1, 3, 3, 3),
        (2, 1, 2, 3),
        (2, 2, 3, 1),
        (2, 3, 1, 2),
        (3, 1, 3, 2),
        (3, 2, 1, 3),
        (3, 3, 2, 1),
    )

    L12_TEMPLATE: Sequence[Sequence[int]] = (
        (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
        (1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2),
        (1, 1, 2, 2, 2, 1, 1, 1, 2, 2, 2),
        (1, 2, 1, 2, 2, 1, 2, 2, 1, 1, 2),
        (1, 2, 2, 1, 2, 2, 1, 2, 1, 2, 1),
        (1, 2, 2, 2, 1, 2, 2, 1, 2, 1, 1),
        (2, 1, 2, 2, 1, 1, 2, 2, 1, 2, 1),
        (2, 1, 2, 1, 2, 2, 2, 1, 1, 1, 2),
        (2, 1, 1, 2, 2, 2, 1, 2, 2, 1, 1),
        (2, 2, 2, 1, 1, 1, 1, 2, 2, 1, 2),
        (2, 2, 1, 2, 1, 2, 1, 1, 1, 2, 2),
        (2, 2, 1, 1, 2, 1, 2, 1, 2, 2, 1),
    )

    L18_TEMPLATE: Sequence[Sequence[int]] = (
        (1, 1, 1, 1, 1, 1, 1, 1),
        (1, 1, 2, 2, 2, 2, 2, 2),
        (1, 1, 3, 3, 3, 3, 3, 3),
        (1, 2, 1, 1, 2, 2, 3, 3),
        (1, 2, 2, 2, 3, 3, 1, 1),
        (1, 2, 3, 3, 1, 1, 2, 2),
        (1, 3, 1, 2, 1, 3, 2, 3),
        (1, 3, 2, 3, 2, 1, 3, 1),
        (1, 3, 3, 1, 3, 2, 1, 2),
        (2, 1, 1, 3, 3, 2, 2, 1),
        (2, 1, 2, 1, 1, 3, 3, 2),
        (2, 1, 3, 2, 2, 1, 1, 3),
        (2, 2, 1, 2, 3, 1, 3, 2),
        (2, 2, 2, 3, 1, 2, 1, 3),
        (2, 2, 3, 1, 2, 3, 2, 1),
        (2, 3, 1, 3, 2, 3, 1, 2),
        (2, 3, 2, 1, 3, 1, 2, 3),
        (2, 3, 3, 2, 1, 2, 3, 1),
    )

    def generate_matrix(
        self,
        array_type: str = "L9",
        factors: Optional[List[str]] = None,
        levels: Optional[Dict[str, List[Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate an orthogonal array matrix mapped to parameter factor levels."""
        templates = {
            "L4": self.L4_TEMPLATE,
            "L8": self.L8_TEMPLATE,
            "L9": self.L9_TEMPLATE,
            "L12": self.L12_TEMPLATE,
            "L18": self.L18_TEMPLATE,
        }
        arr = array_type.upper()
        if arr not in templates:
            raise ValueError(f"Unsupported array type: {array_type}. Supported: {list(templates.keys())}")

        template = templates[arr]
        num_runs = len(template)
        max_factors = len(template[0])

        active_factors = factors or [f"Factor_{i + 1}" for i in range(min(max_factors, len(factors or template[0])))]
        if len(active_factors) > max_factors:
            raise ValueError(
                f"Array {arr} supports at most {max_factors} factors, but {len(active_factors)} were provided."
            )

        # Poka-yoke (#583): levels must match what each array column actually tests, so a factor is
        # never silently wrapped onto the wrong level (modulo mapping) or left with untested levels.
        if levels:
            unknown = sorted(set(levels) - set(active_factors))
            if unknown:
                raise ValueError(f"Levels supplied for factors that are not in the design: {unknown}")
            for col_idx, factor_name in enumerate(active_factors):
                if factor_name not in levels:
                    continue
                required = max(row[col_idx] for row in template)
                supplied = len(levels[factor_name])
                if supplied != required:
                    raise ValueError(
                        f"Factor '{factor_name}' has {supplied} levels but column {col_idx + 1} of {arr} "
                        f"tests exactly {required}. Choose a different array or supply {required} levels."
                    )

        runs: List[Dict[str, Any]] = []
        for run_idx, row in enumerate(template):
            run_dict: Dict[str, Any] = {"run_id": run_idx + 1}
            for col_idx, factor_name in enumerate(active_factors):
                raw_level = row[col_idx]
                if levels and factor_name in levels:
                    available = levels[factor_name]
                    mapped_val = available[(raw_level - 1) % len(available)]
                    run_dict[factor_name] = mapped_val
                else:
                    run_dict[factor_name] = raw_level
            runs.append(run_dict)

        return {
            "success": True,
            "array_type": arr,
            "total_runs": num_runs,
            "max_factors": max_factors,
            "factors": active_factors,
            "matrix": runs,
        }

    def calculate_snr(
        self,
        responses: Sequence[float],
        criterion: str = "smaller_is_better",
    ) -> float:
        """Calculate Taguchi Signal-to-Noise Ratio (SNR) in decibels (dB)."""
        if not responses:
            raise ValueError("Responses list cannot be empty.")

        n = len(responses)
        crit = criterion.lower()

        if crit in ("smaller_is_better", "smaller"):
            # SNR = -10 * log10( (1/n) * sum(y^2) )
            sum_sq = sum(y**2 for y in responses)
            mean_sq = sum_sq / n
            if mean_sq <= 0:
                return 100.0
            return -10.0 * math.log10(mean_sq)

        elif crit in ("larger_is_better", "larger"):
            # SNR = -10 * log10( (1/n) * sum(1 / y^2) )
            sum_inv_sq = sum(1.0 / (y**2) for y in responses if y != 0)
            mean_inv_sq = sum_inv_sq / n
            if mean_inv_sq <= 0:
                return 100.0
            return -10.0 * math.log10(mean_inv_sq)

        elif crit in ("nominal_is_best", "nominal"):
            # SNR = 10 * log10( mean^2 / variance )
            mean = sum(responses) / n
            if n == 1:
                return 100.0
            variance = sum((y - mean) ** 2 for y in responses) / (n - 1)
            if variance <= 1e-12:
                return 100.0
            return 10.0 * math.log10((mean**2) / variance)

        else:
            raise ValueError(
                f"Unknown SNR criterion: {criterion}. Choose: nominal_is_best, smaller_is_better, larger_is_better."
            )

    def calculate_loss(
        self,
        measured_y: float,
        target_m: float,
        sensitivity_k: float,
    ) -> Dict[str, Any]:
        """Calculate Taguchi Quality Loss L(y) = k * (y - m)^2."""
        deviation = measured_y - target_m
        loss = sensitivity_k * (deviation**2)
        return {
            "success": True,
            "measured_y": measured_y,
            "target_m": target_m,
            "sensitivity_k": sensitivity_k,
            "deviation": round(deviation, 4),
            "estimated_loss": round(loss, 4),
        }

    def analyze(
        self,
        *,
        factors: List[str],
        responses_matrix: List[List[float]],
        levels: Optional[Dict[str, List[Any]]] = None,
        array_type: str = "L9",
        criterion: str = "smaller_is_better",
        target_m: float = 0.0,
        sensitivity_k: float = 1.0,
        allow_partial: bool = False,
    ) -> Dict[str, Any]:
        """Analyse measured responses for every run of an orthogonal array (S/N, loss, optimum).

        Poka-yoke (#583): incomplete experiments raise unless ``allow_partial`` is set, and missing
        runs are skipped rather than padded.
        """
        from hath0r_cli.cccd.taguchi_optimizer import TaguchiLossOptimizer

        return TaguchiLossOptimizer(bot=self).optimize_parameters(
            factors=factors,
            levels=levels or {},
            responses_matrix=responses_matrix,
            array_type=array_type,
            criterion=criterion,
            target_m=target_m,
            sensitivity_k=sensitivity_k,
            allow_partial=allow_partial,
        )


def load_responses_file(path: Path) -> Dict[str, Any]:
    """Read a Taguchi responses file (JSON or YAML).

    Accepts either a list of per-run response lists, or a mapping with ``responses`` and optional
    ``levels``, ``factors``, ``criterion``, ``target_m`` and ``sensitivity_k``.
    """
    import json

    import yaml

    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text) if Path(path).suffix.lower() == ".json" else yaml.safe_load(text)
    if isinstance(data, list):
        data = {"responses": data}
    if not isinstance(data, dict) or not isinstance(data.get("responses"), list):
        raise ValueError(f"{path}: expected a 'responses' list of per-run measurement lists")
    rows: List[List[float]] = []
    for i, row in enumerate(data["responses"], start=1):
        if row is None:
            rows.append([])
        elif isinstance(row, (int, float)):
            rows.append([float(row)])
        elif isinstance(row, list):
            rows.append([float(v) for v in row])
        else:
            raise ValueError(f"{path}: run {i} responses must be a number or a list of numbers")
    data["responses"] = rows
    return data
