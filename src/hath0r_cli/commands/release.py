"""Release command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def release() -> None:
    """Version + release notes + GitHub tag/release bot."""


@release.command("validate")
@click.pass_context
def release_validate(ctx: click.Context) -> None:
    """Validate VERSION SemVer and CHANGELOG alignment."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.validate()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.validate", state=state, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("notes")
@click.option("--version", default=None, help="Override VERSION file.")
@click.pass_context
def release_notes(ctx: click.Context, version: str | None) -> None:
    """Generate release notes from CHANGELOG section."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.generate_notes(version=version)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.notes", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(res.get("notes"))
        else:
            click.echo(res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("publish")
@click.option("--repo", default=None)
@click.option("--skip-github-release", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def release_publish(ctx: click.Context, repo: str | None, skip_github_release: bool, dry_run: bool) -> None:
    """Create annotated tag and optional GitHub Release."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.tag_and_release(repo=repo, dry_run=dry_run, skip_github_release=skip_github_release)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.publish", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("tag") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)



