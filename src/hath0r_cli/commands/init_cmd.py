"""Init_cmd command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _cli_repo_root,
    _emit_response,
    console,
)


@click.command("init")
@click.option("--name", "product_name", default=None, help="Product or microservice name.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview onboarding changes without writing to disk.")
@click.option(
    "--rollback", is_flag=True, default=False, help="Roll back repository state from pre-init backup snapshot."
)
@click.option(
    "--sync-ci", is_flag=True, default=False, help="Provision or synchronize canonical CI promotion workflows."
)
@click.option(
    "--yes", "-y", "non_interactive", is_flag=True, default=False, help="Accept all defaults non-interactively."
)
@click.pass_context
def init_cmd(
    ctx: click.Context,
    product_name: str | None,
    dry_run: bool,
    rollback: bool,
    sync_ci: bool,
    non_interactive: bool,
) -> None:
    """Initialize and align any repository with the HATHOR agentic framework."""
    from hath0r_cli.bots.onboarding import RepoLayoutBot
    from hath0r_cli.factory_manager import FactoryManagerBot
    from hath0r_cli.step_runner import BotRegistry, execute_workflow

    cwd = Path.cwd()
    target_name = product_name or cwd.name

    if sync_ci and not rollback:
        layout_bot = RepoLayoutBot(cwd=cwd)
        # Snapshot state before syncing CI
        layout_bot.backup_state(dry_run=dry_run)
        ci_res = layout_bot.sync_ci_workflows(dry_run=dry_run)
        state = "ok" if ci_res.get("success") else "error"
        response = _build_response(
            ctx,
            command="init",
            state=state,
            data={
                "product_name": target_name,
                "dry_run": dry_run,
                "sync_ci": True,
                "ci_sync": ci_res,
            },
            dry_run=dry_run,
        )

        def _text_ci() -> None:
            if ci_res.get("success"):
                console.print(f"[bold green]✓ Synchronized {ci_res.get('synced_count')} CI workflow(s).[/bold green]")
                for wf in ci_res.get("synced_workflows", []):
                    console.print(f"  • .github/workflows/{wf}")
            else:
                console.print(f"[bold red]✗ Failed to sync CI workflows:[/bold red] {ci_res.get('error')}")

        _emit_response(ctx, response, text_renderer=_text_ci)
        if not ci_res.get("success"):
            raise SystemExit(1)
        return

    mgr = FactoryManagerBot(cwd=cwd)
    factory_res = mgr.get_factory("repo-onboarding-factory")

    if factory_res is None or not factory_res.get("success") or not factory_res.get("factory"):
        # Fallback to local package factory definition if not in cwd
        pkg_factory_path = _cli_repo_root() / "cfg" / "factories" / "repo-onboarding-factory.yaml"
        if pkg_factory_path.exists():
            import yaml

            spec = yaml.safe_load(pkg_factory_path.read_text(encoding="utf-8"))
        else:
            response = _build_response(
                ctx, command="init", state="error", data={"error": "repo-onboarding-factory not found"}
            )
            _emit_response(ctx, response)
            raise SystemExit(1)
    else:
        spec = factory_res["factory"]

    wf_id = "repo-rollback" if rollback else "repo-onboard"
    workflow = next((w for w in spec.get("workflows", []) if w.get("id") == wf_id), None)
    if not workflow:
        response = _build_response(
            ctx, command="init", state="error", data={"error": f"Workflow '{wf_id}' missing in factory spec."}
        )
        _emit_response(ctx, response)
        raise SystemExit(1)

    registry = BotRegistry(cwd=cwd)
    exec_res = execute_workflow(workflow, registry, dry_run=dry_run)

    state = "ok" if exec_res.success else "error"
    response = _build_response(
        ctx,
        command="init",
        state=state,
        data={
            "product_name": target_name,
            "dry_run": dry_run,
            "rollback": rollback,
            "workflow": exec_res.to_dict(),
        },
        dry_run=dry_run,
    )

    def _text() -> None:
        if rollback:
            if exec_res.success:
                console.print("[bold green]✓ Successfully rolled back repository state from backup.[/bold green]")
            else:
                console.print("[bold red]✗ Failed to rollback repository state.[/bold red]")
            return

        mode_str = "[bold yellow][DRY-RUN][/bold yellow] " if dry_run else ""
        console.print(f"{mode_str}[bold cyan]HATH0R Universal Repository Onboarding & Alignment[/bold cyan]")
        console.print(f"Target Repository: [bold]{target_name}[/bold] ({cwd})\n")

        for s in exec_res.steps:
            mark = "[bold green]✓[/bold green]" if s.success else "[bold red]✗[/bold red]"
            msg = s.data.get("message") if isinstance(s.data, dict) else s.error or s.action
            console.print(f"  {mark} [{s.bot_id}] {s.action}: {msg}")

        if exec_res.success:
            console.print("\n[bold green]✓ Repository is 100% aligned with HATH0R Agentic Framework.[/bold green]")
            console.print("  • Tri-Graph Substrate: KnowledgeGraph, ContextGraph, MemoryGraph ready.")
            console.print("  • Governance: AGENTS.md, SemVer, and playbooks active.")
            console.print("  • Run [bold cyan]hath0r doctor[/bold cyan] to verify system health.")
        else:
            console.print("\n[bold red]✗ Initialization completed with errors.[/bold red]")

    _emit_response(ctx, response, text_renderer=_text)
    if not exec_res.success:
        raise SystemExit(1)
