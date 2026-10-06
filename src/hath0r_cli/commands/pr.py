"""PR Bot: inspect, process Dependabot, and manage pull requests."""

from __future__ import annotations

import click
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
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


@pr.command("review")
@click.option("--antagonistic", is_flag=True, default=True, help="Execute Antagonistic adversarial code review and tech debt enforcement.")
@click.pass_context
def pr_review(ctx: click.Context, antagonistic: bool) -> None:
    """Execute automated PR diff review and tech debt extraction."""
    from hath0r_cli.bots.antagonistic_review import antagonistic_review_bot

    res = antagonistic_review_bot.review_diff()
    response = _build_response(
        ctx,
        command="pr.review",
        state="ok" if res.get("passed_gate") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("passed_gate"):
            console.print("\n[bold green]✓ Antagonistic PR Code Review PASSED[/bold green]")
        else:
            console.print("\n[bold red]✗ Antagonistic PR Code Review FAILED[/bold red]")
            for flaw in res.get("adversarial_flaws", []):
                console.print(f"  [red]• Flaw:[/red] {flaw['message']} (Line {flaw['line_number']})")

        if res.get("tech_debts_count", 0) > 0:
            console.print(f"\n[bold yellow]⚠️ Tech Debt Discovered (CR-CLI-TECH-DEBT-001): {res['tech_debts_count']} items[/bold yellow]")
            for issue in res.get("auto_created_issues", []):
                console.print(f"  • Issue Created: [cyan]{issue['title']}[/cyan]")

    _emit_response(ctx, response, text_renderer=_text)
