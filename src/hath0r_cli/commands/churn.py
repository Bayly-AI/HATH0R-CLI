"""PMAT Code Churn & Hotspot Analysis CLI Command Group for Hath0r."""

from __future__ import annotations

import json
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..bots.churn_manager_bot import churn_manager_bot, hotspot_refactor_bot

console = Console()


@click.group("churn", help="PMAT code churn, architectural hotspot analysis, and PR risk review gates.")
def churn() -> None:
    """PMAT code churn & hotspot analysis command group."""
    pass


@churn.command("doctor", help="Probe PMAT binary, MCP registration, and repository status.")
@click.option("--repo", default=None, help="Target repository path.")
@click.option("--json", "as_json", is_flag=True, help="Output diagnostic report as JSON.")
def churn_doctor(repo: Optional[str], as_json: bool) -> None:
    """Check health and capabilities of the PMAT churn analysis subsystem."""
    report = churn_manager_bot.doctor(repo_path=repo)
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    table = Table(title="PMAT Churn Engine Health & Diagnostics", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="green")

    table.add_row("Status", str(report.get("status")))
    table.add_row("Repository Path", str(report.get("repo_path")))
    table.add_row("Is Git Repository", "✅ Yes" if report.get("is_git_repository") else "❌ No")
    table.add_row("PMAT Native Binary", "✅ Installed" if report.get("pmat_native_binary") else "⚡ Using Git Log Substrate")
    table.add_row("Engine Mode", str(report.get("engine_mode")))
    table.add_row("MCP Registered", "✅ Yes (pmat-mcp)" if report.get("mcp_registered") else "⚠️ Not configured")
    table.add_row("Schema Contract", str(report.get("schema_contract")))

    console.print(table)


@churn.command("analyze", help="Run time-windowed code churn analysis across repository worktrees.")
@click.option("--days", default=30, type=int, help="Time window in days for commit churn aggregation.")
@click.option("--repo", default=None, help="Target repository path.")
@click.option("--json", "as_json", is_flag=True, help="Output analysis report as JSON.")
def churn_analyze(days: int, repo: Optional[str], as_json: bool) -> None:
    """Execute commit churn extraction and hotspot ranking."""
    report = churn_manager_bot.analyze(repo_path=repo, days=days)
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    summary = report.get("summary", {})
    console.print(
        Panel(
            f"[bold cyan]Repository:[/bold cyan] {report.get('repository')}\n"
            f"[bold cyan]Analysis Window:[/bold cyan] {days} days (HEAD: {report.get('commit_hash', 'unknown')[:8]})\n"
            f"[bold cyan]Files Analyzed:[/bold cyan] {summary.get('total_files_analyzed', 0)} | "
            f"[bold cyan]Commits:[/bold cyan] {summary.get('total_commits_evaluated', 0)} | "
            f"[bold cyan]Total Churn:[/bold cyan] {summary.get('total_churn_lines', 0)} lines\n"
            f"[bold cyan]Mean Volatility:[/bold cyan] {summary.get('mean_volatility_score', 0.0)} | "
            f"[bold red]Hotspots (>0.50):[/bold red] {summary.get('hotspot_count', 0)}",
            title="[bold yellow]PMAT Code Churn Analysis Summary[/bold yellow]",
            border_style="yellow",
        )
    )

    hotspots = report.get("hotspots", [])[:10]
    if hotspots:
        table = Table(title=f"Top {len(hotspots)} Architectural Hotspots", border_style="magenta")
        table.add_column("File Path", style="bold cyan")
        table.add_column("Churn", justify="right")
        table.add_column("Complexity", justify="right")
        table.add_column("Volatility", justify="right")
        table.add_column("Risk Tier", justify="center")

        for h in hotspots:
            tier = h.get("risk_tier", "LOW")
            tier_style = "bold red" if tier == "CRITICAL" else ("bold yellow" if tier == "HIGH" else "green")
            table.add_row(
                h.get("file_path", ""),
                str(h.get("churn_count", 0)),
                str(h.get("complexity_score", 0.0)),
                str(h.get("volatility_score", 0.0)),
                f"[{tier_style}]{tier}[/{tier_style}]",
            )
        console.print(table)


@churn.command("hotspots", help="Extract ranked architectural hotspots by volatility score.")
@click.option("--days", default=30, type=int, help="Time window in days.")
@click.option("--limit", default=10, type=int, help="Max hotspot records to display.")
@click.option("--repo", default=None, help="Target repository path.")
@click.option("--json", "as_json", is_flag=True, help="Output hotspots as JSON.")
def churn_hotspots(days: int, limit: int, repo: Optional[str], as_json: bool) -> None:
    """List ranked architectural hotspots."""
    hotspots = churn_manager_bot.hotspots(repo_path=repo, days=days, limit=limit)
    if as_json:
        click.echo(json.dumps(hotspots, indent=2))
        return

    table = Table(title=f"Top {len(hotspots)} Code Hotspots", border_style="red")
    table.add_column("Rank", justify="right")
    table.add_column("File Path", style="bold white")
    table.add_column("Churn Commits", justify="right")
    table.add_column("Complexity", justify="right")
    table.add_column("Volatility Score", justify="right", style="bold magenta")
    table.add_column("Risk Tier", justify="center")
    table.add_column("Co-Changing Files", style="italic cyan")

    for i, h in enumerate(hotspots, 1):
        tier = h.get("risk_tier", "LOW")
        tier_style = "bold red" if tier == "CRITICAL" else ("bold yellow" if tier == "HIGH" else "green")
        co_files = ", ".join(h.get("co_changing_files", [])[:2]) or "none"
        table.add_row(
            str(i),
            h.get("file_path", ""),
            str(h.get("churn_count", 0)),
            str(h.get("complexity_score", 0.0)),
            str(h.get("volatility_score", 0.0)),
            f"[{tier_style}]{tier}[/{tier_style}]",
            co_files,
        )
    console.print(table)


@churn.command("pr-risk", help="Evaluate git diff churn risk for PR review gates.")
@click.option("--base", default="development", help="Base target branch.")
@click.option("--repo", default=None, help="Target repository path.")
@click.option("--json", "as_json", is_flag=True, help="Output risk evaluation as JSON.")
def churn_pr_risk(base: str, repo: Optional[str], as_json: bool) -> None:
    """Evaluate current work branch risk against base branch."""
    eval_result = churn_manager_bot.pr_risk(repo_path=repo, base_branch=base)
    if as_json:
        click.echo(json.dumps(eval_result, indent=2))
        return

    risk_tier = eval_result.get("overall_risk_tier", "LOW")
    risk_style = "bold red" if risk_tier == "CRITICAL" else ("bold yellow" if risk_tier == "HIGH" else "green")
    safe = eval_result.get("safe_to_merge", True)

    console.print(
        Panel(
            f"[bold cyan]Base Branch:[/bold cyan] {eval_result.get('base_branch')}\n"
            f"[bold cyan]Changed Files:[/bold cyan] {eval_result.get('changed_files_count', 0)}\n"
            f"[bold cyan]Max Volatility Score:[/bold cyan] {eval_result.get('max_volatility_score', 0.0)}\n"
            f"[bold cyan]Overall Risk Tier:[/bold cyan] [{risk_style}]{risk_tier}[/{risk_style}]\n"
            f"[bold cyan]Recommended Reasoning Tier:[/bold cyan] [bold magenta]{eval_result.get('recommended_reasoning_tier')}[/bold magenta]\n"
            f"[bold cyan]PR Review Gate:[/bold cyan] {'[green]PASS (Safe to merge)[/green]' if safe else '[bold red]BLOCK (Requires architectural review)[/bold red]'}",
            title="[bold yellow]PR Churn & Volatility Risk Evaluation[/bold yellow]",
            border_style="yellow",
        )
    )


@churn.command("ui", help="Render and view Generative UI Churn Heatmap dashboard.")
@click.option("--days", default=30, type=int, help="Time window in days.")
@click.option("--repo", default=None, help="Target repository path.")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open HTML report in default browser.")
def churn_ui(days: int, repo: Optional[str], open_browser: bool) -> None:
    """Render interactive Generative UI Churn Heatmap widget."""
    html_content = churn_manager_bot.render_ui_html(repo_path=repo, days=days)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False)
    tmp.write(html_content)
    tmp.close()

    console.print(f"[green]Generative UI Churn Heatmap rendered to:[/green] [bold white]{tmp.name}[/bold white]")
    if open_browser:
        webbrowser.open(f"file://{tmp.name}")


@churn.command("refactor-plan", help="Propose decoupled refactoring plan for a hotspot module.")
@click.argument("file_path")
@click.option("--repo", default=None, help="Target repository path.")
@click.option("--json", "as_json", is_flag=True, help="Output refactoring plan as JSON.")
def churn_refactor_plan(file_path: str, repo: Optional[str], as_json: bool) -> None:
    """Propose modular refactoring plan using HotspotRefactorBot."""
    plan = hotspot_refactor_bot.propose_refactoring(file_path=file_path, repo_path=repo)
    if as_json:
        click.echo(json.dumps(plan, indent=2))
        return

    if "error" in plan:
        console.print(f"[bold red]Error:[/bold red] {plan['error']}")
        return

    console.print(
        Panel(
            f"[bold cyan]File:[/bold cyan] {plan.get('file_path')} ({plan.get('line_count')} lines)\n"
            f"[bold cyan]Refactoring Type:[/bold cyan] {plan.get('refactoring_type')}\n"
            f"[bold cyan]Suggested Pattern:[/bold cyan] {plan.get('suggested_pattern')}\n\n"
            + "\n".join(f"[bold yellow]{i+1}.[/bold yellow] {s}" for i, s in enumerate(plan.get("proposed_steps", []))),
            title="[bold green]Hotspot Refactoring Proposal[/bold green]",
            border_style="green",
        )
    )
