"""Pr command for HATH0R CLI."""

from __future__ import annotations

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def pr() -> None:
    """PR Bot: inspect, process Dependabot, and manage pull requests."""


@pr.command("dependabot")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--auto-merge/--no-auto-merge", default=True, help="Enable auto-merge if checks pass.")
@click.pass_context
def pr_dependabot(ctx: click.Context, pr_number: int, repo: str | None, auto_merge: bool) -> None:
    """Triage and automatically process Dependabot PRs."""
    from hath0r_cli.bots import PRBot

    bot = PRBot()
    res = bot.process_dependabot(pr_number, repo=repo, auto_merge=auto_merge)
    state = "ok" if res.get("status") == "processed" else "degraded"
    response = _build_response(ctx, command="pr.dependabot", state=state, data=res)

    def _text() -> None:
        click.echo(f"PR #{pr_number} Dependabot triage: {res.get('action') or res.get('status')}")

    _emit_response(ctx, response, text_renderer=_text)



