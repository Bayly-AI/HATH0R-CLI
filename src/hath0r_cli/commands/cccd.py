"""Continuous Calibration & Continuous Development (CCCD) commands for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.cccd import CCCDCalibrationLoop
from hath0r_cli.common import _build_response, _emit_response, console


@click.group(name="cccd", invoke_without_command=True)
@click.pass_context
def cccd(ctx: click.Context) -> None:
    """Continuous Calibration & Continuous Development (CCCD) loop engine commands."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cccd.command(name="status")
@click.pass_context
def cccd_status(ctx: click.Context) -> None:
    """Inspect current CCCD calibration metrics, drift parameters, and active tuning loops."""
    loop = CCCDCalibrationLoop()
    status_data = loop.get_status()

    response = _build_response(
        ctx,
        command="cccd status",
        state="ok",
        data=status_data,
    )

    def _text() -> None:
        state = status_data["state"]
        console.print(
            "\n[bold cyan]⚡ HATH0R Continuous Calibration & Continuous Development (CCCD) Status[/bold cyan]\n"
        )

        params_table = Table(title="Calibrated Runtime Parameters", show_header=True, header_style="bold magenta")
        params_table.add_column("Parameter", style="cyan")
        params_table.add_column("Calibrated Value", style="green")

        for k, v in state.get("current_parameters", {}).items():
            params_table.add_row(str(k), str(v))

        console.print(params_table)

        drift_table = Table(title="Drift Telemetry Metrics", show_header=True, header_style="bold blue")
        drift_table.add_column("Metric", style="cyan")
        drift_table.add_column("Value / Drift", style="yellow")

        for k, v in state.get("drift_metrics", {}).items():
            drift_table.add_row(str(k), f"{v:+}" if isinstance(v, (int, float)) else str(v))

        console.print(drift_table)

        freshness = status_data.get("freshness", {})
        fresh_status_str = (
            "[bold green]FRESH[/bold green]" if freshness.get("is_fresh") else "[bold yellow]STALE (>24h)[/bold yellow]"
        )
        age_str = f"{freshness.get('age_hours'):.1f} hours ago" if freshness.get("age_hours") is not None else "Never"

        summary_panel = Panel(
            f"Freshness Status: {fresh_status_str} (Last run: {age_str})\n"
            f"Total Calibration Runs: [bold white]{state.get('total_calibration_runs', 0)}[/bold white]\n"
            f"Last Run Timestamp: [bold white]{state.get('last_run_timestamp') or 'Never'}[/bold white]\n"
            f"Compiled DSPy Signatures: [bold white]{status_data.get('compiled_signatures_count', 0)}[/bold white]",
            title="CCCD Execution Summary & Entry Gate",
            border_style="bold green" if freshness.get("is_fresh") else "bold yellow",
        )
        console.print(summary_panel)

    _emit_response(ctx, response, text_renderer=_text)


@cccd.command(name="calibrate")
@click.option("--iterations", "-i", type=int, default=3, help="Number of benchmark evaluation iterations.")
@click.option("--signature", "-s", type=str, default="default_agent_signature", help="DSPy signature name to compile.")
@click.option(
    "--strategy",
    type=click.Choice(["taguchi", "sequential"]),
    default="taguchi",
    show_default=True,
    help="sequential: screen, response surface, then confirmation (doe-bot, #593).",
)
@click.option("--spec", "spec_file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Sequential: YAML/JSON with factors {name: [low, high]} and goal.")
@click.option("--measure-cmd", default=None, help="Command that reads a JSON point on stdin and prints the measured response (default: measure_cmd in cfg/cccd/doe-spec.yaml).")
@click.option(
    "--responses",
    "responses_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Taguchi: JSON file with measured responses, one list per L9 run (9 rows).",
)
@click.pass_context
def cccd_calibrate(
    ctx: click.Context,
    iterations: int,
    signature: str,
    strategy: str,
    spec_file: Optional[Path],
    measure_cmd: Optional[str],
    responses_file: Optional[Path],
) -> None:
    """Calibrate on measured benchmark responses (nothing is simulated)."""
    if strategy == "sequential":
        _calibrate_sequential(ctx, spec_file, measure_cmd)
        return
    from hath0r_cli.commands._qa_common import call

    def run() -> Dict[str, Any]:
        responses = json.loads(responses_file.read_text(encoding="utf-8")) if responses_file else None
        try:
            return CCCDCalibrationLoop().run_calibration(
                iterations=iterations, signature_name=signature, responses_matrix=responses, measure_cmd=measure_cmd, spec=spec_file
            )
        except RuntimeError as exc:  # the measurement command failed
            raise ValueError(str(exc)) from exc

    result = call(ctx, "cccd calibrate", "CCCD_NO_MEASUREMENT", run)
    if result is None:
        return

    response = _build_response(
        ctx,
        command="cccd calibrate",
        state="ok" if result["success"] else "error",
        data=result,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Continuous Calibration Run Completed Successfully[/bold green]")
        console.print(f"Calibration ID: [bold cyan]#{result['calibration_id']}[/bold cyan]")
        console.print(f"Timestamp: [bold white]{result['timestamp']}[/bold white]")
        console.print(f"DSPy Compiled Signature: [bold yellow]{signature}[/bold yellow]")

        params = result["updated_parameters"]
        console.print("\n[bold cyan]Updated Calibrated Parameters:[/bold cyan]")
        for k, v in params.items():
            console.print(f"  • {k}: [bold green]{v}[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@cccd.command(name="auto-tune")
@click.option("--interval", type=int, default=300, help="Continuous tuning check interval in seconds.")
@click.option("--daemon/--no-daemon", default=False, help="Run continuous calibration loop in daemon mode.")
@click.pass_context
def cccd_autotune(ctx: click.Context, interval: int, daemon: bool) -> None:
    """Enable background continuous development and prompt optimization daemon."""
    loop = CCCDCalibrationLoop()
    state = loop.load_state()
    state["active_calibration"] = True
    loop.save_state(state)

    data = {
        "active_calibration": True,
        "interval_seconds": interval,
        "daemon_mode": daemon,
        "message": f"Continuous calibration auto-tune daemon enabled (interval: {interval}s, daemon: {daemon}).",
    }

    response = _build_response(
        ctx,
        command="cccd auto-tune",
        state="ok",
        data=data,
    )

    def _text() -> None:
        console.print(
            Panel(
                f"[bold green]Continuous Development & Auto-Tune Daemon Active[/bold green]\n\n"
                f"Check Interval: [bold cyan]{interval} seconds[/bold cyan]\n"
                f"Daemon Mode: [bold yellow]{daemon}[/bold yellow]\n"
                f"Status: Monitoring OTLP spans and drift thresholds for automated prompt optimization.",
                title="CCCD Auto-Tune Control Plane",
                border_style="bold cyan",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)


def _calibrate_sequential(ctx: click.Context, spec_file: Optional[Path], measure_cmd: Optional[str]) -> None:
    from hath0r_cli.bots.doe_bot import DoEBot
    from hath0r_cli.commands._qa_common import call, emit

    def run():
        if not spec_file:
            raise ValueError("--strategy sequential needs --spec (factor ranges) and a measurement (--measure-cmd or measure_cmd in the spec; nothing is simulated)")
        return DoEBot(cwd=Path.cwd()).calibrate_sequential(str(spec_file), measure_cmd)

    res = call(ctx, "cccd calibrate", "DOE_INVALID_INPUT", run)
    if res is None:
        return

    def _text() -> None:
        badge = "[green]confirmed[/green]" if res["confirmed"] else "[red]not confirmed[/red]"
        console.print(f"\n[bold cyan]Sequential calibration[/bold cyan]: kept {res['kept_factors']} · optimum {res['optimum']['natural']} {badge}")
        console.print(f"  • Studies: screen {res['screen']}, rsm {res['rsm']}")

    emit(ctx, "cccd calibrate", res, _text, exit_on_failure=True)
