"""
Arize Phoenix CLI Command Group for HATH0R.

Provides first-class CLI commands for launching, stopping, inspecting,
and evaluating AI agents with Arize Phoenix open-source observability.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
import urllib.error
import webbrowser
from typing import Any, Dict, Optional
import click
from rich.console import Console
from rich.table import Table
from ..telemetry import load_otel_config
from ..bots.phoenix_observer_bot import phoenix_observer_bot

console = Console()


@click.group("phoenix", help="Arize Phoenix agent observability, traces, and LLM-as-a-judge evaluations.")
def phoenix_cmd() -> None:
    """Arize Phoenix observability command suite."""
    pass


@phoenix_cmd.command("status", help="Check Arize Phoenix collector and UI availability.")
@click.option("--endpoint", default=None, help="Custom Phoenix OTLP/HTTP endpoint.")
@click.option("--json", "as_json", is_flag=True, help="Output status as JSON.")
def phoenix_status(endpoint: Optional[str], as_json: bool) -> None:
    """Check Arize Phoenix server status and connection parameters."""
    bot = phoenix_observer_bot
    if endpoint:
        bot.custom_endpoint = endpoint

    res = bot.check_health()
    cfg = load_otel_config()

    if as_json:
        payload = {
            "service": res["service"],
            "environment": res["environment"],
            "target_url": res["target_url"],
            "healthy": res["healthy"],
            "http_status": res["http_status"],
            "otlp_endpoint": cfg.otlp_endpoint or "http://1NPHOENIX:4318",
            "error": res["error"],
        }
        click.echo(json.dumps(payload, indent=2))
        return

    console.print(f"[bold cyan]Arize Phoenix Observability Status:[/bold cyan]")
    console.print(f"  • Service Name:    {cfg.service_name}")
    console.print(f"  • Environment:     {cfg.deployment_environment}")
    console.print(f"  • OTLP Target:     {cfg.otlp_endpoint or 'http://1NPHOENIX:4318'}")
    console.print(f"  • Phoenix UI:      {res['target_url']}")

    if res["healthy"]:
        console.print("  [bold green]✓ Phoenix Server is ACTIVE and responding (HTTP 200).[/bold green]")
    else:
        console.print(f"  [yellow]! Phoenix Server at {res['target_url']} is OFFLINE (Error: {res['error'] or 'Unreachable'})[/yellow]")
        console.print("    [dim]To start Phoenix locally: 'hath0r phoenix up' or 'docker compose -p 1-nation up -d 1n-phoenix'[/dim]")


@phoenix_cmd.command("up", help="Start the Arize Phoenix container locally.")
@click.option("--detach/--no-detach", default=True, help="Run in background mode.")
def phoenix_up(detach: bool) -> None:
    """Launch the 1NPHOENIX container using Docker."""
    console.print("[cyan]Starting 1NPHOENIX container via Docker...[/cyan]")
    cmd = ["docker", "compose", "-p", "1-nation", "up", "-d", "1n-phoenix"] if detach else ["docker", "compose", "-p", "1-nation", "up", "1n-phoenix"]
    try:
        subprocess.run(cmd, check=True)
        console.print("[bold green]✓ 1NPHOENIX started successfully.[/bold green]")
        console.print("  • UI: http://localhost:58000/phoenix/ (via 1NEDGE) or http://localhost:6006")
        console.print("  • OTLP: http://localhost:4318")
    except Exception as exc:
        console.print(f"[bold red]Failed to start 1NPHOENIX container: {exc}[/bold red]")


@phoenix_cmd.command("down", help="Stop the Arize Phoenix container.")
def phoenix_down() -> None:
    """Stop the 1NPHOENIX container."""
    console.print("[cyan]Stopping 1NPHOENIX container...[/cyan]")
    try:
        subprocess.run(["docker", "compose", "-p", "1-nation", "stop", "1n-phoenix"], check=True)
        console.print("[bold green]✓ 1NPHOENIX stopped.[/bold green]")
    except Exception as exc:
        console.print(f"[bold red]Failed to stop 1NPHOENIX container: {exc}[/bold red]")


@phoenix_cmd.command("ui", help="Open the Arize Phoenix Web UI in browser.")
@click.option("--edge/--direct", default=True, help="Use 1NEDGE proxy or direct port 6006.")
def phoenix_ui(edge: bool) -> None:
    """Open Phoenix UI in the default web browser."""
    url = "http://localhost:58000/phoenix/" if edge else "http://localhost:6006"
    console.print(f"[cyan]Opening Phoenix UI: {url}[/cyan]")
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
