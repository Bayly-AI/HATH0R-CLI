"""Deploy command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def deploy() -> None:
    """Pre/post-deploy test bot (counts toward coverage narrative)."""


@deploy.command("pre")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def deploy_pre(ctx: click.Context, dry_run: bool) -> None:
    """Run pre-deploy test suite from cfg/quality-gates.json."""
    from hath0r_cli.bots.quality import DeployTestBot

    bot = DeployTestBot(cwd=Path.cwd())
    res = bot.run_pre_deploy(dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="deploy.pre", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("action"))
        if res.get("total_passed") or res.get("total_failed") or res.get("total_errors"):
            click.echo(
                f"  Results: {res.get('total_passed', 0)} passed, "
                f"{res.get('total_failed', 0)} failed, "
                f"{res.get('total_errors', 0)} error(s)"
            )
        issues = res.get("issues", [])
        if issues:
            click.echo(f"  Detected {len(issues)} failure(s):")
            for iss in issues[:10]:
                click.echo(f"    ✗ {iss.get('test')}: {iss.get('detail')}")
            if len(issues) > 10:
                click.echo(f"    ... and {len(issues) - 10} more.")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@deploy.command("post")
@click.option("--base-url", default=None, help="Optional smoke URL when no cfg commands set.")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def deploy_post(ctx: click.Context, base_url: str | None, dry_run: bool) -> None:
    """Run post-deploy smoke checks."""
    from hath0r_cli.bots.quality import DeployTestBot

    bot = DeployTestBot(cwd=Path.cwd())
    res = bot.run_post_deploy(base_url=base_url, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="deploy.post", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("action") or "post-deploy complete")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)



