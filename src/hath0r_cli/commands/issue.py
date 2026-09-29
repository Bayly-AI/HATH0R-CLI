"""Issue command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def issue() -> None:
    """Issue Factory & Manager Bot: scan, validate, prioritize, and manage issues."""


@issue.command("list")
@click.option("--repo", default=None, help="Target specific repository (default: all BaylyAI repos)")
@click.option("--state", default="open", type=click.Choice(["open", "closed", "all"], case_sensitive=False))
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def issue_list(ctx: click.Context, repo: str | None, state: str, dry_run: bool) -> None:
    """List issues across BaylyAI repos with status validation and dependency priority structure."""
    from hath0r_cli.bots.issue_manager import IssueManagerBot

    bot = IssueManagerBot(cwd=Path.cwd())
    res = bot.list_issues(repo=repo, state=state, dry_run=dry_run)
    status_state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="issue.list", state=status_state, dry_run=dry_run, data=res)

    def _text() -> None:
        if dry_run:
            console.print(f"[yellow]{res.get('action')}[/yellow]")
            return
        total = res.get("total_issues", 0)
        valid = res.get("valid_issues", 0)
        repo_cnt = res.get("repo_count", 0)
        console.print(f"[bold cyan]BaylyAI Issue Factory[/bold cyan] ({repo_cnt} repos, {total} issues, {valid} valid)")
        console.print("-" * 75)
        for it in res.get("issues", []):
            rank = it.get("priority_rank")
            tier_label = it.get("priority_label", "P3")
            repo_name = it.get("repository", "")
            num = it.get("number")
            title = it.get("title", "")
            status = it.get("state", "OPEN")
            deps = it.get("depends_on", [])
            dep_str = f" [red](depends on #{','.join(map(str, deps))})[/red]" if deps else ""
            blocks = it.get("blocks", [])
            block_str = f" [green](blocks #{','.join(map(str, blocks))})[/green]" if blocks else ""
            val = it.get("validation", {})
            val_str = "" if val.get("is_valid") else f" [yellow]![/yellow] ({', '.join(val.get('findings', []))})"

            console.print(f"[{tier_label}] #{rank} {repo_name}#{num}: {title} [{status}]{dep_str}{block_str}{val_str}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@issue.command("create")
@click.option("--repo", required=True, help="Target repository (e.g. Bayly-AI/HATH0R-CLI)")
@click.option("--title", required=True, help="Issue title (minimum 10 characters)")
@click.option("--body", required=True, help="Detailed issue description (minimum 15 words)")
@click.option("--label", "-l", "labels", multiple=True, help="Issue labels")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def issue_create(ctx: click.Context, repo: str, title: str, body: str, labels: tuple[str, ...], dry_run: bool) -> None:
    """Create a new issue with enforced detailed description requirements."""
    from hath0r_cli.bots.issue_manager import IssueManagerBot

    bot = IssueManagerBot(cwd=Path.cwd())
    res = bot.create_issue(repo=repo, title=title, body=body, labels=list(labels) if labels else None, dry_run=dry_run)
    status_state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="issue.create", state=status_state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("success"):
            num = res.get("issue_number")
            repo_name = res.get("repo")
            console.print(f"[bold green]✓ Created issue #{num} on {repo_name}:[/bold green] {res.get('url')}")
        else:
            console.print(f"[bold red]✗ Failed to create issue:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


# ============================================================================
# Repository Hygiene & Organization Group (Issue #135)
# ============================================================================
