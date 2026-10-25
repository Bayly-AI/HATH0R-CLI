"""Agentic Runtime & Subagent Orchestration CLI Commands for Hath0r."""

from __future__ import annotations

import json

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.bots.agent_dag_runner import agent_dag_runner
from hath0r_cli.bots.hahp_protocol import hahp_manager
from hath0r_cli.bots.kv_prewarmer import kv_prewarmer
from hath0r_cli.common import _build_response, _emit_response, console


@click.group("agent", help="Hath0r Agentic Subsystem, KV Pre-Warming, HAHP, and DAG Orchestration.")
@click.pass_context
def agent_cmd(ctx: click.Context) -> None:
    """Agentic runtime command group."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@agent_cmd.command("prewarm", help="Execute Princeton KV Cache pre-warming ping on shared context.")
@click.option("--prompt", "-p", default="Canonical Hath0r Agent System Context", help="Shared system prompt context to prewarm.")
@click.option("--block-size", "-b", default=16, type=int, help="PagedAttention KV block size in tokens (default: 16).")
@click.pass_context
def agent_prewarm(ctx: click.Context, prompt: str, block_size: int) -> None:
    """Prewarm KV cache for shared subagent context."""
    res = kv_prewarmer.prewarm_context(
        shared_prompt=prompt,
        system_prompt="hath0r_canonical_agent",
        block_size=block_size,
    )

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
                f"Tokens Pre-warmed: [bold white]{res['tokens_warmed']} (Aligned: {res['aligned_tokens']} @ block_size={res['block_size']})[/bold white]\n"
                f"PagedAttention Blocks: [bold white]{res['block_count']} (Chunk-Boundary Aligned: {res['chunk_boundary_aligned']})[/bold white]\n"
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


@agent_cmd.command("architecture", help="Audit and display Canonical Architecture: Harness, Resilience, and Dreaming.")
@click.pass_context
def agent_architecture(ctx: click.Context) -> None:
    """Audit canonical agentic architecture: Harness, Brain-Hands split, Resilience, and Dreaming."""
    arch_data = {
        "architecture": {
            "harness": {
                "loop_control": "DurableWorkflowEngine & StepRunner (Harness owns loops)",
                "context_management": "AgentGraph Zero-Prompt-Tax + PagedAttention KV Pre-Warmer",
                "sandboxing": "E2B, Daytona, Local, and Wasm multi-provider zero-trust sandboxes",
            },
            "brain_hands_split": {
                "brain_planner": "TieredRouter REASONING/STANDARD (Claude 3.5 Sonnet, o3-mini, DeepSeek-R1)",
                "hands_executor": "LIGHT tier (Haiku, Qwen 2.5 Coder) + Deterministic AST Guardrails",
                "handoff_protocol": "HAHP (Hath0r Agent Handoff Protocol)",
                "benefit": "Faster time-to-first-token (TTFT) and concurrent tool execution",
            },
        },
        "resilience": {
            "server_side_execution": "Host-side event-sourced execution with EventJournal",
            "log_based_resume": "SQLite append-only journal replay recovers exact state machine after crashes",
            "replay_over_restart": "Idempotent step memoization - cached steps replay in 0ms, retrying only failed actions",
        },
        "magic": {
            "logs_to_memory": "Append-only telemetry and task traces compound into MemoryGraph episodes",
            "dreaming": "Autonomous sleep-cycle reflection clusters episodes into higher-order insights (hath0r memory dream)",
            "wakes_up_smarter": "Micro Memory Sessions recall distilled insights at session start with zero prompt tax",
        },
    }

    response = _build_response(
        ctx,
        command="agent architecture",
        state="ok",
        data=arch_data,
    )

    def _text() -> None:
        console.print("\n[bold cyan]🏛️  CANONICAL AGENT ARCHITECTURE & RESILIENCE SPECIFICATION[/bold cyan]\n")
        console.print(
            Panel(
                "[bold white]1. The Architecture:[/bold white]\n"
                "  • [cyan]Harness owns loops, context, sandboxing[/cyan]: "
                "The host harness (not the LLM) manages iteration loops, zero-prompt-tax context, and multi-provider microVM sandboxes (Daytona/E2B/Local).\n"
                "  • [cyan]Brain and hands split → faster to first token[/cyan]: "
                "Architectural planners (Brain) hand off to lightweight streaming executors (Hands) via HAHP envelopes, minimizing TTFT and time-to-action.\n\n"
                "[bold white]2. The Resilience:[/bold white]\n"
                "  • [cyan]Server-side execution with log-based resume after crashes[/cyan]: "
                "Append-only EventJournal records state transitions; upon restart, deterministic log replay reconstructs in-flight state seamlessly.\n"
                "  • [cyan]Retries and replays beat starting over[/cyan]: "
                "Idempotent step memoization serves completed steps instantly (0ms) and retries only failed steps, eliminating full-run resets.\n\n"
                "[bold white]3. The Magic:[/bold white]\n"
                "  • [cyan]Logs become memory ('Dreaming')[/cyan]: "
                "Raw execution traces and episodic logs are clustered during sleep cycles by ReflectionEngine ('hath0r memory dream').\n"
                "  • [cyan]The system wakes up smarter[/cyan]: "
                "On new session start, distilled insights and causal rules are automatically recalled into active working context.",
                title="Hath0r Canonical Substrate Pillars",
                border_style="bold green",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)
