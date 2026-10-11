"""
MLflow CLI Command Group for HATH0R.

Provides first-class CLI commands for launching, stopping, inspecting,
querying experiments, and tracking continuous calibration runs with MLflow.
"""

from __future__ import annotations

import json
import webbrowser
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from ..bots.mlflow_manager_bot import mlflow_manager_bot
from ..telemetry import load_otel_config

console = Console()


@click.group("mlflow", help="MLflow MLOps experiment tracking, model registry, and CCCD calibration runs.")
def mlflow_cmd() -> None:
    """MLflow MLOps and experiment tracking command suite."""
    pass


@mlflow_cmd.command("status", help="Check MLflow tracking server and UI availability.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
@click.option("--endpoint", default=None, help="Custom MLflow HTTP/API endpoint.")
@click.option("--json", "as_json", is_flag=True, help="Output status as JSON.")
def mlflow_status(group: str, endpoint: Optional[str], as_json: bool) -> None:
    """Check MLflow server status and connection parameters."""
    res = mlflow_manager_bot.check_status(group=group, custom_endpoint=endpoint)
    cfg = load_otel_config()

    if as_json:
        payload = {
            "group": group,
            "container": res["container"],
            "service": cfg.service_name,
            "environment": cfg.deployment_environment,
            "active_url": res["active_url"],
            "target_url": res["active_url"] or f"http://localhost:38000/mlflow/",
            "healthy": res["healthy"],
            "http_status": res["http_status"],
            "error": res["error"],
        }
        click.echo(json.dumps(payload, indent=2))
        return

    console.print(f"[bold cyan]MLflow Experiment Tracking Status ({group.upper()}):[/bold cyan]")
    console.print(f"  • Container:       {res['container']}")
    console.print(f"  • Service Name:    {cfg.service_name}")
    console.print(f"  • Environment:     {cfg.deployment_environment}")
    console.print(f"  • Active UI:       {res['active_url'] or 'Offline'}")

    if res["healthy"]:
        console.print("  [bold green]✓ MLflow Server is ACTIVE and responding (HTTP 200).[/bold green]")
    else:
        console.print(f"  [yellow]! MLflow Server is OFFLINE (Error: {res['error'] or 'Unreachable'})[/yellow]")
        console.print(f"    [dim]To start MLflow locally: 'hath0r mlflow up --group {group}'[/dim]")


@mlflow_cmd.command("up", help="Start the MLflow tracking container locally.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
@click.option("--detach/--no-detach", default=True, help="Run in background mode.")
def mlflow_up(group: str, detach: bool) -> None:
    """Launch the MLflow container using Docker."""
    console.print(f"[cyan]Starting MLflow container for group '{group}'...[/cyan]")
    res = mlflow_manager_bot.start_mlflow(group=group, detach=detach)
    if res["success"]:
        console.print(f"[bold green]✓ {res['container']} started successfully.[/bold green]")
        console.print(f"  • UI: {res['edge_url']} or {res['direct_url']}")
    else:
        console.print(f"[bold red]Failed to start {res['container']}: {res['error']}[/bold red]")


@mlflow_cmd.command("down", help="Stop the MLflow tracking container.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
def mlflow_down(group: str) -> None:
    """Stop the MLflow container."""
    console.print(f"[cyan]Stopping MLflow container for group '{group}'...[/cyan]")
    res = mlflow_manager_bot.stop_mlflow(group=group)
    if res["success"]:
        console.print(f"[bold green]✓ {res['container']} stopped successfully.[/bold green]")
    else:
        console.print(f"[bold red]Failed to stop {res['container']}: {res['error']}[/bold red]")


@mlflow_cmd.command("ui", help="Open the MLflow Web UI in default browser.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
@click.option("--edge/--direct", default=True, help="Use Edge proxy or direct port.")
def mlflow_ui(group: str, edge: bool) -> None:
    """Open MLflow UI in the default web browser."""
    group_cfg = mlflow_manager_bot.GROUP_COMPOSE_MAP.get(group, mlflow_manager_bot.GROUP_COMPOSE_MAP["hath0r"])
    url = group_cfg["edge_url"] if edge else group_cfg["direct_url"]
    console.print(f"[cyan]Opening MLflow UI for group '{group}': {url}[/cyan]")
    webbrowser.open(url)


@mlflow_cmd.command("experiments", help="List registered MLflow experiments.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
@click.option("--endpoint", default=None, help="Custom MLflow HTTP endpoint.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def mlflow_experiments(group: str, endpoint: Optional[str], as_json: bool) -> None:
    """Display registered MLflow experiments."""
    exps = mlflow_manager_bot.get_experiments(group=group, custom_endpoint=endpoint)

    if as_json:
        click.echo(json.dumps(exps, indent=2))
        return

    table = Table(title=f"MLflow Experiments ({group.upper()})")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Experiment Name", style="bold green")
    table.add_column("Artifact Location", style="cyan")
    table.add_column("Stage", style="magenta")

    for exp in exps:
        table.add_row(
            str(exp.get("experiment_id", "")),
            str(exp.get("name", "")),
            str(exp.get("artifact_location", "")),
            str(exp.get("lifecycle_stage", "active")),
        )

    console.print(table)


@mlflow_cmd.command("runs", help="List runs for a specific MLflow experiment.")
@click.option("--experiment-id", "-e", default="0", help="MLflow Experiment ID.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
@click.option("--endpoint", default=None, help="Custom MLflow HTTP endpoint.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def mlflow_runs(experiment_id: str, group: str, endpoint: Optional[str], as_json: bool) -> None:
    """Display runs for the designated experiment."""
    runs = mlflow_manager_bot.get_runs(experiment_id=experiment_id, group=group, custom_endpoint=endpoint)

    if as_json:
        click.echo(json.dumps(runs, indent=2))
        return

    table = Table(title=f"MLflow Runs for Experiment ID {experiment_id} ({group.upper()})")
    table.add_column("Run ID", style="dim")
    table.add_column("Run Name", style="bold green")
    table.add_column("Status", style="cyan")
    table.add_column("Artifacts", style="magenta")

    for r in runs:
        info = r.get("info", {})
        table.add_row(
            str(info.get("run_id", "")[:12]),
            str(info.get("run_name", "unnamed")),
            str(info.get("status", "")),
            str(info.get("artifact_uri", "")),
        )

    console.print(table)


@mlflow_cmd.command("log", help="Manually log an experiment run with parameters and metrics.")
@click.option("--experiment", "-e", default="cccd-calibration", help="Experiment name.")
@click.option("--name", "-n", default="cli_logged_run", help="Run name.")
@click.option("--param", "-p", "params", multiple=True, help="Parameter in key=value format.")
@click.option("--metric", "-m", "metrics", multiple=True, help="Metric in key=value format.")
@click.option(
    "--group",
    default="hath0r",
    type=click.Choice(["hath0r", "1-nation", "bai"]),
    help="Docker group name.",
)
def mlflow_log(
    experiment: str,
    name: str,
    params: List[str],
    metrics: List[str],
    group: str,
) -> None:
    """Log parameters and metrics to an MLflow run."""
    param_dict = {}
    for p in params:
        if "=" in p:
            k, v = p.split("=", 1)
            param_dict[k.strip()] = v.strip()

    metric_dict = {}
    for m in metrics:
        if "=" in m:
            k, v = m.split("=", 1)
            try:
                metric_dict[k.strip()] = float(v.strip())
            except ValueError:
                console.print(f"[yellow]Skipping non-numeric metric '{m}'[/yellow]")

    run_id = mlflow_manager_bot.log_run(
        experiment_name=experiment,
        run_name=name,
        params=param_dict,
        metrics=metric_dict,
        group=group,
    )

    if run_id:
        console.print(f"[bold green]✓ Successfully logged MLflow run '{run_id}' under experiment '{experiment}'.[/bold green]")
    else:
        console.print(f"[bold red]Failed to log MLflow run under experiment '{experiment}'.[/bold red]")
