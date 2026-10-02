"""Taguchi Robust Parameter Optimization commands for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("optimize")
def optimize() -> None:
    """Design of Experiments (DoE), Taguchi robust design, and hyperparameter tuning."""


@optimize.command("taguchi")
@click.option("--array", "-a", type=click.Choice(["L4", "L8", "L9", "L12", "L18"], case_sensitive=False), default="L9", help="Orthogonal array type (default L9).")
@click.option("--factors", "-f", multiple=True, help="Names of parameters/factors (e.g. -f temp -f top_p).")
@click.option("--snr", default=None, help="Comma-separated measured response values for SNR calculation (e.g. '120.5,118.2,125.0').")
@click.option("--criterion", type=click.Choice(["smaller", "larger", "nominal"], case_sensitive=False), default="smaller", help="SNR criterion (smaller_is_better, larger_is_better, nominal_is_best).")
@click.option("--loss-k", type=float, default=None, help="Sensitivity factor k for Taguchi Quality Loss L(y) = k * (y - m)^2.")
@click.option("--target-m", type=float, default=None, help="Nominal target value m for Quality Loss.")
@click.option("--measured-y", type=float, default=None, help="Observed output value y for Quality Loss.")
@click.pass_context
def optimize_taguchi(
    ctx: click.Context,
    array: str,
    factors: tuple[str, ...],
    snr: Optional[str],
    criterion: str,
    loss_k: Optional[float],
    target_m: Optional[float],
    measured_y: Optional[float],
) -> None:
    """Generate Taguchi orthogonal design matrices and evaluate Signal-to-Noise Ratio (SNR)."""
    from hath0r_cli.bots.taguchi_bot import TaguchiBot

    bot = TaguchiBot(cwd=Path.cwd())
    factor_list = list(factors) if factors else None

    # Generate design matrix
    matrix_res = bot.generate_matrix(array_type=array, factors=factor_list)

    # Optional SNR calculation
    snr_value = None
    if snr:
        try:
            values = [float(v.strip()) for v in snr.split(",") if v.strip()]
            crit_mapped = f"{criterion}_is_better" if criterion in ("smaller", "larger") else "nominal_is_best"
            snr_value = round(bot.calculate_snr(values, criterion=crit_mapped), 2)
            matrix_res["snr_calculation"] = {
                "values": values,
                "criterion": crit_mapped,
                "snr_db": snr_value,
            }
        except Exception as ex:
            console.print(f"[bold yellow]Warning: Failed to parse SNR values: {ex}[/bold yellow]")

    # Optional Loss function evaluation
    loss_res = None
    if loss_k is not None and target_m is not None and measured_y is not None:
        loss_res = bot.calculate_loss(measured_y=measured_y, target_m=target_m, sensitivity_k=loss_k)
        matrix_res["quality_loss"] = loss_res

    response = _build_response(ctx, command="optimize.taguchi", state="ok", data=matrix_res)

    def _text() -> None:
        console.print(f"[bold green]✓ Taguchi Design Generated[/bold green] (Array: [bold cyan]{matrix_res['array_type']}[/bold cyan], Runs: {matrix_res['total_runs']})")
        table = Table(title=f"Orthogonal Array Matrix: {matrix_res['array_type']}")
        table.add_column("Run ID", style="bold")
        for f in matrix_res["factors"]:
            table.add_column(f)

        for row in matrix_res["matrix"]:
            row_vals = [str(row["run_id"])] + [str(row[f]) for f in matrix_res["factors"]]
            table.add_row(*row_vals)

        console.print(table)

        if "snr_calculation" in matrix_res:
            calc = matrix_res["snr_calculation"]
            console.print(f"\n[bold]Signal-to-Noise Ratio (SNR):[/bold] [cyan]{calc['snr_db']} dB[/cyan] (Criterion: {calc['criterion']})")

        if "quality_loss" in matrix_res:
            ql = matrix_res["quality_loss"]
            console.print(f"[bold]Estimated Quality Loss:[/] [yellow]${ql['estimated_loss']}[/yellow] (Deviation: {ql['deviation']} from target {ql['target_m']})")

    _emit_response(ctx, response, text_renderer=_text)
