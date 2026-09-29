"""Branch command for HATH0R CLI."""

from __future__ import annotations

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def branch() -> None:
    """Branch Bot: create, validate, and manage git branches."""


@branch.command("validate")
@click.argument("name")
@click.pass_context
def branch_validate(ctx: click.Context, name: str) -> None:
    """Validate branch name against governance taxonomy."""
    from hath0r_cli.bots import BranchBot

    bot = BranchBot()
    res = bot.validate_name(name)
    state = "ok" if res.get("valid") else "degraded"
    response = _build_response(ctx, command="branch.validate", state=state, data=res)

    def _text() -> None:
        color = "green" if res.get("valid") else "red"
        click.echo(click.style(res.get("message", ""), fg=color))

    _emit_response(ctx, response, text_renderer=_text)
