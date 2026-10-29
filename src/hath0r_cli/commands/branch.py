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


@branch.command("start")
@click.argument("work_type", type=click.Choice(["feature", "bugfix", "hotfix", "enhancement", "research", "fix", "chore"]))
@click.argument("issue_number", type=int)
@click.argument("slug")
@click.option("--base", default="development", show_default=True, help="Branch to cut from (origin/<base>).")
@click.option("--no-issue-check", is_flag=True, default=False, help="Skip verifying the GitHub issue is open.")
@click.option("--repo", default=None, help="GitHub repository (owner/repo) for the issue check.")
@click.option("--dry-run", is_flag=True, default=False, help="Show the plan without creating the branch.")
@click.pass_context
def branch_start(
    ctx: click.Context,
    work_type: str,
    issue_number: int,
    slug: str,
    base: str,
    no_issue_check: bool,
    repo: str | None,
    dry_run: bool,
) -> None:
    """Start issue-driven work: create <type>/<issue>-<slug> from origin/development."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    res = GitWorkflowBot().start_branch(
        work_type, issue_number, slug, base=base, verify_issue=not no_issue_check, repo=repo, dry_run=dry_run
    )
    response = _build_response(ctx, command="branch.start", state="ok" if res.get("success") else "error", data=res, dry_run=dry_run)

    def _text() -> None:
        if res.get("success"):
            verb = "Would create" if dry_run else "Created"
            click.echo(click.style(f"✓ {verb} {res.get('branch')} from {base}", fg="green"))
            click.echo("  Next: commit work, then `hath0r pr create` (targets development).")
        else:
            click.echo(click.style(f"✗ {res.get('error') or res.get('output')}", fg="red"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@branch.command("sync")
@click.option("--base", default="development", show_default=True, help="Branch to pull updates from.")
@click.option("--rebase", is_flag=True, default=False, help="Rebase instead of merge.")
@click.option("--dry-run", is_flag=True, default=False, help="Show the plan without changing the branch.")
@click.pass_context
def branch_sync(ctx: click.Context, base: str, rebase: bool, dry_run: bool) -> None:
    """Update the current work branch with origin/<base>; aborts cleanly on conflicts."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    res = GitWorkflowBot().sync_branch(base=base, rebase=rebase, dry_run=dry_run)
    response = _build_response(ctx, command="branch.sync", state="ok" if res.get("success") else "error", data=res, dry_run=dry_run)

    def _text() -> None:
        if res.get("success"):
            click.echo(click.style(f"✓ {res.get('branch')} synced with origin/{base} ({res['strategy']})", fg="green"))
            if res.get("action"):
                click.echo(f"  {res['action']}")
        else:
            click.echo(click.style(f"✗ {res.get('error')}", fg="red"))
            for path in res.get("conflicts", []):
                click.echo(f"  conflict: {path}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@branch.group("worktree")
def branch_worktree() -> None:
    """Manage isolated Git Worktree sandboxes for background agent concurrency."""
    pass


@branch_worktree.command("list")
@click.pass_context
def worktree_list(ctx: click.Context) -> None:
    """List all active Git worktrees."""
    from rich.table import Table

    from hath0r_cli.common import console
    from hath0r_cli.worktree_manager import WorktreeManager

    mgr = WorktreeManager()
    wts = mgr.list_worktrees()
    data = [w.to_dict() for w in wts]

    response = _build_response(
        ctx,
        command="branch.worktree.list",
        state="ok",
        data={"worktrees": data, "count": len(data)},
    )

    def _text() -> None:
        table = Table(title="Git Worktrees")
        table.add_column("Branch", style="cyan")
        table.add_column("Main", style="yellow")
        table.add_column("Head Commit", style="magenta")
        table.add_column("Path", style="white")

        for w in wts:
            table.add_row(
                w.branch,
                "✓ Primary" if w.is_main else "Sandbox",
                w.head_commit[:8] if w.head_commit else "-",
                w.path,
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@branch_worktree.command("create")
@click.option("--branch", "-b", required=True, help="Target git branch to checkout in the worktree.")
@click.option("--task-id", "-t", default=None, help="Identifier / slug for the worktree directory.")
@click.option("--new-branch", is_flag=True, default=False, help="Create a new branch if it does not exist.")
@click.pass_context
def worktree_create(ctx: click.Context, branch: str, task_id: str | None, new_branch: bool) -> None:
    """Create an isolated worktree for background agent execution."""
    from hath0r_cli.common import console
    from hath0r_cli.worktree_manager import WorktreeManager

    mgr = WorktreeManager()
    res = mgr.create_worktree(branch=branch, task_id=task_id, create_branch=new_branch)

    response = _build_response(
        ctx,
        command="branch.worktree.create",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Created Isolated Worktree:[/bold green] {res.get('path')}")
            console.print(f"  • Branch: [cyan]{res.get('branch')}[/cyan]")
            console.print(f"  • Task Slug: {res.get('task_id')}")
        else:
            console.print(f"[bold red]✗ Failed to create worktree:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@branch_worktree.command("remove")
@click.argument("target")
@click.option("--force", "-f", is_flag=True, default=False, help="Force remove even with untracked changes.")
@click.pass_context
def worktree_remove(ctx: click.Context, target: str, force: bool) -> None:
    """Remove an isolated worktree by path or task slug."""
    from hath0r_cli.common import console
    from hath0r_cli.worktree_manager import WorktreeManager

    mgr = WorktreeManager()
    res = mgr.remove_worktree(target=target, force=force)

    response = _build_response(
        ctx,
        command="branch.worktree.remove",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Removed Worktree:[/bold green] {res.get('path')}")
        else:
            console.print(f"[bold red]✗ Failed to remove worktree:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@branch_worktree.command("prune")
@click.pass_context
def worktree_prune(ctx: click.Context) -> None:
    """Prune stale administrative records for deleted worktrees."""
    from hath0r_cli.common import console
    from hath0r_cli.worktree_manager import WorktreeManager

    mgr = WorktreeManager()
    res = mgr.prune_worktrees()

    response = _build_response(
        ctx,
        command="branch.worktree.prune",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print("[bold green]✓ Pruned stale worktree records.[/bold green]")
        else:
            console.print(f"[bold red]✗ Failed to prune worktrees:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
