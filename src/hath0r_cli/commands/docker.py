"""Docker command for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _cli_repo_root,
    _emit_response,
    console,
)
from hath0r_cli.envelope import Diagnostic


@click.group()
def docker() -> None:
    """Docker Bot & Factory: validate and execute container workflows, monitor and diagnose stacks."""


@docker.group("workflow")
def docker_workflow() -> None:
    """Manage and execute Hath0r Docker workflow documents."""


@docker_workflow.command("validate")
@click.argument("workflow_file")
@click.pass_context
def docker_workflow_validate(ctx: click.Context, workflow_file: str) -> None:
    """Validate a Docker workflow document JSON against schema contract."""

    from hath0r_cli.bots import DockerBot

    wf_path = Path(workflow_file).resolve()
    if not wf_path.is_file():
        response = _build_response(
            ctx,
            command="docker.workflow.validate",
            state="error",
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FILE_NOT_FOUND",
                    message=f"Workflow file '{workflow_file}' not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    try:
        wf_data = json.loads(wf_path.read_text(encoding="utf-8"))
    except Exception as exc:
        response = _build_response(
            ctx,
            command="docker.workflow.validate",
            state="error",
            diagnostics=[Diagnostic(severity="error", code="INVALID_JSON", message=f"Failed to parse JSON: {exc}")],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    bot = DockerBot()
    res = bot.validate_workflow(wf_data)

    state = "ok" if res.get("valid") else "error"
    diagnostics = [
        Diagnostic(severity="error", code="WORKFLOW_SCHEMA_ERROR", message=err) for err in res.get("errors", [])
    ]
    response = _build_response(
        ctx,
        command="docker.workflow.validate",
        state=state,
        data=res,
        diagnostics=diagnostics,
    )

    def _text() -> None:
        if res.get("valid"):
            console.print(f"[bold green]✓ Workflow '{res.get('workflow_id')}' is valid.[/bold green]")
        else:
            console.print(f"[bold red]✗ Workflow '{res.get('workflow_id')}' failed schema validation:[/bold red]")
            for err in res.get("errors", []):
                console.print(f"  [red]•[/red] {err}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("valid"):
        ctx.exit(1)


@docker_workflow.command("run")
@click.argument("workflow_file")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate workflow steps without modifying Docker state.")
@click.pass_context
def docker_workflow_run(ctx: click.Context, workflow_file: str, dry_run: bool) -> None:
    """Validate and execute a Docker workflow via Docker Factory."""
    import uuid

    from hath0r_cli.bots import DockerBot
    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    wf_path = Path(workflow_file).resolve()
    if not wf_path.is_file():
        response = _build_response(
            ctx,
            command="docker.workflow.run",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FILE_NOT_FOUND",
                    message=f"Workflow file '{workflow_file}' not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    try:
        wf_data = json.loads(wf_path.read_text(encoding="utf-8"))
    except Exception as exc:
        response = _build_response(
            ctx,
            command="docker.workflow.run",
            state="error",
            dry_run=dry_run,
            diagnostics=[Diagnostic(severity="error", code="INVALID_JSON", message=f"Failed to parse JSON: {exc}")],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    # 1. Validation phase
    bot = DockerBot()
    val_res = bot.validate_workflow(wf_data)
    if not val_res.get("valid"):
        response = _build_response(
            ctx,
            command="docker.workflow.run",
            state="error",
            dry_run=dry_run,
            data={"validation": val_res},
            diagnostics=[
                Diagnostic(severity="error", code="WORKFLOW_SCHEMA_ERROR", message=err)
                for err in val_res.get("errors", [])
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    # 2. Convert DockerWorkflow spec into executable factory workflow definition
    spec = wf_data.get("spec", {})
    metadata = wf_data.get("metadata", {})
    wf_id = metadata.get("id", "docker-workflow")
    factory_steps = []

    for step in spec.get("steps", []):
        op = step.get("op")
        params = dict(step.get("params") or {})
        # Map op to docker-bot action
        if op == "validate":
            action = "validate"
            params["workflow"] = wf_data
        elif op == "build":
            action = "build"
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
        elif op == "up":
            action = "up"
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
            params.setdefault("services", spec.get("services"))
        elif op == "healthcheck":
            action = "healthcheck"
            params.setdefault("container", spec.get("container", {}).get("name"))
        elif op == "diagnose":
            action = "diagnose"
            params.setdefault("container", spec.get("container", {}).get("name"))
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
        elif op == "down":
            action = "down"
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
        else:
            action = op

        factory_steps.append(
            {
                "bot": "docker-bot",
                "action": action,
                "args": params,
                "on_failure": step.get("on_failure", "abort"),
            }
        )

    factory_wf_def = {
        "id": wf_id,
        "name": metadata.get("name", wf_id),
        "steps": factory_steps,
    }

    cli_repo_root = _cli_repo_root()
    registry = BotRegistry(cwd=cli_repo_root)
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    exec_res = execute_workflow(factory_wf_def, registry, dry_run=dry_run, run_id=run_id)
    all_success = exec_res.success
    state = "ok" if all_success else "error"

    diagnostics = []
    for st in exec_res.steps:
        if not st.success:
            diagnostics.append(
                Diagnostic(
                    code="DOCKER_STEP_FAILED",
                    message=f"[{st.action}] {st.error or 'Operation failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "docker.workflow.run"},
                    details={"op": st.action, "policy": st.policy},
                )
            )

    spool_telemetry_event(
        event_type="docker.workflow.execution",
        payload={
            "run_id": run_id,
            "workflow_id": wf_id,
            "state": state,
            "dry_run": dry_run,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        base_dir=cli_repo_root,
    )

    response = _build_response(
        ctx,
        command="docker.workflow.run",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "workflow_id": wf_id,
            "dry_run": dry_run,
            "success": all_success,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        status_icon = "✓" if all_success else "✗"
        console.print(f"{prefix}{status_icon} Docker Workflow [{wf_id}]: {metadata.get('name')}")
        for st in exec_res.steps:
            st_icon = "✓" if st.success else "✗"
            detail = st.data or st.error
            console.print(f"    {st_icon} Step [{st.action}]: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@docker.command("diagnose")
@click.argument("container_name", required=False, default=None)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate diagnostic check.")
@click.pass_context
def docker_diagnose(ctx: click.Context, container_name: str | None, dry_run: bool) -> None:
    """Diagnose container health and configuration issues without printing secrets."""
    from hath0r_cli.bots import DockerBot

    bot = DockerBot()
    res = bot.diagnose(container_name=container_name, dry_run=dry_run)
    state = "ok" if res.get("healthy") else "degraded"
    response = _build_response(ctx, command="docker.diagnose", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("healthy"):
            console.print(f"[bold green]✓ Container '{container_name or 'all'}' is healthy.[/bold green]")
        else:
            console.print(f"[bold yellow]! Diagnostic findings for '{container_name}':[/bold yellow]")
            for f in res.get("findings", []):
                console.print(f"  [yellow]•[/yellow] {f}")
            if res.get("remediation"):
                console.print(f"\n[cyan]Remediation:[/cyan] {res['remediation']}")

    _emit_response(ctx, response, text_renderer=_text)


# ============================================================================
# Quality / preflight / deploy / release / docs bots (#66–#71)
# ============================================================================



