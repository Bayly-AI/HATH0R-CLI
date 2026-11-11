"""FMEA commands (WS4, #590): ``hath0r fmea``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from hath0r_cli.commands._qa_common import call, console, emit, show_rows

CODE = "FMEA_INVALID_INPUT"


def _bot():
    from hath0r_cli.bots.fmea_bot import FMEABot

    return FMEABot(cwd=Path.cwd())


def _rows_text(rows, title: str = "") -> None:
    show_rows(
        ([r.get("process", ""), r["id"], r["action_priority"], r["severity"], r["occurrence"], r["detection"], r["rpn"], r["step"], r["failure_mode"], r.get("issue") or ""] for r in rows),
        ("Process", "Id", "AP", "S", "O", "D", "RPN", "Step", "Failure mode", "Issue"),
        title,
    )


@click.group("fmea")
def fmea_cmd() -> None:
    """Failure mode and effects analysis of Hath0r workflows."""


@fmea_cmd.command("init")
@click.argument("process")
@click.option("--factory", default=None, help="Factory YAML (default cfg/factories/<process>-factory.yaml).")
@click.option("--force", is_flag=True, help="Reseed an existing worksheet.")
@click.pass_context
def fmea_init(ctx: click.Context, process: str, factory: Optional[str], force: bool) -> None:
    """Create .hath0r/fmea/<process>.yaml seeded with the 14 multi-agent failure modes."""
    res = call(ctx, "fmea.init", CODE, lambda: _bot().init(process, factory=factory, force=force))
    if res is not None:
        emit(ctx, "fmea.init", res, lambda: console.print(f"[green]✓[/green] {res['rows']} rows ({res['steps_mapped']} mapped to steps) in {res['path']}"))


@fmea_cmd.command("add")
@click.argument("process")
@click.option("--step", required=True)
@click.option("--mode", "failure_mode", required=True, help="Failure mode.")
@click.option("--effect", required=True)
@click.option("--cause", required=True)
@click.option("-s", "--severity", type=int, required=True)
@click.option("-o", "--occurrence", type=int, required=True)
@click.option("-d", "--detection", type=int, required=True)
@click.option("--detected-by", default="", help="Bot that would catch it.")
@click.option("--signal", default=None, help="Data signal for occurrence: eval_fail_rate, tier:<name>, andon:<source>, msa:missed_defects.")
@click.pass_context
def fmea_add(ctx: click.Context, process: str, step: str, failure_mode: str, effect: str, cause: str, severity: int, occurrence: int, detection: int, detected_by: str, signal: Optional[str]) -> None:
    """Add a failure mode row."""
    res = call(ctx, "fmea.add", CODE, lambda: _bot().add(process, step=step, failure_mode=failure_mode, effect=effect, cause=cause, severity=severity, occurrence=occurrence, detection=detection, detected_by=detected_by, signal=signal))
    if res is not None:
        emit(ctx, "fmea.add", res, lambda: _rows_text([res["row"]]))


@fmea_cmd.command("update")
@click.argument("process")
@click.argument("row_id")
@click.option("-s", "--severity", type=int, default=None)
@click.option("-o", "--occurrence", type=int, default=None)
@click.option("-d", "--detection", type=int, default=None)
@click.option("--detected-by", default=None)
@click.option("--action", default=None, help="What was done (recorded on the row).")
@click.option("--issue", type=int, default=None, help="Link an existing GitHub issue to the row.")
@click.pass_context
def fmea_update(ctx: click.Context, process: str, row_id: str, severity: Optional[int], occurrence: Optional[int], detection: Optional[int], detected_by: Optional[str], action: Optional[str], issue: Optional[int]) -> None:
    """Re-rate a row after an action, or link it to an issue."""
    res = call(ctx, "fmea.update", CODE, lambda: _bot().update(process, row_id, severity=severity, occurrence=occurrence, detection=detection, detected_by=detected_by, action=action, issue=issue))
    if res is not None:
        emit(ctx, "fmea.update", res, lambda: _rows_text([res["row"]]))


@fmea_cmd.command("score")
@click.argument("process")
@click.option("--no-refresh", is_flag=True, help="Do not refresh occurrence from eval/andon/msa data.")
@click.pass_context
def fmea_score(ctx: click.Context, process: str, no_refresh: bool) -> None:
    """Refresh occurrence from data, rescore and rank."""
    res = call(ctx, "fmea.score", CODE, lambda: _bot().score(process, refresh=not no_refresh))
    if res is None:
        return

    def _text() -> None:
        _rows_text(res["rows"], f"{process}: {res['high']} high, {res['medium']} medium, {res['low']} low")
        for r in res["refreshed"]:
            console.print(f"  • {r['id']} occurrence {r['from']} → {r['to']} (observed rate {r['rate']})")

    emit(ctx, "fmea.score", res, _text)


@fmea_cmd.command("report")
@click.option("--process", default=None, help="One worksheet (default: all).")
@click.option("--top", type=int, default=10, show_default=True)
@click.pass_context
def fmea_report(ctx: click.Context, process: Optional[str], top: int) -> None:
    """Highest-priority failure modes across worksheets."""
    res = call(ctx, "fmea.report", CODE, lambda: _bot().report(process, top=top))
    if res is not None:
        emit(ctx, "fmea.report", res, lambda: _rows_text(res["top"], f"Top {top}: {res['high']} high-priority rows in {len(res['processes'])} worksheet(s)"))


@fmea_cmd.command("sync-issues")
@click.argument("process")
@click.option("--repo", default="Bayly-AI/HATH0R-CLI", show_default=True)
@click.option("--min-priority", type=click.Choice(["H", "M", "L"]), default="H", show_default=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def fmea_sync_issues(ctx: click.Context, process: str, repo: str, min_priority: str, dry_run: bool) -> None:
    """File a GitHub issue for each high-priority row that has none."""
    res = call(ctx, "fmea.sync-issues", CODE, lambda: _bot().sync_issues(process, repo=repo, min_priority=min_priority, dry_run=dry_run))
    if res is None:
        return

    def _text() -> None:
        for c in res["created"]:
            console.print(f"  [green]✓[/green] {c['id']} → {c.get('url') or ('dry run' if c['dry_run'] else c.get('issue'))}")
        for f in res["failed"]:
            console.print(f"  [red]✗[/red] {f['id']}: {f['error']}")
        console.print(f"  {len(res['skipped'])} row(s) already have issues")

    emit(ctx, "fmea.sync-issues", res, _text, exit_on_failure=True)


@fmea_cmd.command("export")
@click.argument("process")
@click.option("--min-priority", type=click.Choice(["H", "M", "L"]), default="M", show_default=True)
@click.pass_context
def fmea_export(ctx: click.Context, process: str, min_priority: str) -> None:
    """Export rows to AgentGraph (as memory concept nodes) so 'hath0r agentgraph query' finds them."""
    res = call(ctx, "fmea.export", CODE, lambda: _bot().export_agentgraph(process, min_priority=min_priority))
    if res is not None:
        emit(ctx, "fmea.export", res, lambda: console.print(f"[green]✓[/green] exported {len(res['exported'])} node(s); run 'hath0r agentgraph sync'"))
