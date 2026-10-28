"""Evals & Multi-Agent Verification commands for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from hath0r_cli.bots.multiagent_consensus import multiagent_consensus_engine
from hath0r_cli.bots.redteam_engine import multiagent_redteam_engine
from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot
from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.envelope import Diagnostic


@click.group("evals")
def evals_cmd() -> None:
    """Evaluations, 4-tier task completion gates (CR-TASK-EVAL-001), consensus, and Red-Team verification."""
    pass


@evals_cmd.command("run")
@click.option("--task-id", default=None, help="Explicit task ID (defaults to active issue/branch).")
@click.option("--skip-tests", is_flag=True, default=False, help="Skip re-running local pytest/ruff suite.")
@click.option(
    "--compound/--no-compound",
    "compound_node",
    default=True,
    help="Compound eval:<task_id> node into .hath0r/memory/graph.json.",
)
@click.option(
    "--sync-observability/--no-sync-observability",
    default=True,
    help="Emit evaluation telemetry to Arize Phoenix and MLflow.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate evaluation without writing files.")
@click.pass_context
def evals_run(
    ctx: click.Context,
    task_id: Optional[str],
    skip_tests: bool,
    compound_node: bool,
    sync_observability: bool,
    dry_run: bool,
) -> None:
    """Execute 4-tier automatic task evaluation (CR-TASK-EVAL-001) and persist scorecard."""
    bot = TaskEvaluatorBot(cwd=Path.cwd())
    res = bot.evaluate_task(
        task_id=task_id,
        skip_tests=skip_tests,
        compound_node=compound_node,
        sync_observability=sync_observability,
        dry_run=dry_run,
    )
    passed = bool(res.get("passed_gate"))
    state = "ok" if passed else "error"
    diagnostics = []
    for reason in res.get("blocking_reasons", []):
        diagnostics.append(
            Diagnostic(
                code="TASK_EVAL_GATE_FAILED",
                message=reason,
                severity="error",
                provenance={"component": "hath0r-cli", "operation": "evals.run"},
            )
        )

    response = _build_response(
        ctx,
        command="evals.run",
        state=state,
        dry_run=dry_run,
        data=res,
        diagnostics=diagnostics,
    )

    def _text() -> None:
        gate_badge = "[bold green]PASSED[/bold green]" if passed else "[bold red]FAILED[/bold red]"
        console.print(f"\n[bold cyan]Hath0r 4-Tier Task Evaluation Gate (CR-TASK-EVAL-001)[/bold cyan]: {gate_badge}")
        console.print(f"  • Task ID:          [bold white]{res['task_id']}[/bold white] ({res['eval_id']})")
        console.print(
            f"  • Composite Reward: [bold green]{res['r_task']:.4f}[/bold green] "
            f"(Min Threshold: {res['min_reward_threshold']:.2f})"
        )
        t_scores = res.get("tier_scores", {})
        console.print(f"  • Tier 1 (Deterministic): {t_scores.get('deterministic', 0.0):.2f}")
        console.print(f"  • Tier 2 (Trajectory):    {t_scores.get('trajectory', 0.0):.2f}")
        console.print(f"  • Tier 3 (Adversarial):   {t_scores.get('adversarial', 0.0):.2f}")
        console.print(f"  • Tier 4 (Goal Align):    {t_scores.get('goal_alignment', 0.0):.2f}")
        console.print(f"  • Scorecard:        {res['latest_file']}")
        if res.get("compounded_node_id"):
            console.print(f"  • MemoryGraph Node: [bold cyan]{res['compounded_node_id']}[/bold cyan]")
        for reason in res.get("blocking_reasons", []):
            console.print(f"  [bold red]✗ {reason}[/bold red]")

    _emit_response(ctx, response, text_renderer=_text)
    if not passed:
        ctx.exit(1)


@evals_cmd.command("status")
@click.pass_context
def evals_status(ctx: click.Context) -> None:
    """Display the latest task evaluation scorecard from .hath0r/evals/latest.json."""
    bot = TaskEvaluatorBot(cwd=Path.cwd())
    res = bot.get_status()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="evals.status", state=state, data=res)

    def _text() -> None:
        if not res.get("exists"):
            console.print(f"[yellow]{res.get('message')}[/yellow]")
            return
        gate_badge = "[bold green]PASSED[/bold green]" if res.get("passed_gate") else "[bold red]FAILED[/bold red]"
        console.print(f"\n[bold cyan]Latest Task Evaluation Status[/bold cyan]: {gate_badge}")
        console.print(f"  • Eval ID:          {res.get('eval_id')}")
        console.print(f"  • Task ID:          {res.get('task_id')}")
        console.print(f"  • Composite R_task: {res.get('r_task')}")
        console.print(f"  • Evaluated At:     {res.get('evaluated_at')}")
        console.print(f"  • Scorecard File:   {res.get('latest_file')}")

    _emit_response(ctx, response, text_renderer=_text)


@evals_cmd.command("verify")
@click.option("--task-id", default=None, help="Task ID to verify.")
@click.option(
    "--auto-run/--no-auto-run",
    default=True,
    help="Automatically run task evaluation if .hath0r/evals/latest.json is missing.",
)
@click.pass_context
def evals_verify(ctx: click.Context, task_id: Optional[str], auto_run: bool) -> None:
    """Verify pre-announcement task evaluation gate (CR-TASK-EVAL-001)."""
    bot = TaskEvaluatorBot(cwd=Path.cwd())
    res = bot.verify_evaluated(task_id=task_id, auto_run_if_missing=auto_run)
    passed = bool(res.get("passed_gate"))
    state = "ok" if passed else "error"
    diagnostics = []
    if not passed and res.get("error"):
        diagnostics.append(
            Diagnostic(
                code="TASK_EVAL_VERIFY_FAILED",
                message=str(res["error"]),
                severity="error",
                provenance={"component": "hath0r-cli", "operation": "evals.verify"},
            )
        )

    response = _build_response(ctx, command="evals.verify", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if passed:
            console.print(
                f"[bold green]✓ CR-TASK-EVAL-001 Verified:[/bold green] Task '{res.get('task_id')}' "
                f"passed evaluation gate (R_task={res.get('r_task'):.4f})."
            )
        else:
            console.print(f"[bold red]✗ {res.get('error')}[/bold red]")

    _emit_response(ctx, response, text_renderer=_text)
    if not passed:
        ctx.exit(1)


@evals_cmd.command("report")
@click.option("--root", "root_dir", default=None, help="Workspace root directory to scan.")
@click.pass_context
def evals_report(ctx: click.Context, root_dir: Optional[str]) -> None:
    """Aggregate task evaluation scorecards across workspace repositories."""
    bot = TaskEvaluatorBot(cwd=Path.cwd())
    target_root = Path(root_dir).resolve() if root_dir else None
    res = bot.generate_suite_report(root_dir=target_root)
    response = _build_response(ctx, command="evals.report", state="ok", data=res)

    def _text() -> None:
        table = Table(title=f"Hath0r Suite Task Evaluation Report ({res['root_dir']})")
        table.add_column("Repository", style="bold cyan")
        table.add_column("Evaluated", justify="center")
        table.add_column("Gate", justify="center")
        table.add_column("R_task", justify="right", style="magenta")
        table.add_column("Task ID", style="white")
        for r in res.get("repos", []):
            ev_str = "✓" if r["evaluated"] else "—"
            gate_str = "[green]PASS[/green]" if r["passed_gate"] else ("[red]FAIL[/red]" if r["evaluated"] else "—")
            r_str = f"{r['r_task']:.4f}" if r["r_task"] is not None else "—"
            table.add_row(r["repo"], ev_str, gate_str, r_str, str(r["task_id"] or "—"))
        console.print(table)
        console.print(
            f"Evaluated Repos: {res['evaluated_repos']}/{res['total_repos']} | "
            f"Mean R_task: [bold green]{res['mean_r_task']:.4f}[/bold green]"
        )

    _emit_response(ctx, response, text_renderer=_text)


@evals_cmd.command("ensure-all")
@click.option(
    "--root",
    "root_dir",
    default=None,
    help="Root workspace directory to scan (defaults to /Users/raybayly/Development).",
)
@click.option(
    "--run-eval/--no-run-eval",
    default=True,
    help="Run initial 4-tier evaluation across every discovered repository.",
)
@click.option(
    "--sync-agents-md/--no-sync-agents-md",
    default=True,
    help="Ensure AGENTS.md and WARP.md contain the canonical CR-TASK-EVAL-001 directive.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Preview provisioning without writing files.")
@click.pass_context
def evals_ensure_all(
    ctx: click.Context,
    root_dir: Optional[str],
    run_eval: bool,
    sync_agents_md: bool,
    dry_run: bool,
) -> None:
    """Provision CR-TASK-EVAL-001 config, AGENTS.md directives, and baseline scorecards across all repositories."""
    bot = TaskEvaluatorBot(cwd=Path.cwd())
    res = bot.ensure_all_repos(
        root_dir=root_dir,
        run_eval=run_eval,
        sync_agents_md=sync_agents_md,
        dry_run=dry_run,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="evals.ensure_all", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        table = Table(title=f"CR-TASK-EVAL-001 Workspace Enforcement ({res['root_dir']})")
        table.add_column("Repository", style="bold cyan")
        table.add_column("Cfg", justify="center")
        table.add_column("AGENTS.md", justify="center")
        table.add_column("Gate", justify="center")
        table.add_column("R_task", justify="right", style="magenta")
        for r in res.get("repos", []):
            cfg_str = "[green]+created[/green]" if r.get("cfg_created") else "✓"
            ag_str = "[green]+updated[/green]" if r.get("agents_md_updated") else "✓"
            gate_str = "[green]PASS[/green]" if r.get("passed_gate") else "[red]FAIL[/red]"
            r_str = f"{float(r.get('r_task') or 0.0):.4f}"
            table.add_row(str(r.get("repo")), cfg_str, ag_str, gate_str, r_str)
        console.print(table)
        console.print(
            f"[bold green]✓ Enforced CR-TASK-EVAL-001 across {res['passed_repos']}/{res['repos_count']} repositories.[/bold green]"
        )

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


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
        console.print("\n[bold cyan]Multi-Agent Consensus Evaluation Gate[/bold cyan]")
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
        console.print("\n[bold green]✓ Multi-Agent Red-Team Adversarial Verification Completed[/bold green]")
        console.print(f"Target Component: [bold cyan]{res['component_under_test']}[/bold cyan]")
        console.print(f"Survival Gate: [bold green]{res['survival_gate']}[/bold green]")
        console.print(f"Attack Vectors Survived: [bold white]{res['attack_vectors_count']}[/bold white]")
    _emit_response(ctx, response, text_renderer=_text)


# Register gameshow subcommand under evals group
from hath0r_cli.commands.gameshow import gameshow_cmd  # noqa: E402

evals_cmd.add_command(gameshow_cmd, name="gameshow")
