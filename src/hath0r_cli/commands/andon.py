"""Andon stop-the-line commands (WS6, #588, #589): ``hath0r andon``."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.commands._qa_common import fail
from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.envelope import Diagnostic


def _bot():
    from hath0r_cli.bots.andon_bot import AndonBot

    return AndonBot(cwd=Path.cwd())


@click.group("andon")
def andon_cmd() -> None:
    """Stop-the-line signals: see, acknowledge and clear Andon events."""


@andon_cmd.command("status")
@click.pass_context
def andon_status(ctx: click.Context) -> None:
    """Show active Andon stops and warnings and check the event ledger."""
    res = _bot().status()
    diags = [Diagnostic(code="ANDON_STOP", severity="error", message=f"{e['event_id']}: {e['reason']}") for e in res["active"] if e["severity"] == "stop"]
    if not res["ledger_valid"]:
        diags.append(Diagnostic(code="ANDON_LEDGER_TAMPERED", severity="error", message="Andon ledger hash chain is broken"))
    response = _build_response(ctx, command="andon.status", state="stopped" if res["stopped"] else "ok", data=res, diagnostics=diags)

    def _text() -> None:
        badge = "[bold red]LINE STOPPED[/bold red]" if res["stopped"] else "[bold green]running[/bold green]"
        console.print(f"\n[bold cyan]Andon[/bold cyan]: {badge} · {res['active_stops']} stop(s), {res['active_warnings']} warning(s)")
        for e in res["active"]:
            colour = "red" if e["severity"] == "stop" else "yellow"
            console.print(f"  [{colour}]{e['severity']:<4}[/{colour}] {e['event_id']} [{e['state']}] {e['source']}: {e['reason']}")
        if not res["ledger_valid"]:
            console.print("  [red]✗ ledger hash chain is broken[/red]")

    _emit_response(ctx, response, text_renderer=_text)
    if res["stopped"]:
        ctx.exit(1)


@andon_cmd.command("raise")
@click.option("--source", default="operator", show_default=True)
@click.option("--severity", type=click.Choice(["stop", "warn"]), default="stop", show_default=True)
@click.option("--reason", required=True)
@click.pass_context
def andon_raise(ctx: click.Context, source: str, severity: str, reason: str) -> None:
    """Pull the cord by hand."""
    res = _bot().raise_event(source=source, severity=severity, reason=reason)
    response = _build_response(ctx, command="andon.raise", state="ok", data=res)
    _emit_response(ctx, response, text_renderer=lambda: console.print(f"[red]Andon {severity}[/red] {res['event_id']}: {reason}"))


def _transition(ctx: click.Context, command: str, method: str, event_id: str, by: str, note: str) -> None:
    try:
        res = getattr(_bot(), method)(event_id, by=by, note=note)
    except ValueError as exc:
        fail(ctx, command, "ANDON_INVALID_TRANSITION", exc)
        return
    response = _build_response(ctx, command=command, state="ok", data=res)
    _emit_response(ctx, response, text_renderer=lambda: console.print(f"[green]✓[/green] {method} {event_id}"))


@andon_cmd.command("ack")
@click.argument("event_id")
@click.option("--by", default="operator", show_default=True)
@click.option("--note", default="")
@click.pass_context
def andon_ack(ctx: click.Context, event_id: str, by: str, note: str) -> None:
    """Acknowledge an event (required before a stop can be cleared)."""
    _transition(ctx, "andon.ack", "ack", event_id, by, note)


@andon_cmd.command("clear")
@click.argument("event_id")
@click.option("--by", default="operator", show_default=True)
@click.option("--note", default="", help="What fixed the cause.")
@click.pass_context
def andon_clear(ctx: click.Context, event_id: str, by: str, note: str) -> None:
    """Clear an acknowledged event so work can resume."""
    _transition(ctx, "andon.clear", "clear", event_id, by, note)


@andon_cmd.command("verify")
@click.pass_context
def andon_verify(ctx: click.Context) -> None:
    """Verify the Andon ledger hash chain."""
    res = _bot().verify()
    response = _build_response(ctx, command="andon.verify", state="ok" if res["valid"] else "failed", data=res)
    _emit_response(ctx, response, text_renderer=lambda: console.print(("[green]✓ ledger valid[/green]" if res["valid"] else f"[red]✗ tampered records {res['tampered_records']}[/red]") + f" ({res['records_checked']} records)"))
    if not res["valid"]:
        ctx.exit(1)
