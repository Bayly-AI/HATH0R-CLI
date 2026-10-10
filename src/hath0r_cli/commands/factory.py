"""Factory command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _cli_repo_root,
    _discover_group_root,
    _emit_response,
    console,
)
from hath0r_cli.envelope import Diagnostic


@click.group()
def factory() -> None:
    """Manage and execute Hath0r automation factories."""


@factory.command("list")
@click.pass_context
def factory_list(ctx: click.Context) -> None:
    """List available automation factories."""

    import yaml

    cli_repo_root = _cli_repo_root()
    group_root = Path.cwd() if (Path.cwd() / "cfg/factories").is_dir() else (_discover_group_root() or cli_repo_root)
    factories_dir = group_root / "cfg" / "factories"
    if not factories_dir.is_dir():
        factories_dir = cli_repo_root / "cfg" / "factories"

    items = []
    if factories_dir.is_dir():
        for f in factories_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "factory_id" in data:
                    items.append(
                        {
                            "id": data.get("factory_id"),
                            "name": data.get("name"),
                            "version": data.get("version"),
                            "description": data.get("description", "").strip(),
                            "bots_count": len(data.get("bots", [])),
                            "workflows_count": len(data.get("workflows", [])),
                            "file": str(f),
                        }
                    )
            except Exception:
                pass

    response = _build_response(ctx, command="factory.list", state="ok", data={"factories": items})

    def _text() -> None:
        if not items:
            click.echo("No factories found.")
            return
        table = Table(title="Hath0r Automation Factories")
        table.add_column("Factory ID", style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Version", style="magenta")
        table.add_column("Bots", style="yellow")
        table.add_column("Workflows", style="blue")
        for it in items:
            table.add_row(it["id"], it["name"], str(it["version"]), str(it["bots_count"]), str(it["workflows_count"]))
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@factory.command("info")
@click.argument("factory_id")
@click.pass_context
def factory_info(ctx: click.Context, factory_id: str) -> None:
    """Show detailed metadata and available workflows for a specific factory."""

    import yaml

    cli_repo_root = _cli_repo_root()
    group_root = Path.cwd() if (Path.cwd() / "cfg/factories").is_dir() else (_discover_group_root() or cli_repo_root)
    factories_dir = group_root / "cfg" / "factories"
    if not factories_dir.is_dir():
        factories_dir = cli_repo_root / "cfg" / "factories"

    factory_file = None
    for f in factories_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("factory_id") == factory_id:
                factory_file = f
                break
        except Exception:
            pass

    if not factory_file:
        response = _build_response(
            ctx,
            command="factory.info",
            state="error",
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FACTORY_NOT_FOUND",
                    message=f"Factory '{factory_id}' not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_data = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    response = _build_response(ctx, command="factory.info", state="ok", data=factory_data)

    def _text() -> None:
        console.print(f"[bold cyan]Factory:[/bold cyan] {factory_data.get('name')} ([dim]{factory_id}[/dim])")
        console.print(f"[bold]Version:[/bold] {factory_data.get('version')}")
        if factory_data.get("description"):
            console.print(f"[bold]Description:[/bold] {factory_data.get('description').strip()}")

        console.print("\n[bold yellow]Participating Bots:[/bold yellow]")
        for b in factory_data.get("bots", []):
            caps = ", ".join(b.get("capabilities", []))
            console.print(f"  • [cyan]{b.get('id')}[/cyan] ({b.get('name')}): {caps}")

        console.print("\n[bold green]Declared Workflows:[/bold green]")
        for wf in factory_data.get("workflows", []):
            sched = f" [dim](cron: {wf.get('schedule')})[/dim]" if wf.get("schedule") else ""
            console.print(f"  • [bold]{wf.get('id')}[/bold]: {wf.get('name')}{sched}")
            for st in wf.get("steps", []):
                console.print(f"      - {st.get('bot')} → {st.get('action')}")

    _emit_response(ctx, response, text_renderer=_text)


@factory.command("validate")
@click.argument("factory_id", required=False, default=None)
@click.pass_context
def factory_validate(ctx: click.Context, factory_id: str | None) -> None:
    """Validate factory configurations against schema contracts and bot integrity."""
    from hath0r_cli.factory_validation import validate_all_factories, validate_factory_file

    group_root = Path.cwd() if (Path.cwd() / "cfg/factories").is_dir() else _discover_group_root()
    all_results = validate_all_factories(group_root)

    if factory_id:
        selected = [r for r in all_results if r.factory_id == factory_id]
        if not selected:
            # Check if factory_id is a file path
            candidate_path = Path(factory_id)
            if candidate_path.is_file():
                selected = [validate_factory_file(candidate_path)]
            else:
                response = _build_response(
                    ctx,
                    command="factory.validate",
                    state="error",
                    diagnostics=[
                        Diagnostic(
                            severity="error",
                            code="FACTORY_NOT_FOUND",
                            message=f"Factory '{factory_id}' not found.",
                        )
                    ],
                )
                _emit_response(ctx, response)
                ctx.exit(1)
        results = selected
    else:
        results = all_results

    all_valid = all(r.valid for r in results)
    state = "ok" if all_valid else "error"

    data = {
        "factories": [r.to_dict() for r in results],
        "total": len(results),
        "valid_count": sum(1 for r in results if r.valid),
        "invalid_count": sum(1 for r in results if not r.valid),
    }

    diagnostics: list[Diagnostic] = []
    for r in results:
        for err in r.errors:
            diagnostics.append(
                Diagnostic(
                    code="FACTORY_VALIDATION_ERROR",
                    message=f"[{r.factory_id}] {err}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "factory.validate"},
                    details={"factory_id": r.factory_id, "file": str(r.file_path)},
                )
            )
        for warn in r.warnings:
            diagnostics.append(
                Diagnostic(
                    code="FACTORY_VALIDATION_WARNING",
                    message=f"[{r.factory_id}] {warn}",
                    severity="warning",
                    provenance={"component": "hath0r-cli", "operation": "factory.validate"},
                    details={"factory_id": r.factory_id, "file": str(r.file_path)},
                )
            )

    response = _build_response(ctx, command="factory.validate", state=state, data=data, diagnostics=diagnostics)

    def _text() -> None:
        table = Table(title="Factory Specification Validation")
        table.add_column("Factory ID", style="bold cyan")
        table.add_column("Status")
        table.add_column("Bots", justify="right")
        table.add_column("Workflows", justify="right")
        table.add_column("Issues / Path")

        for r in results:
            status = "[green]VALID[/green]" if r.valid else "[red]INVALID[/red]"
            issues = []
            if r.errors:
                issues.append(f"[red]{len(r.errors)} error(s)[/red]")
            if r.warnings:
                issues.append(f"[yellow]{len(r.warnings)} warning(s)[/yellow]")
            issue_str = ", ".join(issues) if issues else "[dim]OK[/dim]"

            table.add_row(
                r.factory_id,
                status,
                str(r.bots_count),
                str(r.workflows_count),
                issue_str,
            )
        console.print(table)

        for r in results:
            if not r.valid:
                console.print(f"[bold red]Errors for {r.factory_id} ({r.file_path.name}):[/bold red]")
                for err in r.errors:
                    console.print(f"  [red]✗[/red] {err}")
            if r.warnings:
                console.print(f"[bold yellow]Warnings for {r.factory_id}:[/bold yellow]")
                for warn in r.warnings:
                    console.print(f"  [yellow]![/yellow] {warn}")

        if all_valid:
            console.print(f"[green]All {len(results)} factory specification(s) validated successfully.[/green]")
        else:
            console.print(
                f"[red]{data['invalid_count']} of {data['total']} factory specification(s) failed validation.[/red]"
            )

    _emit_response(ctx, response, text_renderer=_text)
    if not all_valid:
        ctx.exit(1)


@factory.command("run")
@click.argument("factory_id")
@click.option("--workflow", "-w", "workflow_id", default=None, help="Target specific workflow ID within the factory.")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without modifying git or GitHub.")
@click.pass_context
def factory_run(ctx: click.Context, factory_id: str, workflow_id: str | None, repo: str | None, dry_run: bool) -> None:
    """Execute workflows defined in a factory."""
    import uuid

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    cli_repo_root = _cli_repo_root()
    group_root = Path.cwd() if (Path.cwd() / "cfg/factories").is_dir() else (_discover_group_root() or cli_repo_root)
    factories_dir = group_root / "cfg" / "factories"
    if not factories_dir.is_dir():
        factories_dir = cli_repo_root / "cfg" / "factories"

    factory_file = None
    for f in factories_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("factory_id") == factory_id:
                factory_file = f
                break
        except Exception:
            pass

    if not factory_file:
        response = _build_response(
            ctx,
            command="factory.run",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(severity="error", code="FACTORY_NOT_FOUND", message=f"Factory '{factory_id}' not found.")
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_def = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    workflows = factory_def.get("workflows", [])

    if workflow_id:
        target_wfs = [w for w in workflows if w.get("id") == workflow_id]
        if not target_wfs:
            available = ", ".join(w.get("id", "") for w in workflows if w.get("id"))
            response = _build_response(
                ctx,
                command="factory.run",
                state="error",
                dry_run=dry_run,
                diagnostics=[
                    Diagnostic(
                        severity="error",
                        code="WORKFLOW_NOT_FOUND",
                        message=(
                            f"Workflow '{workflow_id}' not found in factory '{factory_id}'. "
                            f"Available workflows: {available or 'none'}"
                        ),
                        details={"factory_id": factory_id, "workflow": workflow_id},
                    )
                ],
            )
            _emit_response(ctx, response)
            ctx.exit(1)
        workflows = target_wfs

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    registry = BotRegistry(cwd=group_root)

    wf_results = []
    diagnostics = []

    for wf in workflows:
        wf_res = execute_workflow(wf, registry, repo=repo, dry_run=dry_run, run_id=run_id)
        wf_results.append(wf_res.to_dict())
        for st in wf_res.steps:
            if not st.success:
                diagnostics.append(
                    Diagnostic(
                        code="STEP_EXECUTION_FAILED",
                        message=f"[{wf_res.workflow_id}::{st.bot_id}] {st.error or 'Step execution failed'}",
                        severity="error",
                        provenance={"component": "hath0r-cli", "operation": "factory.run"},
                        details={
                            "factory_id": factory_id,
                            "workflow": wf_res.workflow_id,
                            "bot": st.bot_id,
                            "policy": st.policy,
                            "aborted": st.aborted,
                        },
                    )
                )

    all_success = len(diagnostics) == 0
    state = "ok" if all_success else "error"

    # Spool execution telemetry event (never blocks or errors CLI)
    spool_telemetry_event(
        event_type="factory.execution",
        payload={
            "run_id": run_id,
            "factory_id": factory_id,
            "state": state,
            "dry_run": dry_run,
            "workflows": wf_results,
        },
        base_dir=group_root,
    )

    response = _build_response(
        ctx,
        command="factory.run",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "factory_id": factory_id,
            "dry_run": dry_run,
            "workflows": wf_results,
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix}Executed factory '{factory_id}':")
        for w in wf_results:
            status_icon = "✓" if w["success"] else "✗"
            click.echo(f"  {status_icon} Workflow [{w['id']}]: {w['name']}")
            for st in w["steps"]:
                st_icon = "✓" if st["success"] else "✗"
                detail = st.get("data") or st.get("error")
                click.echo(f"    {st_icon} Bot [{st['bot']}] Action [{st['action']}]: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@factory.command("create")
@click.argument("factory_id")
@click.option("--name", default=None, help="Human-readable factory name.")
@click.option("--description", default="", help="Factory description.")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing factory file.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without writing.")
@click.pass_context
def factory_create(
    ctx: click.Context,
    factory_id: str,
    name: str | None,
    description: str,
    force: bool,
    dry_run: bool,
) -> None:
    """Create a new factory YAML under cfg/factories (Factory Manager bot)."""
    from hath0r_cli.factory_manager import FactoryManagerBot

    bot = FactoryManagerBot(cwd=Path.cwd(), group_root=_discover_group_root())
    res = bot.create(factory_id, name=name, description=description, force=force, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="factory.create", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(f"Created factory '{factory_id}' → {res.get('path')}")
        else:
            click.echo(f"Failed: {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@factory.command("update")
@click.argument("factory_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--version", default=None)
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def factory_update(
    ctx: click.Context,
    factory_id: str,
    name: str | None,
    description: str | None,
    version: str | None,
    dry_run: bool,
) -> None:
    """Update factory metadata (name/description/version)."""
    from hath0r_cli.factory_manager import FactoryManagerBot

    bot = FactoryManagerBot(cwd=Path.cwd(), group_root=_discover_group_root())
    res = bot.update(factory_id, name=name, description=description, version=version, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="factory.update", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("path") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@factory.command("delete")
@click.argument("factory_id")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def factory_delete(ctx: click.Context, factory_id: str, dry_run: bool) -> None:
    """Delete a factory YAML manifest."""
    from hath0r_cli.factory_manager import FactoryManagerBot

    bot = FactoryManagerBot(cwd=Path.cwd(), group_root=_discover_group_root())
    res = bot.delete(factory_id, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="factory.delete", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or (f"Deleted {res.get('path')}" if res.get("success") else res.get("error")))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@factory.group("schedule")
def factory_schedule() -> None:
    """Manage and synchronize automation factory schedules."""


@factory_schedule.command("list")
@click.pass_context
def factory_schedule_list(ctx: click.Context) -> None:
    """List all declared cron schedules across automation factories."""
    from hath0r_cli.scheduler import discover_scheduled_workflows

    group_root = _discover_group_root()
    scheduled = discover_scheduled_workflows(group_root=group_root)

    items = [s.to_dict() for s in scheduled]
    response = _build_response(ctx, command="factory.schedule.list", state="ok", data={"schedules": items})

    def _text() -> None:
        if not items:
            console.print("[dim]No factory workflows with declared cron schedules found.[/dim]")
            return
        table = Table(title="Factory Automation Schedules")
        table.add_column("Factory ID", style="cyan")
        table.add_column("Workflow", style="bold green")
        table.add_column("Cron Expression", style="yellow")
        table.add_column("Next Estimated Run (UTC)", style="magenta")
        for s in items:
            table.add_row(
                s["factory_id"],
                f"{s['workflow_id']} ({s['workflow_name']})",
                s["schedule"],
                s.get("next_run") or "N/A",
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@factory_schedule.command("sync")
@click.option("--target-dir", default=None, help="Target repository root where .github/workflows/ lives.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate sync without creating or modifying files.")
@click.pass_context
def factory_schedule_sync(ctx: click.Context, target_dir: str | None, dry_run: bool) -> None:
    """Synchronize factory cron schedules into GitHub Actions workflows."""
    from pathlib import Path

    from hath0r_cli.scheduler import sync_factory_schedules_to_github

    cli_repo_root = _cli_repo_root()
    group_root = _discover_group_root() or cli_repo_root
    dest_dir = Path(target_dir).resolve() if target_dir else group_root

    sync_results = sync_factory_schedules_to_github(dest_dir, group_root=group_root, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="factory.schedule.sync",
        state="ok",
        dry_run=dry_run,
        data={
            "target_dir": str(dest_dir),
            "dry_run": dry_run,
            "synced_count": len(sync_results),
            "workflows": sync_results,
        },
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        if not sync_results:
            console.print(f"{prefix}[dim]No scheduled factory workflows found to synchronize.[/dim]")
            return
        console.print(
            f"{prefix}[bold green]Synchronized {len(sync_results)} schedule(s) to GitHub Actions:[/bold green]"
        )
        for item in sync_results:
            console.print(f"  • {item['action']} [cyan]{item['filename']}[/cyan] ({item['schedule']})")

    _emit_response(ctx, response, text_renderer=_text)
