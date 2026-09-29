"""Docs command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def docs() -> None:
    """Documentation / wiki / knowledge-share bots."""


@docs.command("wiki")
@click.option("--repo", required=True, help="owner/repo with GitHub wiki enabled")
@click.option("--title", required=True, help="Wiki page title")
@click.option("--body", default=None, help="Markdown body (or stdin)")
@click.option("--pr", "pr_number", type=int, default=None)
@click.option("--force", is_flag=True, default=False, help="Ignore wiki.enabled=false")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def docs_wiki(
    ctx: click.Context,
    repo: str,
    title: str,
    body: str | None,
    pr_number: int | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Sync a PR page to the GitHub wiki when cfg enables it."""
    from hath0r_cli.bots import DocumentationBot

    content = body
    if content is None and not click.get_text_stream("stdin").isatty():
        content = click.get_text_stream("stdin").read()
    content = content or f"# {title}\n\n(empty body)\n"

    bot = DocumentationBot(cwd=Path.cwd())
    res = bot.sync_to_wiki(repo, title, content, pr_number=pr_number, dry_run=dry_run, force=force)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="docs.wiki", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("skipped"):
            click.echo(f"Skipped: {res.get('reason')}")
        else:
            click.echo(res.get("action") or res.get("status") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@docs.command("share")
@click.option("--summary", default=None, help="Knowledge summary text")
@click.option("--pr", "pr_number", type=int, default=None)
@click.option("--repo", default=None)
@click.option("--target-kb", default=None, help="Override local KB path")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def docs_share(
    ctx: click.Context,
    summary: str | None,
    pr_number: int | None,
    repo: str | None,
    target_kb: str | None,
    dry_run: bool,
) -> None:
    """Post-PR knowledge share → project MCP / group KB (idempotent by PR)."""
    from hath0r_cli.bots import DocumentationBot

    bot = DocumentationBot(cwd=Path.cwd())
    res = bot.share_knowledge(
        summary=summary or (f"Knowledge share for PR #{pr_number}" if pr_number else "Knowledge share"),
        pr_number=pr_number,
        repo=repo,
        target_kb=target_kb,
        dry_run=dry_run,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="docs.share", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("path") or res.get("reason") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)



