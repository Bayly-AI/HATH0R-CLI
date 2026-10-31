"""Workflow-First CLI command group (`hath0r workflow`) enforcing CR-FEATURE-WORKFLOW-STANDARD-001."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from hath0r_cli.bots.mcp_workflow_engine_bot import MCPWorkflowEngineBot
from hath0r_cli.common import _build_response, _emit_response, console


@click.group("workflow")
def workflow_cmd() -> None:
    """Workflow-First execution, Missing-Workflow Offer, and Level 1/2 AgentGraph workflow scaffolding."""


@workflow_cmd.command("list")
@click.pass_context
def workflow_list(ctx: click.Context) -> None:
    """List all declarative workflows registered across Level 1 (HATH0R-MCP) & Level 2 (HATH0R-CLI)."""
    bot = MCPWorkflowEngineBot(cwd=Path.cwd())
    res = bot.list_workflows()
    response = _build_response(ctx, command="workflow.list", state="ok", data=res)

    def _text() -> None:
        table = Table(title=f"Declarative Workflows ({res['count']} Registered)")
        table.add_column("Workflow ID", style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Owning Bot(s)", style="magenta")
        table.add_column("AgentGraph Level", style="yellow")
        table.add_column("File", style="blue")
        for wf in res.get("workflows", []):
            table.add_row(
                str(wf.get("workflow_id", "")),
                str(wf.get("name", "")),
                ", ".join(wf.get("owning_bots", [])),
                str(wf.get("agentgraph_level", "")),
                str(wf.get("file", "")),
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@workflow_cmd.command("match")
@click.option("--intent", "-i", required=True, help="Task intent or natural-language request.")
@click.option("--strict/--no-strict", default=True, help="Generate Missing-Workflow Offer when unmatched.")
@click.pass_context
def workflow_match(ctx: click.Context, intent: str, strict: bool) -> None:
    """Match a task intent to an existing workflow or generate a Missing-Workflow Offer."""
    bot = MCPWorkflowEngineBot(cwd=Path.cwd())
    res = bot.match_workflow(intent=intent, strict_offer=strict)
    response = _build_response(ctx, command="workflow.match", state="ok", data=res)

    def _text() -> None:
        if res.get("matched"):
            wf = res["workflow"]
            console.print(
                f"[bold green]✓ Matched Workflow:[/bold green] [cyan]{wf['workflow_id']}[/cyan] "
                f"(score={res['score']}, bots={wf['owning_bots']})"
            )
        else:
            offer = res.get("missing_workflow_offer") or {}
            console.print(f"[bold yellow]! Missing-Workflow Offer Triggered:[/bold yellow] {offer.get('message', '')}")
            console.print(f"  • Acceptance Test: [cyan]{offer.get('acceptance_test', '')}[/cyan]")
            console.print(f"  • Scaffold Command: [green]{offer.get('cli_scaffold_command', '')}[/green]")

    _emit_response(ctx, response, text_renderer=_text)


@workflow_cmd.command("offer")
@click.option("--intent", "-i", required=True, help="Original user request / task intent.")
@click.option("--bot", "owning_bots", multiple=True, help="Owning Bot ID(s) in BotRegistry.")
@click.option("--acceptance-test", default=None, help="Override acceptance test (defaults to original intent).")
@click.pass_context
def workflow_offer(
    ctx: click.Context,
    intent: str,
    owning_bots: tuple[str, ...],
    acceptance_test: str | None,
) -> None:
    """Generate a Missing-Workflow Offer using the original request as its acceptance test."""
    bot = MCPWorkflowEngineBot(cwd=Path.cwd())
    res = bot.offer_missing_workflow(
        intent=intent,
        owning_bots=list(owning_bots) if owning_bots else None,
        acceptance_test=acceptance_test,
    )
    response = _build_response(ctx, command="workflow.offer", state="ok", data=res)

    def _text() -> None:
        console.print(f"[bold cyan]Missing-Workflow Offer ({res['offer_id']}):[/bold cyan]")
        console.print(f"  • Proposed File: [green]{res['proposed_file']}[/green]")
        console.print(f"  • Owning Bot(s): [magenta]{', '.join(res['owning_bots'])}[/magenta]")
        console.print(f"  • Acceptance Test: [yellow]{res['acceptance_test']}[/yellow]")
        console.print(f"  • Scaffold: [cyan]{res['cli_scaffold_command']}[/cyan]")

    _emit_response(ctx, response, text_renderer=_text)


@workflow_cmd.command("scaffold")
@click.option("--intent", "-i", required=True, help="Original user request / task intent to scaffold.")
@click.option("--bot", "owning_bots", multiple=True, help="Owning Bot ID(s) in BotRegistry.")
@click.option("--acceptance-test", default=None, help="Acceptance test (defaults to original intent).")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without writing YAML.")
@click.pass_context
def workflow_scaffold(
    ctx: click.Context,
    intent: str,
    owning_bots: tuple[str, ...],
    acceptance_test: str | None,
    dry_run: bool,
) -> None:
    """Scaffold a declarative workflow YAML under cfg/factories/ and bind it in AgentGraph."""
    bot = MCPWorkflowEngineBot(cwd=Path.cwd())
    res = bot.scaffold_workflow(
        intent=intent,
        owning_bots=list(owning_bots) if owning_bots else None,
        acceptance_test=acceptance_test,
        dry_run=dry_run,
    )
    response = _build_response(ctx, command="workflow.scaffold", state="ok", dry_run=dry_run, data=res)

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        console.print(
            f"{prefix}[bold green]✓ Scaffolded Declarative Workflow:[/bold green] [cyan]{res['file']}[/cyan] "
            f"(owners={res['owning_bots']}, acceptance_test='{res['acceptance_test']}')"
        )

    _emit_response(ctx, response, text_renderer=_text)


@workflow_cmd.command("run")
@click.argument("intent_or_workflow_id")
@click.option("--max-age-hours", default=4.0, type=float, show_default=True, help="Pre-task calibration TTL in hours.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution.")
@click.pass_context
def workflow_run(
    ctx: click.Context,
    intent_or_workflow_id: str,
    max_age_hours: float,
    dry_run: bool,
) -> None:
    """Execute a workflow with pre-task 4-hour calibration, Phoenix trace propagation, and Cruise Control sync."""
    bot = MCPWorkflowEngineBot(cwd=Path.cwd())
    res = bot.execute_workflow_first(
        intent_or_workflow_id,
        max_age_hours=max_age_hours,
        dry_run=dry_run,
    )
    state = "ok" if res.get("success") else "degraded"
    response = _build_response(ctx, command="workflow.run", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("success"):
            wf = res["workflow"]
            console.print(
                f"[bold green]✓ Executed Workflow:[/bold green] [cyan]{wf['workflow_id']}[/cyan] "
                f"(status={res['status']}, trace={res['phoenix_trace']['traceparent']})"
            )
        else:
            offer = res.get("missing_workflow_offer") or {}
            console.print(f"[bold yellow]! Workflow Offer Required:[/bold yellow] {offer.get('message', '')}")

    _emit_response(ctx, response, text_renderer=_text)


@workflow_cmd.command("cascade")
@click.option("--intent", "-i", required=True, help="Task intent to run through the 4-stage iteration cascade.")
@click.option("--stage2-confidence", default=0.90, type=float, show_default=True)
@click.option("--stage3-confidence", default=0.90, type=float, show_default=True)
@click.option("--strict/--no-strict", default=True, help="Enforce strict Workflow-First check at Stage 1.")
@click.pass_context
def workflow_cascade(
    ctx: click.Context,
    intent: str,
    stage2_confidence: float,
    stage3_confidence: float,
    strict: bool,
) -> None:
    """Execute the 4-Stage Iteration Cascade (Task -> CLI/MCP -> Computer -> Web) for a task intent."""
    from hath0r_cli.bots.iteration_cascade_bot import IterationCascadeBot

    bot = IterationCascadeBot(cwd=Path.cwd())
    res = bot.execute_cascade(
        intent,
        stage2_confidence=stage2_confidence,
        stage3_confidence=stage3_confidence,
        strict_workflow_first=strict,
    )
    state = "ok" if res.get("success") else "degraded"
    response = _build_response(ctx, command="workflow.cascade", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print(
                f"[bold green]✓ 4-Stage Cascade Completed:[/bold green] stages={res['completed_stages']}, "
                f"adherence={res['adherence_rate']}"
            )
        else:
            console.print(f"[bold yellow]! Cascade Halted at Stage 1 (Missing-Workflow Offer):[/bold yellow] {intent}")

    _emit_response(ctx, response, text_renderer=_text)

