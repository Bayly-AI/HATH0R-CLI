"""PMAT Unified Multi-Dimensional Stats & Provability Reporting CLI Group for Hath0r."""

from __future__ import annotations

import json
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..bots.pmat_bot import pmat_bot

console = Console()


@click.group("pmat", help="PMAT Multi-Dimensional Stats, Provability & Complexity Subsystem.")
def pmat_cmd() -> None:
    """PMAT multi-dimensional reporting command group."""
    pass


@pmat_cmd.command("doctor", help="Probe PMAT Bot, stats engine, and contract schema health.")
@click.option("--target", default=None, help="Target repository path.")
@click.option("--json", "as_json", is_flag=True, help="Output diagnostic as JSON.")
def pmat_doctor(target: Optional[str], as_json: bool) -> None:
    """Check health and capabilities of PmatBot and PMAT stats substrate."""
    diag = pmat_bot.doctor(repo_path=target)
    if as_json:
        click.echo(json.dumps(diag, indent=2))
        return

    table = Table(title="PMAT Subsystem & PmatBot Health Diagnostics", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="green")

    table.add_row("Status", str(diag.get("status")))
    table.add_row("Bot Name", str(diag.get("bot_name")))
    table.add_row("Repository Path", str(diag.get("repo_path")))
    table.add_row("Is Git Repository", "✅ Yes" if diag.get("is_git_repository") else "❌ No")
    table.add_row("Schema Contract", str(diag.get("schema_contract")))
    table.add_row("Supported Intents", ", ".join(diag.get("supported_intents", [])))

    console.print(table)


@pmat_cmd.command("stats", help="Query multi-dimensional Code Churn, Provability, and Complexity stats.")
@click.option("--target", default=None, help="Target repository path.")
@click.option("--window", default=30, type=int, help="Churn analysis window in days.")
@click.option("--format", "out_format", type=click.Choice(["table", "json", "markdown"]), default="table", help="Output format.")
@click.option("--threshold", default=0.0, type=float, help="Filter hotspots exceeding minimum risk threshold.")
@click.option("--provability", is_flag=True, help="Include formal provability breakdown.")
@click.option("--complexity", is_flag=True, help="Include AST complexity metrics breakdown.")
def pmat_stats(
    target: Optional[str],
    window: int,
    out_format: str,
    threshold: float,
    provability: bool,
    complexity: bool,
) -> None:
    """Generate multi-dimensional PMAT stats report."""
    report = pmat_bot.get_stats(repo_path=target, window_days=window)

    if threshold > 0.0:
        report["hotspots"] = [h for h in report.get("hotspots", []) if h.get("composite_hotspot_risk_index", 0.0) >= threshold]

    if out_format == "json":
        click.echo(json.dumps(report, indent=2))
        return

    if out_format == "markdown":
        summary = report.get("summary", {})
        md = [
            f"# PMAT Multi-Dimensional Report: {report.get('repository')}",
            f"- **Commit Hash**: `{report.get('commit_hash', 'unknown')[:8]}`",
            f"- **Files Analyzed**: {summary.get('total_files_analyzed')}",
            f"- **Mean Volatility**: {summary.get('mean_volatility_score')}",
            f"- **Mean Provability**: {summary.get('mean_provability_score')}",
            f"- **Mean Complexity**: {summary.get('mean_complexity_score')}",
            f"- **Hotspots (High/Critical)**: {summary.get('hotspot_count')}",
            "\n## Hotspots Ranking",
            "| File Path | Churn Score | Provability Score | Complexity | Composite Risk Index | Risk Tier |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |",
        ]
        for h in report.get("hotspots", []):
            md.append(
                f"| `{h['file_path']}` | {h['churn_score']} | {h['provability_score']} | {h['complexity_score']} | **{h['composite_hotspot_risk_index']}** | `{h['risk_tier']}` |"
            )
        click.echo("\n".join(md))
        return

    summary = report.get("summary", {})
    console.print(
        Panel(
            f"[bold cyan]Repository:[/bold cyan] {report.get('repository')}\n"
            f"[bold cyan]Window:[/bold cyan] {window} days | [bold cyan]Commit:[/bold cyan] {report.get('commit_hash', 'unknown')[:8]}\n"
            f"[bold cyan]Files Analyzed:[/bold cyan] {summary.get('total_files_analyzed', 0)} | "
            f"[bold cyan]Mean Volatility:[/bold cyan] {summary.get('mean_volatility_score', 0.0)}\n"
            f"[bold cyan]Mean Provability Score:[/bold cyan] [bold green]{summary.get('mean_provability_score', 0.0)}[/bold green] | "
            f"[bold cyan]Mean AST Complexity:[/bold cyan] {summary.get('mean_complexity_score', 0.0)}\n"
            f"[bold red]Hotspot Count (>0.50 Risk):[/bold red] {summary.get('hotspot_count', 0)}",
            title="[bold yellow]PMAT Multi-Dimensional Stats & Provability Summary[/bold yellow]",
            border_style="yellow",
        )
    )

    hotspots = report.get("hotspots", [])[:15]
    if hotspots:
        table = Table(title=f"Hotspots Breakdown (Top {len(hotspots)})", border_style="magenta")
        table.add_column("File Path", style="bold cyan")
        table.add_column("Churn", justify="right")

        if provability:
            table.add_column("Provability", justify="right", style="bold green")

        if complexity:
            table.add_column("Complexity", justify="right", style="bold yellow")

        table.add_column("Composite Risk Index", justify="right", style="bold red")
        table.add_column("Risk Tier", justify="center")

        for h in hotspots:
            tier = h.get("risk_tier", "LOW")
            tier_style = "bold red" if tier == "CRITICAL" else ("bold yellow" if tier == "HIGH" else "green")
            row = [h.get("file_path", ""), str(h.get("churn_score", 0.0))]

            if provability:
                row.append(str(h.get("provability_score", 0.0)))
            if complexity:
                row.append(str(h.get("complexity_score", 0.0)))

            row.append(str(h.get("composite_hotspot_risk_index", 0.0)))
            row.append(f"[{tier_style}]{tier}[/{tier_style}]")
            table.add_row(*row)

        console.print(table)


@pmat_cmd.command("bot-run", help="Execute PmatBot conversational query handler.")
@click.argument("intent_text")
@click.option("--target", default=None, help="Target repository path.")
def pmat_bot_run(intent_text: str, target: Optional[str]) -> None:
    """Run PmatBot conversational query."""
    res = pmat_bot.handle_conversational_intent(intent_text=intent_text, repo_path=target)
    click.echo(json.dumps(res, indent=2))
