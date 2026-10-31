"""Architecture Preservation, Substrate Utilization & Task Completion Verifier CLI (`hath0r arch`)."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from hath0r_cli.bots.architecture_preservation_bot import ArchitecturePreservationBot
from hath0r_cli.bots.substrate_utilization_bot import SubstrateUtilizationBot
from hath0r_cli.bots.task_completion_verifier_bot import TaskCompletionVerifierBot
from hath0r_cli.common import _build_response, _emit_response, console


@click.group("arch")
def arch_cmd() -> None:
    """Verify CR-FEATURE-WORKFLOW-STANDARD-001 architecture, substrate utilization, and completion gates."""


@arch_cmd.command("verify")
@click.option("--fleet", is_flag=True, default=False, help="Verify across all 5 suite repositories.")
@click.pass_context
def arch_verify(ctx: click.Context, fleet: bool) -> None:
    """Verify CR-FEATURE-WORKFLOW-STANDARD-001 (Service >= 1 Bot, Level 1/2 AgentGraph, Workflow-First)."""
    bot = ArchitecturePreservationBot(cwd=Path.cwd())
    res = bot.verify_fleet() if fleet else bot.verify_repo()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="arch.verify", state=state, data=res)

    def _text() -> None:
        if fleet:
            table = Table(title=f"Suite Architecture Verification ({res['repos_checked']} Repos)")
            table.add_column("Repo", style="bold cyan")
            table.add_column("Status")
            table.add_column("Commands", justify="right")
            table.add_column("Bots", justify="right")
            for r in res.get("repos", []):
                table.add_row(
                    str(r.get("repo", "")),
                    "[green]PASS[/green]" if r.get("success") else "[red]FAIL[/red]",
                    str(r.get("commands_verified", 0)),
                    str(r.get("registered_bots_count", 0)),
                )
            console.print(table)
        else:
            console.print(
                f"[bold green]✓ Architecture Verified ({res['repo']}):[/bold green] "
                f"commands={res['commands_verified']}, bots={res['registered_bots_count']}"
            )

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@arch_cmd.command("substrate")
@click.pass_context
def arch_substrate(ctx: click.Context) -> None:
    """Audit AST & runtime utilization of SuperSqueeze, OTel/Phoenix, OpenFeature, and OpenObservation."""
    bot = SubstrateUtilizationBot(cwd=Path.cwd())
    res = bot.audit_substrate()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="arch.substrate", state=state, data=res)

    def _text() -> None:
        console.print(
            f"[bold green]✓ Substrate Utilization Audit:[/bold green] scanned={res['scanned_files']} files, "
            f"ddtrace_imports={len(res['ddtrace_imports'])}"
        )

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@arch_cmd.command("completion")
@click.option("--require-eval/--no-require-eval", default=True, help="Require passing continuous 4-tier eval.")
@click.pass_context
def arch_completion(ctx: click.Context, require_eval: bool) -> None:
    """Run TaskCompletionVerifierBot and FactSettlementEngine probes prior to announcing complete."""
    bot = TaskCompletionVerifierBot(cwd=Path.cwd())
    res = bot.verify_completion(require_eval=require_eval)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="arch.completion", state=state, data=res)

    def _text() -> None:
        console.print(
            f"[bold cyan]Task Completion Verification:[/bold cyan] "
            f"{'[green]PASS[/green]' if res['success'] else '[red]FAIL[/red]'} "
            f"(R_task={res['composite_reward']:.4f}, blockers={res['open_cruise_control_blockers']})"
        )

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
