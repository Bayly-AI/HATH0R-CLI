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


@pr.command("check")
@click.option("--head", default=None, help="Head branch (defaults to the current branch).")
@click.option("--base", default="development", show_default=True, help="Base branch the PR targets.")
@click.pass_context
def pr_check(ctx: click.Context, head: str | None, base: str) -> None:
    """Check a head → base PR against the promotion path (same rules as CI)."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    bot = GitWorkflowBot()
    res = bot.check_path(head or bot.current_branch(), base)
    response = _build_response(ctx, command="pr.check", state="ok" if res["allowed"] else "error", data=res)

    def _text() -> None:
        mark, color = ("✓", "green") if res["allowed"] else ("✗", "red")
        click.echo(click.style(f"{mark} {res['head']} → {res['base']}: {res['reason']}", fg=color))
        if res["allowed"]:
            click.echo(f"  class={res['classification']} merge={res['merge_strategy']} human_gate={res['human_gate']}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res["allowed"]:
        ctx.exit(1)


@pr.command("create")
@click.option("--title", default=None, help="PR title (defaults from branch name).")
@click.option("--body", default=None, help="PR body (defaults to issue link + Version Impact).")
@click.option("--base", default="development", show_default=True, help="Base branch.")
@click.option(
    "--semver",
    type=click.Choice(["patch", "minor", "major"]),
    default="patch",
    show_default=True,
    help="Version Impact declared in the PR body (CR-SEMVER-BUMP-001).",
)
@click.option("--draft", is_flag=True, default=False, help="Open as draft.")
@click.option("--repo", default=None, help="GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Validate and show the plan without pushing.")
@click.pass_context
def pr_create(
    ctx: click.Context,
    title: str | None,
    body: str | None,
    base: str,
    semver: str,
    draft: bool,
    repo: str | None,
    dry_run: bool,
) -> None:
    """Push the current work branch and open its PR into development."""
    from hath0r_cli.bots import PRBot
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    head = GitWorkflowBot().current_branch()
    path = GitWorkflowBot().check_path(head, base)
    if not path["allowed"]:
        res = {"success": False, "branch": head, "base": base, "path": path, "error": path["reason"]}
        if head in ("development", "testing", "staging", "master") or head.startswith("release/"):
            res["hint"] = "Use `hath0r promote to <stage>` for promotion PRs."
    else:
        issue = path.get("issue_number")
        default_body = (f"Closes #{issue}\n\n" if issue else "") + f"Version Impact: {semver}\n"
        res = PRBot().create_pr(
            title=title, body=body or default_body, base=base, head=head, repo=repo, draft=draft, semver=semver, dry_run=dry_run
        )
        res["path"] = path
    response = _build_response(ctx, command="pr.create", state="ok" if res.get("success") else "error", data=res, dry_run=dry_run)

    def _text() -> None:
        if res.get("success"):
            click.echo(click.style(f"✓ {res.get('url') or res.get('action')}", fg="green"))
        else:
            click.echo(click.style(f"✗ {res.get('error') or res.get('output')}", fg="red"))
            if res.get("hint"):
                click.echo(f"  {res['hint']}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@pr.command("status")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="GitHub repository (owner/repo).")
@click.pass_context
def pr_status(ctx: click.Context, pr_number: int, repo: str | None) -> None:
    """Show CI check rollup for a PR (failing / pending / total)."""
    from hath0r_cli.bots import PRBot

    res = PRBot().monitor_checks(pr_number, repo=repo)
    if "error" in res:
        state = "error"
    else:
        state = "ok" if res.get("healthy") and not res.get("pending_checks") else "degraded"
    response = _build_response(ctx, command="pr.status", state=state, data=res)

    def _text() -> None:
        if "error" in res:
            click.echo(click.style(f"✗ PR #{pr_number}: {res['error']}", fg="red"))
            return
        click.echo(f"PR #{pr_number} [{res.get('state')}] checks: {res.get('total_checks')}")
        for name in res.get("failing_checks", []):
            click.echo(click.style(f"  ✗ {name}", fg="red"))
        for name in res.get("pending_checks", []):
            click.echo(click.style(f"  … {name}", fg="yellow"))
        if res.get("healthy"):
            click.echo(click.style("  ✓ no failing checks", fg="green"))

    _emit_response(ctx, response, text_renderer=_text)
    if state == "error":
        ctx.exit(1)


@pr.command("merge")
@click.argument("pr_number", type=int)
@click.option("--human-approved", is_flag=True, default=False, help="Confirm human review for staging/master PRs.")
@click.option("--repo", default=None, help="GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Show the merge command without running it.")
@click.pass_context
def pr_merge(ctx: click.Context, pr_number: int, human_approved: bool, repo: str | None, dry_run: bool) -> None:
    """Merge a PR with the policy strategy: squash into development, merge-commit for promotions."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    res = GitWorkflowBot().merge(pr_number, human_approved=human_approved, repo=repo, dry_run=dry_run)
    response = _build_response(ctx, command="pr.merge", state="ok" if res.get("success") else "error", data=res, dry_run=dry_run)

    def _text() -> None:
        if res.get("success"):
            click.echo(click.style(f"✓ PR #{pr_number} {res.get('head')} → {res.get('base')} ({res.get('strategy')})", fg="green"))
            if res.get("action"):
                click.echo(f"  {res['action']}")
        else:
            click.echo(click.style(f"✗ {res.get('error')}", fg="red"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


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
