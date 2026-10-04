"""Continuous Integration, Continuous Calibration & Continuous Development (CICCCD) commands for HATH0R CLI."""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.bots.cicccd_bot import CICCCDManagingBot
from hath0r_cli.common import _build_response, _emit_response, console


@click.group(name="cicccd", invoke_without_command=True)
@click.pass_context
def cicccd(ctx: click.Context) -> None:
    """Continuous Integration, Calibration & Development (CICCCD) commands."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cicccd.command(name="status")
@click.pass_context
def cicccd_status(ctx: click.Context) -> None:
    """Inspect current CICCCD calibration metrics, CI status, drift parameters, and active tuning loops."""
    bot = CICCCDManagingBot()
    status_data = bot.status()

    response = _build_response(
        ctx,
        command="cicccd status",
        state="ok",
        data=status_data,
    )

    def _text() -> None:
        state = status_data["state"]
        console.print("\n[bold cyan]⚡ HATH0R Continuous Integration, Calibration & Development (CICCCD) Status[/bold cyan]\n")

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
            drift_table.add_row(str(k), f"{v:+}")

        console.print(drift_table)

        freshness = status_data.get("freshness", {})
        fresh_status_str = "[bold green]FRESH[/bold green]" if freshness.get("is_fresh") else "[bold yellow]STALE (>24h)[/bold yellow]"
        age_str = f"{freshness.get('age_hours'):.1f} hours ago" if freshness.get("age_hours") is not None else "Never"

        summary_panel = Panel(
            f"Freshness Status: {fresh_status_str} (Last run: {age_str})\n"
            f"Total Calibration Runs: [bold white]{state.get('total_calibration_runs', 0)}[/bold white]\n"
            f"Last Run Timestamp: [bold white]{state.get('last_run_timestamp') or 'Never'}[/bold white]\n"
            f"Compiled DSPy Signatures: [bold white]{status_data.get('compiled_signatures_count', 0)}[/bold white]",
            title="CICCCD Execution Summary & Entry Gate",
            border_style="bold green" if freshness.get("is_fresh") else "bold yellow",
        )
        console.print(summary_panel)

    _emit_response(ctx, response, text_renderer=_text)


@cicccd.command(name="validate")
@click.option("--repo", type=str, default=None, help="Target repository to validate CICCCD state for.")
@click.pass_context
def cicccd_validate(ctx: click.Context, repo: str | None) -> None:
    """Validate CICCCD state across CI contracts, CC freshness, and CD Artifact Hexad."""
    bot = CICCCDManagingBot()
    res = bot.validate_cicccd(repo=repo)

    response = _build_response(
        ctx,
        command="cicccd validate",
        state="ok" if res["valid"] else "warning",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold cyan]🔍 HATH0R CICCCD Multi-Stage Validation[/bold cyan]\n")
        console.print(f"Target Repo: [bold white]{res['repo']}[/bold white]")
        console.print(f"Overall Status: {'[bold green]VALID[/bold green]' if res['valid'] else '[bold yellow]REQUIRES RE-CALIBRATION[/bold yellow]'}\n")

        console.print("[bold green]Continuous Integration (CI):[/bold green]")
        console.print(f"  • Schema Contracts: [green]{res['ci']['contracts_valid']}[/green]")
        console.print(f"  • AgentGraph Policy: [green]{res['ci']['agentgraph_valid']}[/green]")

        console.print("\n[bold yellow]Continuous Calibration (CC):[/bold yellow]")
        console.print(f"  • Calibration Freshness: {'[green]Fresh[/green]' if res['cc']['is_fresh'] else '[yellow]Stale (>24h)[/yellow]'}")
        console.print(f"  • Calibration Age: {res['cc']['age_hours']:.1f} hours")

        console.print("\n[bold magenta]Continuous Development (CD):[/bold magenta]")
        console.print(f"  • Artifact Hexad Docs: [green]{res['cd']['artifact_hexad_published']}[/green]")
        console.print(f"  • Auto-Tune Active: [cyan]{res['cd']['auto_tune_active']}[/cyan]\n")

    _emit_response(ctx, response, text_renderer=_text)


@cicccd.command(name="calibrate")
@click.option("--iterations", "-i", type=int, default=3, help="Number of benchmark evaluation iterations.")
@click.option("--signature", "-s", type=str, default="default_agent_signature", help="DSPy signature name to compile.")
@click.pass_context
def cicccd_calibrate(ctx: click.Context, iterations: int, signature: str) -> None:
    """Trigger on-demand continuous calibration run against specified benchmark datasets."""
    bot = CICCCDManagingBot()
    result = bot.calibrate(iterations=iterations, signature=signature)

    response = _build_response(
        ctx,
        command="cicccd calibrate",
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


@cicccd.command(name="auto-tune")
@click.option("--interval", type=int, default=300, help="Continuous tuning check interval in seconds.")
@click.option("--daemon/--no-daemon", default=False, help="Run continuous calibration loop in daemon mode.")
@click.pass_context
def cicccd_autotune(ctx: click.Context, interval: int, daemon: bool) -> None:
    """Enable background continuous development and prompt optimization daemon."""
    bot = CICCCDManagingBot()
    data = bot.auto_tune(interval=interval, daemon=daemon)

    response = _build_response(
        ctx,
        command="cicccd auto-tune",
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
                title="CICCCD Auto-Tune Control Plane",
                border_style="bold cyan",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)
