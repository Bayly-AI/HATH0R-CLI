"""TLP (Task-Level, Thread-Level, and Temporal Logic Planning) commands for Hath0r CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import click
from rich.table import Table

from hath0r_cli.bots.task_level_planner_bot import TaskExecutionDAG, task_level_planner
from hath0r_cli.bots.temporal_logic_planner_bot import temporal_logic_planner
from hath0r_cli.bots.thread_parallelism_bot import thread_parallelism
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("tlp")
def tlp() -> None:
    """TLP Subsystem: Task-Level Planning, Thread-Level Parallelism, and Temporal Verification."""


@tlp.command("plan")
@click.option("--goal", "-g", required=True, help="High-level objective or macro-task description.")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "json", "mermaid"], case_sensitive=False),
    default="text",
    show_default=True,
    help="Plan visualization format.",
)
@click.option("--output-file", "-o", type=click.Path(path_type=Path), default=None, help="Save generated DAG to JSON file.")
@click.pass_context
def tlp_plan(
    ctx: click.Context,
    goal: str,
    output_format: str,
    output_file: Optional[Path],
) -> None:
    """Decompose a macro-goal into a dependency-aware Task Execution DAG."""
    dag = task_level_planner.create_plan(goal=goal)
    tiers = task_level_planner.topological_sort(dag)
    mermaid_diag = task_level_planner.export_mermaid(dag)

    if output_file:
        output_file.write_text(json.dumps(dag.to_dict(), indent=2), encoding="utf-8")

    data = {
        "dag": dag.to_dict(),
        "tiers": tiers,
        "mermaid": mermaid_diag,
        "saved_to": str(output_file) if output_file else None,
    }

    response = _build_response(ctx, command="tlp.plan", state="ok", data=data)

    def _text() -> None:
        if output_format.lower() == "mermaid":
            click.echo(mermaid_diag)
            return

        if output_format.lower() == "json":
            click.echo(json.dumps(dag.to_dict(), indent=2))
            return

        console.print(f"\n[bold cyan]Task Execution DAG:[/bold cyan] {dag.goal} ([dim]{dag.dag_id}[/dim])")
        console.print("=" * 65)

        for idx, tier in enumerate(tiers):
            console.print(f"\n[bold green]Tier {idx + 1}[/bold green] (Independent concurrent steps):")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Task ID", style="cyan")
            table.add_column("Title")
            table.add_column("Depends On")
            table.add_column("Tools", style="dim")
            table.add_column("Est. Tokens", justify="right")

            for nid in tier:
                node = dag.nodes[nid]
                table.add_row(
                    node.id,
                    node.title,
                    ", ".join(node.depends_on) or "-",
                    ", ".join(node.required_tools) or "-",
                    str(node.estimated_tokens),
                )
            console.print(table)

        if output_file:
            console.print(f"\n[dim]DAG serialized to {output_file}[/dim]")

    _emit_response(ctx, response, text_renderer=_text)


@tlp.command("run")
@click.option("--goal", "-g", default=None, help="High-level goal to plan and execute.")
@click.option("--plan", "-p", "plan_file", type=click.Path(exists=True, path_type=Path), default=None, help="Path to JSON plan file.")
@click.option("--parallel/--sequential", default=True, show_default=True, help="Execute independent tasks concurrently using TLP.")
@click.option("--max-workers", "-w", type=int, default=4, show_default=True, help="Maximum concurrent worker threads.")
@click.option("--timeout", "-t", type=int, default=60, show_default=True, help="Timeout per task in seconds.")
@click.pass_context
def tlp_run(
    ctx: click.Context,
    goal: Optional[str],
    plan_file: Optional[Path],
    parallel: bool,
    max_workers: int,
    timeout: int,
) -> None:
    """Execute a Task DAG using Thread-Level Parallelism with context isolation."""
    if not goal and not plan_file:
        raise click.UsageError("Must specify either --goal or --plan.")

    if plan_file:
        plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
        dag = TaskExecutionDAG.from_dict(plan_data)
    else:
        dag = task_level_planner.create_plan(goal=goal)  # type: ignore[arg-type]

    workers = max_workers if parallel else 1
    result = thread_parallelism.run_parallel_dag(
        dag=dag,
        max_workers=workers,
        timeout_per_step=timeout,
    )

    response = _build_response(
        ctx,
        command="tlp.run",
        state="ok" if result["success"] else "degraded",
        data=result,
    )

    def _text() -> None:
        console.print(f"\n[bold cyan]TLP Execution Summary:[/bold cyan] {result['goal']} ([dim]{result['dag_id']}[/dim])")
        console.print("=" * 70)
        console.print(f"Status: [{'green' if result['success'] else 'red'}]{'SUCCESS' if result['success'] else 'FAILED'}[/]")
        console.print(f"Completed Nodes: {result['completed_nodes']} / {result['total_nodes']}")
        console.print(f"Total Latency: {result['total_latency_ms']} ms")
        console.print(f"Tokens Used: {result['finops']['total_tokens']} (${result['finops']['total_cost_usd']:.4f})")

        table = Table(title="Thread Execution Details", show_header=True, header_style="bold cyan")
        table.add_column("Node ID", style="cyan")
        table.add_column("Thread ID", style="dim")
        table.add_column("Status")
        table.add_column("Latency (ms)", justify="right")
        table.add_column("Tokens", justify="right")

        for r in result["records"]:
            status_style = "[green]✓ completed[/green]" if r["status"] == "completed" else f"[red]✗ {r['error']}[/red]"
            table.add_row(
                r["node_id"],
                r["thread_id"],
                status_style,
                str(r["latency_ms"]),
                str(r["tokens_used"]),
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@tlp.command("verify")
@click.option("--trajectory", "-t", default=None, help="Comma-separated event sequence (e.g. 'local,development,testing,staging,master').")
@click.option("--plan", "-p", "plan_file", type=click.Path(exists=True, path_type=Path), default=None, help="Plan file to extract sequence from.")
@click.option(
    "--policy",
    type=click.Choice(["all", "cr-bai-001", "cr-hathor-init-001", "cr-cicccd-001"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Temporal policy specification to evaluate.",
)
@click.pass_context
def tlp_verify(
    ctx: click.Context,
    trajectory: Optional[str],
    plan_file: Optional[Path],
    policy: str,
) -> None:
    """Verify an execution trace or plan against Temporal Logic Planning (TLP) automata."""
    trace: List[str] = []
    if trajectory:
        trace = [item.strip() for item in trajectory.split(",") if item.strip()]
    elif plan_file:
        plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
        dag = TaskExecutionDAG.from_dict(plan_data)
        # Extract ordered task IDs as trajectory
        tiers = task_level_planner.topological_sort(dag)
        for t in tiers:
            trace.extend(t)
    else:
        raise click.UsageError("Must specify either --trajectory or --plan.")

    report = temporal_logic_planner.verify_trace(trace=trace, policy_name=policy.lower())

    response = _build_response(
        ctx,
        command="tlp.verify",
        state="ok" if report["valid"] else "degraded",
        data=report,
    )

    def _text() -> None:
        console.print("\n[bold cyan]Temporal Logic Planning (TLP) Verification Report[/bold cyan]")
        console.print("=" * 70)
        console.print(f"Overall Status: [{'green' if report['valid'] else 'red'}]{'VERIFIED (Compliant)' if report['valid'] else 'VIOLATION DETECTED'}[/]")
        console.print(f"Trace Length: {report['trace_length']} steps: [dim]{' -> '.join(trace)}[/dim]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Policy Automaton", style="bold cyan")
        table.add_column("Status")
        table.add_column("States Visited")
        table.add_column("Rejection Details / Invariant")

        for pol_id, res in report["results"].items():
            if res.get("valid"):
                status_str = "[green]✓ Compliant[/green]"
                detail_str = "[green]Accepted by DFA[/green]"
            else:
                status_str = "[red]✗ Violates Policy[/red]"
                detail_str = f"[red]{res.get('rejection_reason', 'Rejection')}[/red]"

            table.add_row(
                pol_id,
                status_str,
                " -> ".join(res.get("states_visited", [])),
                detail_str,
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)
