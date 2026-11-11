"""Root-cause analysis commands (WS9, #591): ``hath0r rca``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import click

from hath0r_cli.commands._qa_common import call, console, emit, show_rows

CODE = "RCA_INVALID_INPUT"


def _bot():
    from hath0r_cli.bots.root_cause_bot import RootCauseBot

    return RootCauseBot(cwd=Path.cwd())


@click.group("rca")
def rca_cmd() -> None:
    """Root cause: tag failures, Pareto, fishbone and 5 Whys."""


@rca_cmd.command("tag")
@click.option("--source", default="manual", show_default=True, help="eval, ci, redteam, andon or manual.")
@click.option("--ref", required=True, help="Id of the failure (eval id, run id, PR number).")
@click.option("--summary", required=True)
@click.option("--category", default=None, help="Cause category (default: classified from the summary).")
@click.option("--gate", default=None)
@click.option("--issue", type=int, default=None)
@click.pass_context
def rca_tag(ctx: click.Context, source: str, ref: str, summary: str, category: Optional[str], gate: Optional[str], issue: Optional[int]) -> None:
    """Tag one failure with a cause category."""
    res = call(ctx, "rca.tag", CODE, lambda: _bot().tag(source=source, ref=ref, summary=summary, category=category, gate=gate, issue=issue))
    if res is not None:
        emit(ctx, "rca.tag", res, lambda: console.print(f"[green]✓[/green] {res['id']} {res['category']} ({res['classified_by']})"))


@rca_cmd.command("pareto")
@click.option("--since", "since", default="30d", show_default=True, help="Window like 30d, or 'all'.")
@click.option("--by", type=click.Choice(["category", "gate", "source"]), default="category", show_default=True)
@click.pass_context
def rca_pareto(ctx: click.Context, since: str, by: str) -> None:
    """Rank causes; the vital few cover 80% of failures."""
    def _run():
        days = None if since == "all" else int(since.rstrip("d"))
        return _bot().pareto(since_days=days, by=by)

    res = call(ctx, "rca.pareto", CODE, _run)
    if res is None:
        return

    def _text() -> None:
        if not res["total"]:
            console.print("[green]No tagged failures in the window.[/green]")
            return
        show_rows(([r[by], r["count"], f"{r['pct']}%", f"{r['cumulative_pct']}%"] for r in res["table"]), (by.title(), "Count", "%", "Cumulative"), f"Pareto of {res['total']} failures")
        console.print(f"  Vital few: {', '.join(res['vital_few'])}")

    emit(ctx, "rca.pareto", res, _text)


@rca_cmd.command("fishbone")
@click.argument("issue", type=int)
@click.option("--problem", default=None)
@click.option("--category", default=None)
@click.option("--cause", default=None, help="Add a cause to the diagram.")
@click.pass_context
def rca_fishbone(ctx: click.Context, issue: int, problem: Optional[str], category: Optional[str], cause: Optional[str]) -> None:
    """Show, or add to, the Ishikawa diagram for an issue."""
    res = call(ctx, "rca.fishbone", CODE, lambda: _bot().fishbone(issue, problem=problem, category=category, cause=cause))
    if res is None:
        return

    def _text() -> None:
        console.print(f"\n[bold cyan]#{issue}[/bold cyan] {res.get('problem') or ''}")
        for cat, causes in res["fishbone"].items():
            console.print(f"  {cat:<12} {'; '.join(causes) if causes else '[dim]—[/dim]'}")

    emit(ctx, "rca.fishbone", res, _text)


@rca_cmd.command("why")
@click.argument("issue", type=int)
@click.option("--problem", required=True)
@click.option("--because", "whys", multiple=True, required=True, help="One answer per 'why?', 3 to 5 times.")
@click.option("--root-cause", default=None)
@click.option("--category", default=None)
@click.pass_context
def rca_why(ctx: click.Context, issue: int, problem: str, whys: Tuple[str, ...], root_cause: Optional[str], category: Optional[str]) -> None:
    """Record a 5 Whys chain and compound it as an insight."""
    res = call(ctx, "rca.why", CODE, lambda: _bot().why(issue, problem, list(whys), root_cause=root_cause, category=category))
    if res is None:
        return

    def _text() -> None:
        w = res["whys"]
        console.print(f"\n[bold cyan]#{issue}[/bold cyan] {w['problem']}")
        for i, a in enumerate(w["chain"], start=1):
            console.print(f"  {i}. why? {a}")
        console.print(f"  [bold]Root cause ({w['category']}):[/bold] {w['root_cause']}")

    emit(ctx, "rca.why", res, _text)
