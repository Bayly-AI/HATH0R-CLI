"""Taguchi Robust Parameter Optimization commands for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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
@click.option(
    "--array",
    "-a",
    type=click.Choice(["L4", "L8", "L9", "L12", "L18"], case_sensitive=False),
    default="L9",
    help="Orthogonal array type (default L9).",
)
@click.option("--factors", "-f", multiple=True, help="Names of parameters/factors (e.g. -f temp -f top_p).")
@click.option(
    "--snr",
    default=None,
    help="Comma-separated measured response values for SNR calculation (e.g. '120.5,118.2,125.0').",
)
@click.option(
    "--criterion",
    type=click.Choice(["smaller", "larger", "nominal"], case_sensitive=False),
    default="smaller",
    help="SNR criterion (smaller_is_better, larger_is_better, nominal_is_best).",
)
@click.option(
    "--loss-k", type=float, default=None, help="Sensitivity factor k for Taguchi Quality Loss L(y) = k * (y - m)^2."
)
@click.option("--target-m", type=float, default=None, help="Nominal target value m for Quality Loss.")
@click.option("--measured-y", type=float, default=None, help="Observed output value y for Quality Loss.")
@click.option(
    "--responses",
    "responses_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="JSON/YAML file of measured responses per run (and optional levels) to analyse the experiment.",
)
@click.option(
    "--allow-partial",
    is_flag=True,
    help="Analyse only the measured runs when some runs have no responses (never padded).",
)
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
    responses_file: Optional[Path],
    allow_partial: bool,
) -> None:
    """Generate Taguchi orthogonal design matrices and evaluate Signal-to-Noise Ratio (SNR)."""
    from hath0r_cli.bots.taguchi_bot import TaguchiBot

    bot = TaguchiBot(cwd=Path.cwd())
    factor_list = list(factors) if factors else None

    crit_mapped = f"{criterion}_is_better" if criterion in ("smaller", "larger") else "nominal_is_best"
    spec: dict = {}
    try:
        if responses_file is not None:
            from hath0r_cli.bots.taguchi_bot import load_responses_file

            spec = load_responses_file(responses_file)
            factor_list = factor_list or spec.get("factors") or list((spec.get("levels") or {}).keys()) or None
        # Generate design matrix
        matrix_res = bot.generate_matrix(array_type=array, factors=factor_list, levels=spec.get("levels"))
        if responses_file is not None:
            matrix_res["analysis"] = bot.analyze(
                factors=matrix_res["factors"],
                levels=spec.get("levels"),
                responses_matrix=spec["responses"],
                array_type=array,
                criterion=spec.get("criterion", crit_mapped),
                target_m=float(spec.get("target_m", target_m if target_m is not None else 0.0)),
                sensitivity_k=float(spec.get("sensitivity_k", loss_k if loss_k is not None else 1.0)),
                allow_partial=allow_partial,
            )
    except ValueError as exc:
        from hath0r_cli.envelope import Diagnostic

        msg = str(exc)

        response = _build_response(
            ctx,
            command="optimize.taguchi",
            state="error",
            data={"success": False, "error": str(exc)},
            diagnostics=[Diagnostic(code="TAGUCHI_INVALID_EXPERIMENT", severity="error", message=str(exc))],
        )
        _emit_response(ctx, response, text_renderer=lambda: console.print(f"[bold red]✗ {msg}[/bold red]"))
        ctx.exit(2)
        return

    # Optional SNR calculation
    snr_value = None
    if snr:
        try:
            values = [float(v.strip()) for v in snr.split(",") if v.strip()]
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
        console.print(
            f"[bold green]✓ Taguchi Design Generated[/bold green] (Array: [bold cyan]{matrix_res['array_type']}[/bold cyan], Runs: {matrix_res['total_runs']})"
        )
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
            console.print(
                f"\n[bold]Signal-to-Noise Ratio (SNR):[/bold] [cyan]{calc['snr_db']} dB[/cyan] (Criterion: {calc['criterion']})"
            )

        if "analysis" in matrix_res:
            an = matrix_res["analysis"]
            note = f" [yellow](partial: runs {an['missing_runs']} not measured)[/yellow]" if an["partial"] else ""
            console.print(
                f"\n[bold]Experiment analysis:[/bold] {an['measured_runs']}/{an['total_runs']} runs measured{note}"
            )
            console.print(f"  • Optimal levels: {an['optimal_parameters']}")
            console.print(f"  • Best run: {an['best_run']['run_id']} (S/N {an['best_run']['snr_db']} dB)")

        if "quality_loss" in matrix_res:
            ql = matrix_res["quality_loss"]
            console.print(
                f"[bold]Estimated Quality Loss:[/] [yellow]${ql['estimated_loss']}[/yellow] (Deviation: {ql['deviation']} from target {ql['target_m']})"
            )

    _emit_response(ctx, response, text_renderer=_text)


# ------------------------------------------------------------------ sequential DoE (WS8, #593)
def _doe_spec(path: Optional[Path], factor_opts: tuple[str, ...]) -> dict:
    """Read a DoE spec file and/or ``--factor name=low:high`` options."""
    import json as _json

    import yaml as _yaml

    spec: dict = {}
    if path is not None:
        text = path.read_text(encoding="utf-8")
        spec = _json.loads(text) if path.suffix.lower() == ".json" else (_yaml.safe_load(text) or {})
    factors = dict(spec.get("factors") or {})
    for opt in factor_opts:
        name, _, rng = opt.partition("=")
        lo, _, hi = rng.partition(":")
        if not name or not lo or not hi:
            raise ValueError(f"--factor must look like name=low:high, got '{opt}'")
        factors[name.strip()] = [float(lo), float(hi)]
    spec["factors"] = factors
    return spec


def _doe_options(fn):
    fn = click.option("--spec", "spec_file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="YAML/JSON with factors {name: [low, high]} and optional responses.")(fn)
    fn = click.option("--factor", "factor_opts", multiple=True, help="Factor range, name=low:high (repeatable).")(fn)
    fn = click.option("--measure-cmd", default=None, help="Command that reads a JSON point on stdin and prints one number.")(fn)
    return fn


def _doe_run(ctx: click.Context, command: str, runner) -> None:
    from hath0r_cli.commands._qa_common import call, emit

    res = call(ctx, command, "DOE_INVALID_INPUT", runner)
    if res is None:
        return

    def _text() -> None:
        console.print(f"\n[bold cyan]{res.get('kind', 'doe')} study[/bold cyan] {res.get('study_id', '')} · {res.get('status', '')}")
        if res.get("status") == "awaiting_responses":
            table = Table(title="Runs to measure (put responses in the spec file, one list per run, in this order)")
            factors = list(res["factors"])
            table.add_column("Run")
            for f in factors:
                table.add_column(f)
            for i, run in enumerate(res["design"], start=1):
                table.add_row(str(i), *[f"{run[f]:.4g}" for f in factors])
            console.print(table)
        if res.get("significant_factors") is not None:
            for f, r in res["anova"]["factors"].items():
                mark = "[green]significant[/green]" if r["significant"] else "[dim]not significant[/dim]"
                console.print(f"  • {f}: F={r['f']:.3g} p={r['p_value']:.3g} {mark}")
        if res.get("optimum"):
            o = res["optimum"]
            console.print(f"  • Optimum: {o['natural']} → predicted {o['predicted']:.4g}")
        if res.get("fallback"):
            console.print(f"  [yellow]{res['fallback']}[/yellow]")
        if res.get("confirmation"):
            c = res["confirmation"]
            badge = "[green]confirmed[/green]" if c["confirmed"] else "[red]not confirmed[/red]"
            console.print(f"  • Confirmation: observed {c['observed_mean']:.4g} in [{c['interval'][0]:.4g}, {c['interval'][1]:.4g}] {badge}")

    emit(ctx, command, res, _text, exit_on_failure=True)


def _doe_bot():
    from hath0r_cli.bots.doe_bot import DoEBot

    return DoEBot(cwd=Path.cwd())


def _measure(cmd: Optional[str]):
    if not cmd:
        return None
    from hath0r_cli.bots.doe_bot import shell_measure

    return shell_measure(cmd)


@optimize.command("screen")
@_doe_options
@click.option("--fraction", type=int, default=0, show_default=True, help="p in a 2^(k-p) design.")
@click.option("--replicates", type=int, default=3, show_default=True)
@click.option("--alpha", type=float, default=0.05, show_default=True)
@click.pass_context
def optimize_screen(ctx: click.Context, spec_file: Optional[Path], factor_opts: tuple[str, ...], measure_cmd: Optional[str], fraction: int, replicates: int, alpha: float) -> None:
    """Screen factors with a 2-level (fractional) factorial and main-effects ANOVA."""
    def run():
        spec = _doe_spec(spec_file, factor_opts)
        return _doe_bot().screen(spec["factors"], responses=spec.get("responses"), measure=_measure(measure_cmd), fraction=int(spec.get("fraction", fraction)), replicates=replicates, alpha=alpha)

    _doe_run(ctx, "optimize.screen", run)


@optimize.command("rsm")
@_doe_options
@click.option("--design", type=click.Choice(["ccd", "bbd"]), default="ccd", show_default=True)
@click.option("--goal", type=click.Choice(["maximize", "minimize"]), default="maximize", show_default=True)
@click.option("--replicates", type=int, default=1, show_default=True)
@click.pass_context
def optimize_rsm(ctx: click.Context, spec_file: Optional[Path], factor_opts: tuple[str, ...], measure_cmd: Optional[str], design: str, goal: str, replicates: int) -> None:
    """Response surface (central composite or Box-Behnken) on the 2-3 factors kept after screening."""
    def run():
        spec = _doe_spec(spec_file, factor_opts)
        return _doe_bot().rsm(spec["factors"], responses=spec.get("responses"), measure=_measure(measure_cmd), design=spec.get("design", design), goal=spec.get("goal", goal), replicates=replicates)

    _doe_run(ctx, "optimize.rsm", run)


@optimize.command("bayes")
@_doe_options
@click.option("--trials", type=int, default=30, show_default=True)
@click.option("--goal", type=click.Choice(["maximize", "minimize"]), default="maximize", show_default=True)
@click.pass_context
def optimize_bayes(ctx: click.Context, spec_file: Optional[Path], factor_opts: tuple[str, ...], measure_cmd: Optional[str], trials: int, goal: str) -> None:
    """Bayesian optimization (optional optuna extra); falls back to a response surface."""
    def run():
        spec = _doe_spec(spec_file, factor_opts)
        return _doe_bot().bayes(spec["factors"], measure=_measure(measure_cmd), n_trials=trials, goal=spec.get("goal", goal))

    _doe_run(ctx, "optimize.bayes", run)


@optimize.command("confirm")
@click.argument("study_id")
@click.option("--observed", required=True, help="Comma-separated observations at the predicted optimum.")
@click.pass_context
def optimize_confirm(ctx: click.Context, study_id: str, observed: str) -> None:
    """Confirmation run: observations must land inside the predicted interval before promoting."""
    def run():
        values = [float(v) for v in observed.split(",") if v.strip()]
        return _doe_bot().confirm(study_id, values)

    _doe_run(ctx, "optimize.confirm", run)
