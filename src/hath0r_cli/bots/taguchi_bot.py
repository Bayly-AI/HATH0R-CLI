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
