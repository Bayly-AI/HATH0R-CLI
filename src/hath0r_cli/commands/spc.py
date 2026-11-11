"""Statistical Process Control commands (WS2/WS3, #586, #587): ``hath0r spc``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from hath0r_cli.commands._qa_common import fail
from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.envelope import Diagnostic

METRIC_HELP = "Metric: r_task, deterministic, trajectory, adversarial, goal_alignment, eval_duration_ms, total_tokens, cost_usd, latency_ms."


def _bot():
    from hath0r_cli.bots.spc_monitor_bot import SPCMonitorBot

    return SPCMonitorBot(cwd=Path.cwd())


def _bad_metric(ctx: click.Context, command: str, exc: ValueError) -> None:
    fail(ctx, command, "SPC_INVALID_INPUT", exc)


@click.group("spc")
def spc_cmd() -> None:
    """Control charts and capability for evals, tokens and cost (warnings by default)."""


@spc_cmd.command("status")
@click.pass_context
def spc_status(ctx: click.Context) -> None:
    """Chart every metric and report signals and R_task capability."""
    res = _bot().status()
    diags = [Diagnostic(code="SPC_SIGNAL", severity="error" if res["blocking"] else "warning", message=w) for w in res["warnings"]]
    response = _build_response(ctx, command="spc.status", state="failed" if res["blocking"] else "ok", data=res, diagnostics=diags)

    def _text() -> None:
        console.print(f"\n[bold cyan]SPC status[/bold cyan] (mode: {res['mode']})")
        t = Table(show_header=True, header_style="bold")
        for col in ("Metric", "Status", "n", "Center", "LCL", "UCL", "Latest", "Signals"):
            t.add_column(col)
        for m, s in res["metrics"].items():
            if s["status"] == "insufficient_data":
                t.add_row(m, "[dim]no data[/dim]", str(s["n"]), "", "", "", "", "")
                continue
            colour = "green" if "in_control" in s["status"] else "yellow"
            t.add_row(m, f"[{colour}]{s['status']}[/{colour}]", str(s["n"]), f"{s['center']:.4g}", f"{s['lcl']:.4g}", f"{s['ucl']:.4g}", f"{s['latest']:.4g}", str(s["signals"]))
        console.print(t)
        cap = res["capability"]
        if cap.get("cpk") is not None:
            console.print(f"  • R_task Cpk {cap['cpk']:.2f} / Ppk {cap['ppk']:.2f} against LSL {cap['lsl']} (warn below {cap['min_cpk_warn']})")
        for w in res["warnings"]:
            console.print(f"  [yellow]⚠ {w}[/yellow]")

    _emit_response(ctx, response, text_renderer=_text)
    if res["blocking"]:
        ctx.exit(1)


@spc_cmd.command("chart")
@click.option("--metric", "-m", default="r_task", show_default=True, help=METRIC_HELP)
@click.option("--lam", type=float, default=None, help="EWMA lambda (default from thresholds.json, 0.2).")
@click.pass_context
def spc_chart(ctx: click.Context, metric: str, lam: Optional[float]) -> None:
    """I-MR, EWMA and CUSUM chart for one metric."""
    try:
        res = _bot().chart(metric, lam=lam)
    except ValueError as exc:
        _bad_metric(ctx, "spc.chart", exc)
        return
    response = _build_response(ctx, command="spc.chart", state="ok", data=res)

    def _text() -> None:
        if res.get("status") == "insufficient_data":
            console.print(f"[yellow]{metric}: not enough data ({res['n']} points)[/yellow]")
            return
        b = res["baseline"]
        console.print(f"\n[bold cyan]{metric}[/bold cyan]: {res['status']} · n={res['n']} · center {b['center']:.4g} · limits [{b['lcl']:.4g}, {b['ucl']:.4g}]")
        flagged = set(res["signal_indices"])
        for i, p in enumerate(res["points"][-20:], start=max(0, res["n"] - 20)):
            mark = "[red]●[/red]" if i in flagged else "·"
            console.print(f"  {mark} {i + 1:>3} {p['value']:.4g}  {p['id']}")
        for r in res["western_electric"][-5:]:
            console.print(f"  [yellow]rule {r['rule']} at point {r['index'] + 1}: {r['description']}[/yellow]")

    _emit_response(ctx, response, text_renderer=_text)


@spc_cmd.command("baseline")
@click.option("--metric", "-m", default="r_task", show_default=True, help=METRIC_HELP)
@click.option("--points", type=int, default=None, help="Observations to freeze limits from (default 20).")
@click.option("--recent", is_flag=True, help="Use the most recent points (after a deliberate process change).")
@click.option("--dry-run", is_flag=True, help="Compute limits without saving them.")
@click.pass_context
def spc_baseline(ctx: click.Context, metric: str, points: Optional[int], recent: bool, dry_run: bool) -> None:
    """Freeze phase 1 control limits for a metric in .hath0r/spc/baselines.json."""
    try:
        res = _bot().baseline(metric, points=points, recent=recent, dry_run=dry_run)
    except ValueError as exc:
        _bad_metric(ctx, "spc.baseline", exc)
        return
    diags = [Diagnostic(code="SPC_PROVISIONAL_BASELINE", severity="warning", message=res["warning"])] if res.get("warning") else []
    response = _build_response(ctx, command="spc.baseline", state="ok" if res["success"] else "error", data=res, diagnostics=diags)

    def _text() -> None:
        if not res["success"]:
            console.print(f"[red]{res['error']}[/red]")
            return
        console.print(f"[green]✓[/green] {metric} baseline from {res['points']} points: center {res['center']:.4g}, limits [{res['lcl']:.4g}, {res['ucl']:.4g}]")
        if res.get("warning"):
            console.print(f"  [yellow]⚠ {res['warning']}[/yellow]")

    _emit_response(ctx, response, text_renderer=_text)


@spc_cmd.command("capability")
@click.option("--metric", "-m", default="r_task", show_default=True, help=METRIC_HELP)
@click.option("--lsl", type=float, default=None, help="Lower spec limit (r_task defaults to the eval threshold).")
@click.option("--usl", type=float, default=None, help="Upper spec limit.")
@click.pass_context
def spc_capability(ctx: click.Context, metric: str, lsl: Optional[float], usl: Optional[float]) -> None:
    """Cp/Cpk (within) and Pp/Ppk (overall) against spec limits."""
    try:
        res = _bot().capability(metric, lsl=lsl, usl=usl)
    except ValueError as exc:
        _bad_metric(ctx, "spc.capability", exc)
        return
    diags = []
    if res.get("success") and res.get("cpk") is not None and not res["capable"]:
        diags.append(Diagnostic(code="SPC_LOW_CPK", severity="warning", message=f"Cpk {res['cpk']:.2f} below {res['min_cpk_warn']}"))
    response = _build_response(ctx, command="spc.capability", state="ok" if res["success"] else "error", data=res, diagnostics=diags)

    def _text() -> None:
        if not res["success"]:
            console.print(f"[red]{res.get('error')}[/red]")
            return
        if res.get("cpk") is None:
            console.print(f"[yellow]{metric}: not enough data[/yellow]")
            return
        console.print(f"\n[bold cyan]{metric} capability[/bold cyan] (n={res['n']}, mean {res['mean']:.4g}, LSL {res['lsl']}, USL {res['usl']})")
        console.print(f"  • Cp {res['cp']}  Cpk {res['cpk']:.2f}  Pp {res['pp']}  Ppk {res['ppk']:.2f}")
        badge = "[green]capable[/green]" if res["capable"] else f"[yellow]below {res['min_cpk_warn']}[/yellow]"
        console.print(f"  • {badge}")

    _emit_response(ctx, response, text_renderer=_text)
