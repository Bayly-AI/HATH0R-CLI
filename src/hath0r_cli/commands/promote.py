"""Environment promotion command for HATH0R CLI (CR-BAI-001)."""

from __future__ import annotations

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def promote() -> None:
    """Environment promotion: development → testing → staging → master (production)."""


@promote.command("status")
@click.option("--no-fetch", is_flag=True, default=False, help="Use local remote-tracking refs without fetching.")
@click.pass_context
def promote_status(ctx: click.Context, no_fetch: bool) -> None:
    """Show commits pending per stage, drift, versions, release branches and open promotion PRs."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    res = GitWorkflowBot().status(fetch=not no_fetch)
    response = _build_response(ctx, command="promote.status", state="ok" if res.get("success") else "degraded", data=res)

    def _text() -> None:
        from rich.table import Table

        table = Table(title="Promotion Pipeline (CR-BAI-001)")
        table.add_column("Stage", style="cyan")
        table.add_column("Env", style="white")
        table.add_column("Pending", justify="right", style="yellow")
        table.add_column("Drift", justify="right", style="magenta")
        table.add_column("Version", style="green")
        table.add_column("Gate", style="red")
        table.add_column("Open PR", style="white")
        for s in res["stages"]:
            pr = s.get("open_pr")
            table.add_row(
                f"{s['from']} → {s['to']}",
                s["environment"],
                "?" if s["pending_commits"] is None else str(s["pending_commits"]),
                "?" if s["drift_commits"] is None else str(s["drift_commits"]),
                f"{s.get('source_version') or '?'} → {s.get('target_version') or '?'}",
                "human" if s["human_gate"] else "ci",
                f"#{pr['number']}" if pr else "-",
            )
        console.print(table)
        console.print(f"Current branch: [cyan]{res['current_branch'] or '(detached)'}[/cyan] ({res['current_branch_kind']})")
        if res["release_branches"]:
            console.print("Release branches: " + ", ".join(res["release_branches"]))
        if res.get("fetched") is False:
            console.print("[yellow]! fetch failed — counts reflect last known remote refs[/yellow]")

    _emit_response(ctx, response, text_renderer=_text)


@promote.command("release")
@click.argument("version")
@click.option("--base", default="development", show_default=True, help="Branch to cut the release from.")
@click.option("--dry-run", is_flag=True, default=False, help="Show the push without creating the branch.")
@click.pass_context
def promote_release(ctx: click.Context, version: str, base: str, dry_run: bool) -> None:
    """Cut release/<version> from origin/development and push it (checkout is untouched)."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    res = GitWorkflowBot().cut_release(version, base=base, dry_run=dry_run)
    state = "error" if not res.get("success") else ("degraded" if res.get("warning") else "ok")
    response = _build_response(ctx, command="promote.release", state=state, data=res, dry_run=dry_run)

    def _text() -> None:
        if res.get("success"):
            verb = "Would push" if dry_run else "Pushed"
            console.print(f"[green]✓ {verb} {res['branch']} from {base}[/green]")
            if res.get("warning"):
                console.print(f"[yellow]! {res['warning']}[/yellow]")
            console.print(f"  Next: [cyan]hath0r promote to testing --from {res['branch']}[/cyan]")
        else:
            console.print(f"[red]✗ {res.get('error')}[/red]")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@promote.command("to")
@click.argument("target", type=click.Choice(["testing", "staging", "master", "production"], case_sensitive=False))
@click.option("--from", "source", default=None, help="Source branch (default: previous stage, or release/x.y.z).")
@click.option("--draft", is_flag=True, default=False, help="Open the promotion PR as draft.")
@click.option("--gate", is_flag=True, default=False, help="Also dispatch the promotion-environment-gates workflow.")
@click.option("--repo", default=None, help="GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Show the PR plan without creating it.")
@click.pass_context
def promote_to(
    ctx: click.Context,
    target: str,
    source: str | None,
    draft: bool,
    gate: bool,
    repo: str | None,
    dry_run: bool,
) -> None:
    """Open (or reuse) the promotion PR into TARGET after validating the path and pending commits."""
    from hath0r_cli.bots.git_workflow_bot import GitWorkflowBot

    res = GitWorkflowBot().promote(target, source=source, draft=draft, trigger_gate=gate, repo=repo, dry_run=dry_run)
    response = _build_response(ctx, command="promote.to", state="ok" if res.get("success") else "error", data=res, dry_run=dry_run)

    def _text() -> None:
        if not res.get("success"):
            console.print(f"[red]✗ {res.get('error')}[/red]")
            return
        if res.get("noop"):
            console.print(f"[green]✓ {res['message']}[/green]")
            return
        head = f"{res['source']} → {res['target']} ({res['pending_commits']} commits, env {res['environment']})"
        if res.get("dry_run"):
            console.print(f"[cyan]Plan:[/cyan] {head}")
            for action in res.get("actions", []):
                console.print(f"  {action}")
        else:
            verb = "Reusing" if res.get("reused") else "Opened"
            console.print(f"[green]✓ {verb} PR #{res.get('pr_number')}[/green] {head}\n  {res.get('url')}")
            if res.get("gate"):
                console.print(f"  gate: {res['gate']}")
        if res.get("human_gate"):
            console.print("[yellow]  Human gate: review, then `hath0r pr merge <n> --human-approved`.[/yellow]")
        if res.get("drift_commits"):
            console.print(f"[yellow]  ! {res['target']} has {res['drift_commits']} commit(s) not in {res['source']} (back-merge drift).[/yellow]")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
