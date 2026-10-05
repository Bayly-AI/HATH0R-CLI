"""
Arize Phoenix CLI Command Group for HATH0R.

Provides first-class CLI commands for launching, stopping, inspecting,
evaluating, and tracking FinOps costs with Arize Phoenix open-source observability.
"""

from __future__ import annotations

import json
import webbrowser
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..bots.phoenix_manager_bot import phoenix_manager_bot
from ..bots.phoenix_observer_bot import phoenix_observer_bot
from ..telemetry import load_otel_config

console = Console()


@click.group("phoenix", help="Arize Phoenix agent observability, traces, and LLM-as-a-judge evaluations.")
def phoenix_cmd() -> None:
    """Arize Phoenix observability command suite."""
    pass


@phoenix_cmd.command("status", help="Check Arize Phoenix collector and UI availability.")
@click.option("--group", default="hath0r", type=click.Choice(["hath0r", "1-nation", "bai"]), help="Docker group name.")
@click.option("--endpoint", default=None, help="Custom Phoenix OTLP/HTTP endpoint.")
@click.option("--json", "as_json", is_flag=True, help="Output status as JSON.")
def phoenix_status(group: str, endpoint: Optional[str], as_json: bool) -> None:
    """Check Arize Phoenix server status and connection parameters."""
    res = phoenix_manager_bot.check_status(group=group, custom_endpoint=endpoint)
    cfg = load_otel_config()

    if as_json:
        payload = {
            "group": group,
            "container": res["container"],
            "service": cfg.service_name,
            "environment": cfg.deployment_environment,
            "active_url": res["active_url"],
            "target_url": res["active_url"]
            or (
                res.get("candidates", ["http://localhost:58000/phoenix/"])[0]
                if "candidates" in res
                else "http://localhost:58000/phoenix/"
            ),
            "healthy": res["healthy"],
            "http_status": res["http_status"],
            "otlp_endpoint": cfg.otlp_endpoint or "http://1NPHOENIX:4318",
            "error": res["error"],
        }
        click.echo(json.dumps(payload, indent=2))
        return

    console.print(f"[bold cyan]Arize Phoenix Observability Status ({group.upper()}):[/bold cyan]")
    console.print(f"  • Container:       {res['container']}")
    console.print(f"  • Service Name:    {cfg.service_name}")
    console.print(f"  • Environment:     {cfg.deployment_environment}")
    console.print(f"  • OTLP Target:     {cfg.otlp_endpoint or 'http://1NPHOENIX:4318'}")
    console.print(f"  • Active UI:       {res['active_url'] or 'Offline'}")

    if res["healthy"]:
        console.print("  [bold green]✓ Phoenix Server is ACTIVE and responding (HTTP 200).[/bold green]")
    else:
        console.print(f"  [yellow]! Phoenix Server is OFFLINE (Error: {res['error'] or 'Unreachable'})[/yellow]")
        console.print(f"    [dim]To start Phoenix locally: 'hath0r phoenix up --group {group}'[/dim]")


@phoenix_cmd.command("up", help="Start the Arize Phoenix container locally.")
@click.option("--group", default="hath0r", type=click.Choice(["hath0r", "1-nation", "bai"]), help="Docker group name.")
@click.option("--detach/--no-detach", default=True, help="Run in background mode.")
def phoenix_up(group: str, detach: bool) -> None:
    """Launch the Phoenix container using Docker."""
    console.print(f"[cyan]Starting Phoenix container for group '{group}'...[/cyan]")
    res = phoenix_manager_bot.start_phoenix(group=group, detach=detach)
    if res["success"]:
        console.print(f"[bold green]✓ {res['container']} started successfully.[/bold green]")
        console.print(f"  • UI: {res['edge_url']} or {res['direct_url']}")
    else:
        console.print(f"[bold red]Failed to start {res['container']}: {res['error']}[/bold red]")


@phoenix_cmd.command("down", help="Stop the Arize Phoenix container.")
@click.option("--group", default="hath0r", type=click.Choice(["hath0r", "1-nation", "bai"]), help="Docker group name.")
def phoenix_down(group: str) -> None:
    """Stop the Phoenix container."""
    console.print(f"[cyan]Stopping Phoenix container for group '{group}'...[/cyan]")
    res = phoenix_manager_bot.stop_phoenix(group=group)
    if res["success"]:
        console.print(f"[bold green]✓ {res['container']} stopped successfully.[/bold green]")
    else:
        console.print(f"[bold red]Failed to stop {res['container']}: {res['error']}[/bold red]")


@phoenix_cmd.command("projects", help="List registered Phoenix projects and span distributions.")
@click.option(
    "--group", default="1-nation", type=click.Choice(["hath0r", "1-nation", "bai"]), help="Docker group name."
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def phoenix_projects(group: str, as_json: bool) -> None:
    """Display Phoenix projects and span telemetry."""
    projects = phoenix_manager_bot.get_projects(group=group)

    if as_json:
        click.echo(json.dumps(projects, indent=2))
        return

    table = Table(title=f"Arize Phoenix Projects & Telemetry ({group.upper()})")
    table.add_column("Project / Service Name", style="bold green")
    table.add_column("Recorded Spans", justify="right", style="cyan")

    for proj in projects:
        table.add_row(proj.get("name", "unknown"), str(proj.get("span_count", 0)))

    console.print(table)


@phoenix_cmd.command("costs", help="Show FinOps token usage and computed LLM costs.")
@click.option(
    "--group", default="1-nation", type=click.Choice(["hath0r", "1-nation", "bai"]), help="Docker group name."
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def phoenix_costs(group: str, as_json: bool) -> None:
    """Display FinOps token count and USD cost totals."""
    summary = phoenix_manager_bot.get_cost_summary(group=group)

    if as_json:
        click.echo(json.dumps(summary, indent=2))
        return

    console.print(f"[bold cyan]Arize Phoenix FinOps Summary ({group.upper()}):[/bold cyan]")
    console.print(f"  • Total Spans:      {summary.get('total_spans', 0)}")
    console.print(f"  • Total LLM Tokens: {summary.get('total_tokens', 0):,}")
    console.print(f"  • Total LLM Cost:   ${summary.get('total_cost_usd', 0.0):.4f} USD")


@phoenix_cmd.command("ui", help="Open the Arize Phoenix Web UI in browser.")
@click.option(
    "--group", default="1-nation", type=click.Choice(["hath0r", "1-nation", "bai"]), help="Docker group name."
)
@click.option("--edge/--direct", default=True, help="Use Edge proxy or direct port.")
def phoenix_ui(group: str, edge: bool) -> None:
    """Open Phoenix UI in the default web browser."""
    group_cfg = phoenix_manager_bot.GROUP_COMPOSE_MAP.get(group, phoenix_manager_bot.GROUP_COMPOSE_MAP["hath0r"])
    url = group_cfg["edge_url"] if edge else group_cfg["direct_url"]
    console.print(f"[cyan]Opening Phoenix UI for group '{group}': {url}[/cyan]")
    webbrowser.open(url)


@phoenix_cmd.command("evals", help="Inspect evaluation benchmarks and thresholds.")
@click.option("--suite", default="1-nation", help="Suite identifier.")
@click.option("--json", "as_json", is_flag=True, help="Output evaluation schema as JSON.")
def phoenix_evals(suite: str, as_json: bool) -> None:
    """List registered evaluation judges and quality gates."""
    manifest = phoenix_observer_bot.get_evaluation_manifest()

    if as_json:
        click.echo(json.dumps(manifest, indent=2))
        return

    table = Table(title=f"HATH0R Suite Evaluation Benchmarks ({manifest['suite']})")
    table.add_column("Evaluator Name", style="bold green")
    table.add_column("Evaluator Kind", style="cyan")
    table.add_column("Target Product", style="yellow")
    table.add_column("Min Threshold", justify="right", style="magenta")

    for ev in manifest["evaluators"]:
        table.add_row(
            ev["name"],
            ev["kind"],
            ev["target_product"],
            f"{ev['min_threshold']:.2f}",
        )

    console.print(table)
