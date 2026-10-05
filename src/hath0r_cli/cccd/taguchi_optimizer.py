"""Taguchi Quality Loss and OATS Optimizer for CCCD Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from hath0r_cli.bots.taguchi_bot import TaguchiBot


@dataclass
class TaguchiLossOptimizer:
    """Applies Taguchi Methods (S/N ratio and Quality Loss) for CCCD hyperparameter tuning."""

    bot: TaguchiBot = field(default_factory=TaguchiBot)

    def optimize_parameters(
        self,
        factors: List[str],
        levels: Dict[str, List[Any]],
        responses_matrix: List[List[float]],
        array_type: str = "L9",
        criterion: str = "smaller_is_better",
        target_m: float = 0.0,
        sensitivity_k: float = 1.0,
    ) -> Dict[str, Any]:
        """Generate orthogonal design matrix, calculate S/N ratios and Taguchi Quality Loss L(y)."""
        matrix_data = self.bot.generate_matrix(array_type=array_type, factors=factors, levels=levels)
        runs = matrix_data["matrix"]

        if len(responses_matrix) < len(runs):
            # Pad responses if needed with baseline estimates
            responses_matrix = list(responses_matrix) + [[1.0]] * (len(runs) - len(responses_matrix))

        run_results: List[Dict[str, Any]] = []
        snr_per_run: List[float] = []
        loss_per_run: List[float] = []

        for idx, run in enumerate(runs):
            responses = responses_matrix[idx] if idx < len(responses_matrix) else [1.0]
            snr = self.bot.calculate_snr(responses, criterion=criterion)
            mean_y = sum(responses) / len(responses) if responses else 0.0
            loss_data = self.bot.calculate_loss(mean_y, target_m=target_m, sensitivity_k=sensitivity_k)

            snr_per_run.append(snr)
            loss_per_run.append(loss_data["estimated_loss"])

            run_results.append(
                {
                    "run_id": run["run_id"],
                    "parameters": {k: v for k, v in run.items() if k != "run_id"},
                    "responses": responses,
                    "snr_db": round(snr, 4),
                    "quality_loss": loss_data["estimated_loss"],
                }
            )

        # Find best parameter combination based on max S/N ratio and min Quality Loss
        best_run_idx = max(range(len(snr_per_run)), key=lambda i: snr_per_run[i])
        best_run = run_results[best_run_idx]

        # Compute factor level main effects
        optimal_levels: Dict[str, Any] = {}
        for factor in factors:
            level_snrs: Dict[Any, List[float]] = {}
            for res in run_results:
                val = res["parameters"].get(factor)
                if val is not None:
                    level_snrs.setdefault(val, []).append(res["snr_db"])

            # Find level with highest mean SNR
            best_level = max(
                level_snrs.keys(),
                key=lambda lvl, snrs=level_snrs: sum(snrs[lvl]) / len(snrs[lvl]),
            )
            optimal_levels[factor] = best_level

        return {
            "success": True,
            "array_type": array_type,
            "total_runs": len(runs),
            "runs": run_results,
            "best_run": best_run,
            "optimal_parameters": optimal_levels,
            "mean_snr_db": round(sum(snr_per_run) / len(snr_per_run), 4) if snr_per_run else 0.0,
            "mean_quality_loss": round(sum(loss_per_run) / len(loss_per_run), 4) if loss_per_run else 0.0,
        }
