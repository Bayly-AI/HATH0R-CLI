"""Preflight command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def preflight() -> None:
    """Pre-PR thresholds bot — run before opening a pull request."""


@preflight.command("run")
@click.option("--skip-tests", is_flag=True, default=False, help="Only check branch + VERSION.")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def preflight_run(ctx: click.Context, skip_tests: bool, dry_run: bool) -> None:
    """Block PR open until branch taxonomy, VERSION, and local gates pass."""
    from hath0r_cli.bots.quality import PreflightBot

    bot = PreflightBot(cwd=Path.cwd())
    res = bot.run(skip_tests=skip_tests, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="preflight.run", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or "preflight complete")
        for c in res.get("checks", []):
            icon = "✓" if c.get("ok") else "✗"
            detail = c.get("error") or c.get("message") or c.get("version") or c.get("branch") or ""
            click.echo(f"  {icon} {c.get('check')}: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)



