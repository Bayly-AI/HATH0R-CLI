"""Shared helpers for the industrial QA command groups (spc, andon, fmea, rca, dmaic, optimize)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import click

from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.envelope import Diagnostic


def fail(ctx: click.Context, command: str, code: str, exc: Exception, exit_code: int = 2) -> None:
    """Emit an error envelope with one diagnostic and exit (2 = invalid input)."""
    msg = str(exc)
    response = _build_response(
        ctx, command=command, state="error", data={"success": False, "error": msg},
        diagnostics=[Diagnostic(code=code, severity="error", message=msg)],
    )
    _emit_response(ctx, response, text_renderer=lambda: console.print(f"[red]✗ {msg}[/red]"))
    ctx.exit(exit_code)


def emit(
    ctx: click.Context,
    command: str,
    res: Dict[str, Any],
    text: Callable[[], None],
    *,
    state: Optional[str] = None,
    diagnostics: Optional[list] = None,
    exit_on_failure: bool = False,
) -> None:
    """Emit a result envelope; optionally exit 1 when ``res['success']`` is false."""
    ok = bool(res.get("success", True))
    response = _build_response(ctx, command=command, state=state or ("ok" if ok else "failed"), data=res, diagnostics=diagnostics or [])
    _emit_response(ctx, response, text_renderer=text)
    if exit_on_failure and not ok:
        ctx.exit(1)


def call(ctx: click.Context, command: str, code: str, fn: Callable[[], Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Run ``fn``; turn ValueError / FileNotFoundError / FileExistsError into an exit-2 envelope."""
    try:
        return fn()
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        fail(ctx, command, code, exc)
        return None


def show_rows(rows: Any, columns: Any, title: str = "") -> None:
    from rich.table import Table

    t = Table(title=title or None, show_header=True, header_style="bold")
    for c in columns:
        t.add_column(c)
    for r in rows:
        t.add_row(*[str(x) for x in r])
    console.print(t)


__all__ = ["fail", "emit", "call", "show_rows", "console", "Diagnostic"]
