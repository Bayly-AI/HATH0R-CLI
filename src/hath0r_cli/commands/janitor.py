"""Janitor command for HATH0R CLI."""

from __future__ import annotations

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def janitor() -> None:
    """Git Janitor Bot: audit and prune stale or merged branches."""


@janitor.command("scan")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.pass_context
def janitor_scan(ctx: click.Context, repo: str | None) -> None:
    """Scan for merged, closed, or stale branches."""
    from hath0r_cli.bots import GitJanitorBot

    bot = GitJanitorBot()
    res = bot.scan_stale_branches(repo=repo)
    response = _build_response(ctx, command="janitor.scan", state="ok", data=res)

    def _text() -> None:
        click.echo(
            f"Scanned {res.get('scanned_count', 0)} candidate branches. Found {res.get('stale_count', 0)} stale."
        )
        for b in res.get("stale_branches", []):
            click.echo(f"  - {b['branch']}: {b['reason']}")

    _emit_response(ctx, response, text_renderer=_text)


@janitor.command("prune")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate pruning without deleting branches.")
@click.pass_context
def janitor_prune(ctx: click.Context, repo: str | None, dry_run: bool) -> None:
    """Scan and prune all merged or closed branches."""
    from hath0r_cli.bots import GitJanitorBot

    bot = GitJanitorBot()
    scan = bot.scan_stale_branches(repo=repo)
    pruned = []
    for b in scan.get("stale_branches", []):
        res = bot.prune_branch(b["branch"], remote=True, dry_run=dry_run)
        pruned.append(
            {
                "branch": b["branch"],
                "success": res.get("success"),
                "action": res.get("action"),
            }
        )

    response = _build_response(
        ctx,
        command="janitor.prune",
        state="ok",
        dry_run=dry_run,
        data={
            "scanned": scan.get("scanned_count"),
            "dry_run": dry_run,
            "pruned": pruned,
        },
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix}Pruned {len(pruned)} stale branches.")
        for p in pruned:
            status = "✓" if p["success"] else "✗"
            act = f" ({p['action']})" if p.get("action") else ""
            click.echo(f"  {status} {p['branch']}{act}")

    _emit_response(ctx, response, text_renderer=_text)
