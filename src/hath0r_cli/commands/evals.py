"""Evals & Multi-Agent Verification commands for HATH0R CLI."""

from __future__ import annotations

import click
from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.bots.multiagent_consensus import multiagent_consensus_engine
from hath0r_cli.bots.redteam_engine import multiagent_redteam_engine


@click.group("evals")
def evals_cmd() -> None:
    """Evaluations, consensus gates, and adversarial Red-Team verification loops."""
    pass


@evals_cmd.command("consensus")
@click.option("--threshold", default=0.70, type=float, help="Agreement score threshold (0.0 - 1.0).")
@click.pass_context
def evals_consensus(ctx: click.Context, threshold: float) -> None:
    """Evaluate agreement and compute consensus score across peer agent outputs."""
    sample_agent_outputs = [
        {"agent_id": "agent_1", "output": "Approved refactor with 0 errors"},
        {"agent_id": "agent_2", "output": "Approved refactor with 0 errors"},
        {"agent_id": "agent_3", "output": "Approved refactor with 0 errors"},
    ]
    multiagent_consensus_engine.consensus_threshold = threshold
    res = multiagent_consensus_engine.evaluate_consensus(sample_agent_outputs)

    response = _build_response(ctx, command="evals.consensus", state="ok", data=res)

    def _text() -> None:
        console.print(f"\n[bold cyan]Multi-Agent Consensus Evaluation Gate[/bold cyan]")
        console.print(f"Consensus Score: [bold green]{res['consensus_score']}[/bold green] (Threshold: {threshold})")
        console.print(f"Evaluator Gate: {'[bold green]PASSED[/bold green]' if res['passed_gate'] else '[bold red]FAILED[/bold red]'}")
        console.print(f"Agreed Agents: {res['agreed_agent_count']} / {res['total_agents']}")
        if res.get("fallback_human_in_loop_required"):
            console.print("  [bold yellow]⚠️ Consensus low: Human-in-the-loop review triggered.[/bold yellow]")

    _emit_response(ctx, response, text_renderer=_text)


@evals_cmd.command("redteam")
@click.option("--component", default="agent_subsystem", help="Target component for Red-Team stress testing.")
@click.pass_context
def evals_redteam(ctx: click.Context, component: str) -> None:
    """Execute adversarial Red-Team vs Blue-Team stress verification loop."""
    res = multiagent_redteam_engine.run_redteam_verification(component_name=component)

    response = _build_response(ctx, command="evals.redteam", state="ok", data=res)

    def _text() -> None:
        console.print(f"\n[bold green]✓ Multi-Agent Red-Team Adversarial Verification Completed[/bold green]")
        console.print(f"Target Component: [bold cyan]{res['component_under_test']}[/bold cyan]")
        console.print(f"Survival Gate: [bold green]{res['survival_gate']}[/bold green]")
        console.print(f"Attack Vectors Survived: [bold white]{res['attack_vectors_count']}[/bold white]")
        console.print(f"Adversarial Suite: [bold yellow]{res['adversarial_test_file']}[/bold yellow]")

    _emit_response(ctx, response, text_renderer=_text)
