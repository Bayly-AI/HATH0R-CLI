"""Taguchi Quality Loss and OATS Optimizer for CCCD Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from hath0r_cli.bots.taguchi_bot import TaguchiBot


class IncompleteExperimentError(ValueError):
    """Raised when an orthogonal-array experiment is missing responses for one or more runs.

    Poka-yoke guard (#581, #583): the optimizer never invents data for runs that were not measured.
    """


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
        allow_partial: bool = False,
    ) -> Dict[str, Any]:
        """Generate orthogonal design matrix, calculate S/N ratios and Taguchi Quality Loss L(y).

        Every run of the array must have at least one measured response. Missing runs raise
        ``IncompleteExperimentError``; with ``allow_partial=True`` they are skipped (never padded),
        the result is marked ``partial: True`` and only measured runs inform the optimum.
        """
        matrix_data = self.bot.generate_matrix(array_type=array_type, factors=factors, levels=levels)
        runs = matrix_data["matrix"]

        if len(responses_matrix) > len(runs):
            raise ValueError(
                f"{len(responses_matrix)} response rows supplied but array {array_type} has only {len(runs)} runs"
            )
        missing_runs = [
            run["run_id"]
            for idx, run in enumerate(runs)
            if idx >= len(responses_matrix) or not list(responses_matrix[idx])
        ]
        if missing_runs and not allow_partial:
            raise IncompleteExperimentError(
                f"Array {array_type} needs responses for all {len(runs)} runs; missing runs {missing_runs}. "
                "Measure them, or pass allow_partial=True to analyse only the measured runs."
            )
        if len(missing_runs) == len(runs):
            raise IncompleteExperimentError("No runs have measured responses.")

        run_results: List[Dict[str, Any]] = []
        snr_per_run: List[float] = []
        loss_per_run: List[float] = []

        for idx, run in enumerate(runs):
            if run["run_id"] in missing_runs:
                continue
            responses = [float(v) for v in responses_matrix[idx]]
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
            def _calc_mean_snr(lvl: Any) -> float:
                snrs = level_snrs[lvl]
                return sum(snrs) / len(snrs)

            best_level = max(level_snrs.keys(), key=_calc_mean_snr)
            optimal_levels[factor] = best_level

        return {
            "success": True,
            "array_type": array_type,
            "total_runs": len(runs),
            "measured_runs": len(run_results),
            "missing_runs": missing_runs,
            "partial": bool(missing_runs),
            "runs": run_results,
            "best_run": best_run,
            "optimal_parameters": optimal_levels,
            "mean_snr_db": round(sum(snr_per_run) / len(snr_per_run), 4) if snr_per_run else 0.0,
            "mean_quality_loss": round(sum(loss_per_run) / len(loss_per_run), 4) if loss_per_run else 0.0,
        }
