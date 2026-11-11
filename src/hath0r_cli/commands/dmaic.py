"""DMAIC improvement project commands (WS7, #592): ``hath0r dmaic``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from hath0r_cli.commands._qa_common import Diagnostic, call, console, emit

CODE = "DMAIC_INVALID_INPUT"


def _bot():
    from hath0r_cli.bots.dmaic_project_bot import DMAICProjectBot

    return DMAICProjectBot(cwd=Path.cwd())


def _summary(res) -> None:
    console.print(f"\n[bold cyan]DMAIC #{res['issue']}[/bold cyan] · CTQ {res['ctq']} ({res.get('goal')}) · phase [bold]{res['phase']}[/bold]")
    b = res.get("baseline") or {}
    if b:
        console.print(f"  • Baseline: n={b.get('n')} center={b.get('center')} status={b.get('status')}")
    if res.get("analysis"):
        console.print(f"  • Root cause ({res['analysis']['category']}): {res['analysis']['root_cause']}")
    if res.get("change"):
        console.print(f"  • Change after point {res['change']['after_point']}: {res['change']['description']}")
    c = res.get("control") or {}
    if c:
        console.print(f"  • Control: {c['points_after_change']}/{c['required']} points, status {c.get('status')}, ready={c['ready_to_close']}")


@click.group("dmaic")
def dmaic_cmd() -> None:
    """Define-Measure-Analyze-Improve-Control improvement projects."""


@dmaic_cmd.command("start")
@click.argument("issue", type=int)
@click.option("--ctq", required=True, help="Critical-to-quality metric (any 'hath0r spc' metric).")
@click.option("--problem", default="", help="Problem statement.")
@click.option("--target", type=float, default=None)
@click.option("--goal", type=click.Choice(["maximize", "minimize"]), default="maximize", show_default=True)
@click.pass_context
def dmaic_start(ctx: click.Context, issue: int, ctq: str, problem: str, target: Optional[float], goal: str) -> None:
    """Define the project and take the Measure baseline."""
    res = call(ctx, "dmaic.start", CODE, lambda: _bot().start(issue, ctq, problem=problem, target=target, goal=goal))
    if res is not None:
        emit(ctx, "dmaic.start", res, lambda: _summary(res))


@dmaic_cmd.command("analyze")
@click.argument("issue", type=int)
@click.pass_context
def dmaic_analyze(ctx: click.Context, issue: int) -> None:
    """Attach the 5 Whys root cause (from 'hath0r rca why') and the Pareto."""
    res = call(ctx, "dmaic.analyze", CODE, lambda: _bot().analyze(issue))
    if res is not None:
        emit(ctx, "dmaic.analyze", res, lambda: _summary(res))


@dmaic_cmd.command("improve")
@click.argument("issue", type=int)
@click.option("--change", required=True, help="What changed (PR, config, rule).")
@click.pass_context
def dmaic_improve(ctx: click.Context, issue: int, change: str) -> None:
    """Record the change; control points are counted from here."""
    res = call(ctx, "dmaic.improve", CODE, lambda: _bot().improve(issue, change))
    if res is not None:
        emit(ctx, "dmaic.improve", res, lambda: _summary(res))


@dmaic_cmd.command("status")
@click.argument("issue", type=int, required=False)
@click.pass_context
def dmaic_status(ctx: click.Context, issue: Optional[int]) -> None:
    """One project (with its control chart) or all projects."""
    def _run():
        return _bot().control(issue) if issue is not None and "change" in _bot().load(issue) else _bot().status(issue)

    res = call(ctx, "dmaic.status", CODE, _run)
    if res is None:
        return

    def _text() -> None:
        if issue is not None:
            _summary(res)
            return
        for p in res["projects"]:
            console.print(f"  #{p['issue']} {p['phase']:<8} CTQ {p['ctq']}  {p.get('problem') or ''}")
        if not res["projects"]:
            console.print("[dim]No DMAIC projects.[/dim]")

    emit(ctx, "dmaic.status", res, _text)


@dmaic_cmd.command("close")
@click.argument("issue", type=int)
@click.pass_context
def dmaic_close(ctx: click.Context, issue: int) -> None:
    """Close only when the CTQ chart shows 20+ in-control points after the change."""
    res = call(ctx, "dmaic.close", CODE, lambda: _bot().close(issue))
    if res is None:
        return
    diags = [Diagnostic(code="DMAIC_CLOSE_REFUSED", severity="error", message=res["reason"])] if res.get("refused") else []

    def _text() -> None:
        if res.get("refused"):
            console.print(f"[yellow]{res['reason']}[/yellow]")
        else:
            _summary(res)

    emit(ctx, "dmaic.close", res, _text, diagnostics=diags, exit_on_failure=True)
