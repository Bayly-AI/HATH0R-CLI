"""Quality command for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def quality() -> None:
    """PR Quality Gates bot — aggregate hard gates including SonarCloud."""


@quality.command("check")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="owner/repo")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def quality_check(ctx: click.Context, pr_number: int, repo: str | None, dry_run: bool) -> None:
    """Evaluate PR status checks against configured hard gates."""
    from hath0r_cli.bots.quality import QualityGateBot

    bot = QualityGateBot(cwd=Path.cwd())
    res = bot.check_pr(pr_number, repo=repo, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="quality.check", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or json.dumps(res, indent=2))
        if res.get("hard_failures"):
            click.echo(f"Hard failures: {', '.join(res['hard_failures'])}")
        if res.get("hard_missing"):
            click.echo(f"Missing gates: {', '.join(res['hard_missing'])}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
