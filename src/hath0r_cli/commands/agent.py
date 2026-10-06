"""Agentic Runtime & Subagent Orchestration CLI Commands for Hath0r."""

from __future__ import annotations

import json
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.bots.kv_prewarmer import kv_prewarmer
from hath0r_cli.bots.hahp_protocol import hahp_manager
from hath0r_cli.bots.agent_dag_runner import agent_dag_runner


@click.group("agent", help="Hath0r Agentic Subsystem, KV Pre-Warming, HAHP, and DAG Orchestration.")
@click.pass_context
def agent_cmd(ctx: click.Context) -> None:
    """Agentic runtime command group."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@agent_cmd.command("prewarm", help="Execute Princeton KV Cache pre-warming ping on shared context.")
@click.option("--prompt", "-p", default="Canonical Hath0r Agent System Context", help="Shared system prompt context to prewarm.")
@click.pass_context
def agent_prewarm(ctx: click.Context, prompt: str) -> None:
    """Prewarm KV cache for shared subagent context."""
    res = kv_prewarmer.prewarm_context(shared_prompt=prompt, system_prompt="hath0r_canonical_agent")
    
    response = _build_response(
        ctx,
        command="agent prewarm",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print(
            Panel(
                f"[bold green]✓ Princeton KV Cache Pre-Warming Gate Executed[/bold green]\n\n"
                f"Context Hash: [bold cyan]{res['context_hash']}[/bold cyan]\n"
                f"Tokens Pre-warmed: [bold white]{res['tokens_warmed']}[/bold white]\n"
                f"Prefill Latency: [bold white]{res['prefill_latency_ms']} ms[/bold white]\n"
                f"Estimated Subagent Latency Reduction: [bold green]{res['cache_hit_reduction_pct']}%[/bold green]",
                title="Hath0r KV Pre-Warmer",
                border_style="bold cyan",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)


@agent_cmd.command("dag", help="Execute Multi-Agent DAG workflow dependency spec.")
@click.option("--spec", "-s", type=click.Path(exists=True), help="Path to JSON/YAML DAG workflow spec file.")
@click.option("--demo", is_flag=True, help="Run built-in multi-agent parallel fan-out / barrier demo DAG.")
@click.pass_context
def agent_dag(ctx: click.Context, spec: str | None, demo: bool) -> None:
    """Execute Multi-Agent DAG runner."""
    if demo or not spec:
        dag_spec = {
            "name": "hath0r_phase1_demo_dag",
            "shared_system_prompt": "Hath0r Multi-Agent Subagent Subgraph",
            "nodes": [
                {"id": "researcher", "agent_role": "Codebase Researcher", "depends_on": []},
                {"id": "planner", "agent_role": "Architecture Planner", "depends_on": []},
                {"id": "evaluator", "agent_role": "Quality Evaluator Barrier", "depends_on": ["researcher", "planner"], "type": "barrier"},
            ]
        }
    else:
        with open(spec, "r", encoding="utf-8") as f:
            dag_spec = json.load(f)

    res = agent_dag_runner.execute_dag(dag_spec)
    response = _build_response(
        ctx,
        command="agent dag",
        state="ok" if res.get("status") == "success" else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("status") == "success":
            console.print("\n[bold green]✓ Multi-Agent DAG Workflow Executed Successfully[/bold green]")
            console.print(f"DAG Name: [bold cyan]{res['dag_name']}[/bold cyan]")
            console.print(f"Total Nodes: [bold white]{res['total_nodes']}[/bold white]")
            console.print(f"Execution Order: [bold yellow]{' -> '.join(res['execution_order'])}[/bold yellow]")
            console.print(f"Elapsed Time: [bold white]{res['elapsed_ms']} ms[/bold white]\n")

            table = Table(title="Node Execution Summary", border_style="cyan")
            table.add_column("Node ID", style="bold white")
            table.add_column("Agent Role", style="cyan")
            table.add_column("HAHP Envelope ID", style="magenta")
            table.add_column("Barrier (Fan-in)", style="yellow")

            for node_id, out in res.get("node_outputs", {}).items():
                table.add_row(
                    node_id,
                    out.get("agent_role", ""),
                    out.get("envelope_id", ""),
                    "✅ Yes" if out.get("is_barrier") else "No",
                )
            console.print(table)
        else:
            console.print(f"[bold red]❌ DAG Execution Error:[/bold red] {res.get('message')}")

    _emit_response(ctx, response, text_renderer=_text)


@agent_cmd.command("hahp", help="Inspect or issue Structured Hath0r Agent Handoff Protocol (HAHP) envelopes.")
@click.option("--sender", default="planner_agent", help="Sender agent ID.")
@click.option("--recipient", default="executor_agent", help="Recipient agent ID.")
@click.option("--scratchpad", default="Refactored module dependencies and updated tests.", help="Working memory scratchpad.")
@click.pass_context
def agent_hahp(ctx: click.Context, sender: str, recipient: str, scratchpad: str) -> None:
    """Create and validate HAHP handoff envelope."""
    envelope = hahp_manager.create_envelope(
        sender_agent=sender,
        recipient_agent=recipient,
        scratchpad_delta=scratchpad,
        state_variables={"active_phase": 1, "status": "in_progress"},
    )

    data = envelope.model_dump()
    response = _build_response(
        ctx,
        command="agent hahp",
        state="ok",
        data=data,
    )

    def _text() -> None:
        console.print(
            Panel(
                f"[bold green]✓ HAHP State Handoff Envelope Created & Serialized[/bold green]\n\n"
                f"Handoff ID: [bold cyan]{envelope.handoff_id}[/bold cyan]\n"
                f"Sender: [bold white]{envelope.sender_agent}[/bold white] ➔ Recipient: [bold white]{envelope.recipient_agent}[/bold white]\n"
                f"Scratchpad: [bold yellow]{envelope.scratchpad_delta}[/bold yellow]\n"
                f"Session Sync: [bold green]Redis & DynamoDB Synced[/bold green]",
                title="HAHP Protocol Manager",
                border_style="bold green",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)


@agent_cmd.command("status", help="Inspect status of pre-warmer, HAHP protocol, and DAG execution runner.")
@click.pass_context
def agent_status(ctx: click.Context) -> None:
    """Inspect overall agent subsystem status."""
    telemetry = kv_prewarmer.get_telemetry()
    handoffs = hahp_manager.list_handoffs()

    status_data = {
        "kv_prewarmer_telemetry": telemetry,
        "active_hahp_handoffs_count": len(handoffs),
        "recent_handoffs": handoffs[-3:] if handoffs else [],
    }

    response = _build_response(
        ctx,
        command="agent status",
        state="ok",
        data=status_data,
    )

    def _text() -> None:
        console.print("\n[bold cyan]🤖 Hath0r Agentic Subsystem Status & Telemetry[/bold cyan]\n")
        table = Table(title="KV Prewarmer & HAHP Metrics", border_style="bold cyan")
        table.add_column("Metric", style="bold white")
        table.add_column("Value", style="green")

        table.add_row("Total Context Prewarms", str(telemetry["total_prewarms"]))
        table.add_row("Cached Contexts", str(telemetry["cached_contexts"]))
        table.add_row("Total Cache Hits", str(telemetry["total_cache_hits"]))
        table.add_row("Estimated Prefill Latency Reduction", f"{telemetry['prefill_reduction_pct']}%")
        table.add_row("Active HAHP Handoff Envelopes", str(len(handoffs)))

        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)
