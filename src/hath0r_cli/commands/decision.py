"""HATH0R CLI 'decision' / 'cruise' command group — Cruise Control Agent Decision Control Layer.

Implements Task 5 (#504) & #508:
- hath0r cruise / hath0r decision ask / wait / list / answer / reject
- hath0r cruise / hath0r decision snooze / assert-fact / settle
- hath0r cruise / hath0r decision approve-in / approve-out / dep
- hath0r cruise / hath0r decision radar / tui
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli.bots.decision_radar_bot import CANONICAL_CATEGORIES, DecisionRadarBot
from hath0r_cli.server.decision_radar_server import (
    DEFAULT_CRUISE_PORT,
    HathorDecisionRadarServer,
    build_local_radar_url,
    launch_cruise_control_split_window,
    render_radar_tui,
)

console = Console()

_SPLIT_WINDOW_FLAG = "--split-window/--no-split-window"
_SPLIT_WINDOW_HELP = "Auto-open Cruise Control in a split-window browser display."
_SPLIT_SIDE_OPT = "--split-side"
_SPLIT_SIDE_HELP = "Screen half for Cruise Control split browser window (right or left)."


def _split_csv(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@click.group("decision")
def decision_cmd() -> None:
    """Cruise Control Agent Decision Control Layer & Unblocking Engine."""


@decision_cmd.command("ask")
@click.option("--question", "-q", required=True, help="Question or decision needed from the operator.")
@click.option(
    "--category",
    "-c",
    default="set_product_rule",
    show_default=True,
    type=click.Choice(list(CANONICAL_CATEGORIES.keys()), case_sensitive=False),
    help="Canonical radar wedge category.",
)
@click.option("--agent", "-a", "agent_id", default="@agent", show_default=True, help="Waiting agent identifier.")
@click.option("--unblocks", "-u", default="", help="Comma-separated downstream tasks/agents unblocked.")
@click.option("--options", default="", help="Comma-separated answer options.")
@click.option("--fact", "--wait-for-fact", "wait_for_fact", default=None, help="Declarative fact predicate to wait on.")
@click.option("--criticality", default=1.0, type=float, show_default=True, help="Criticality multiplier.")
@click.option(_SPLIT_WINDOW_FLAG, default=True, show_default=True, help=_SPLIT_WINDOW_HELP)
@click.option(_SPLIT_SIDE_OPT, default="right", show_default=True, help=_SPLIT_SIDE_HELP)
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_ask(
    question: str,
    category: str,
    agent_id: str,
    unblocks: str,
    options: str,
    wait_for_fact: Optional[str],
    criticality: float,
    split_window: bool,
    split_side: str,
    as_json: bool,
) -> None:
    """Submit a non-blocking agent decision to the radar queue and display in split browser window."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.request_decision(
        question=question,
        category=category,
        agent_id=agent_id,
        unblocks=_split_csv(unblocks),
        options=_split_csv(options),
        wait_for_fact=wait_for_fact,
        criticality=criticality,
        split_window=split_window,
        split_side=split_side,
    )
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    dec = res["decision"]
    console.print(
        f"[bold green]✓ Decision queued:[/bold green] [cyan]{dec['decision_id']}[/cyan] "
        f"({dec['category_label']}) — [yellow]|| {dec['unblock_badge']} (U={dec['unblock_weight']})[/yellow]"
    )
    win = res.get("browser_window")
    if isinstance(win, dict) and win.get("url"):
        console.print(
            f"[bold blue]◫ Split-window Cruise Control ({win.get('layout')}):[/bold blue] [cyan]{win['url']}[/cyan]"
        )


@decision_cmd.command("wait")
@click.option("--question", "-q", required=True, help="Question blocking the current agent terminal.")
@click.option(
    "--category",
    "-c",
    default="set_product_rule",
    show_default=True,
    type=click.Choice(list(CANONICAL_CATEGORIES.keys()), case_sensitive=False),
    help="Canonical radar wedge category.",
)
@click.option("--agent", "-a", "agent_id", default="@agent", show_default=True, help="Waiting agent identifier.")
@click.option("--unblocks", "-u", default="", help="Comma-separated downstream tasks/agents unblocked.")
@click.option("--fact", "--wait-for-fact", "wait_for_fact", default=None, help="Fact predicate that settles this wait.")
@click.option("--criticality", default=1.0, type=float, show_default=True, help="Criticality multiplier.")
@click.option("--timeout", default=0.5, type=float, show_default=True, help="Seconds to wait before returning state.")
@click.option("--poll-interval", default=0.1, type=float, show_default=True, help="Polling interval in seconds.")
@click.option("--live-probes", is_flag=True, default=False, help="Run live Git/GH probes during wait.")
@click.option(_SPLIT_WINDOW_FLAG, default=True, show_default=True, help=_SPLIT_WINDOW_HELP)
@click.option(_SPLIT_SIDE_OPT, default="right", show_default=True, help=_SPLIT_SIDE_HELP)
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_wait(
    question: str,
    category: str,
    agent_id: str,
    unblocks: str,
    wait_for_fact: Optional[str],
    criticality: float,
    timeout: float,
    poll_interval: float,
    live_probes: bool,
    split_window: bool,
    split_side: str,
    as_json: bool,
) -> None:
    """Register an agent decision, open split-window Cruise Control, and wait for resolution."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    req = bot.request_decision(
        question=question,
        category=category,
        agent_id=agent_id,
        unblocks=_split_csv(unblocks),
        wait_for_fact=wait_for_fact,
        criticality=criticality,
    )
    dec_id = str(req["decision"]["decision_id"])
    res = bot.wait_for_resolution(
        decision_id=dec_id,
        timeout_seconds=timeout,
        poll_interval=poll_interval,
        live_probes=live_probes,
        split_window=split_window,
        split_side=split_side,
    )
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    win = res.get("browser_window")
    if isinstance(win, dict) and win.get("url"):
        console.print(
            f"[bold blue]◫ Split-window Cruise Control ({win.get('layout')}):[/bold blue] [cyan]{win['url']}[/cyan]"
        )
    dec = res.get("decision", {})
    if res.get("resolved"):
        console.print(
            f"[bold green]✓ Decision {dec_id} resolved ({dec.get('status')}):[/bold green] {dec.get('answer')}"
        )
    else:
        console.print(
            f"[bold yellow]⏳ Decision {dec_id} waiting ({dec.get('status')}):[/bold yellow] "
            f"U={dec.get('unblock_weight')} | || {dec.get('unblock_badge')} unblocked"
        )


@decision_cmd.command("list")
@click.option("--status", default=None, help="Filter by decision status.")
@click.option("--category", default=None, help="Filter by wedge category.")
@click.option("--archived", is_flag=True, default=False, help="Include resolved and event-settled decisions.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_list(
    status: Optional[str],
    category: Optional[str],
    archived: bool,
    as_json: bool,
) -> None:
    """List decisions ranked descending by transitive downstream work unblocked."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.list_decisions(status_filter=status, category_filter=category, include_archived=archived)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return

    summary = res["summary"]
    console.print(
        f"[bold cyan]Open:[/bold cyan] {summary['open_count']}  "
        f"[bold green]Answered:[/bold green] {summary['resolved_by_human_count']}  "
        f"[bold magenta]Settled by Event:[/bold magenta] {summary['settled_by_event_count']}  "
        f"[bold yellow]Total Unblock Weight:[/bold yellow] {summary['total_unblock_weight']}"
    )
    table = Table(title="Decision Queue Ranked by Unblock Impact U(d)")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Tier", style="bold red", no_wrap=True)
    table.add_column("Unblocks", justify="right", style="bold yellow")
    table.add_column("Agent", style="bold white")
    table.add_column("Wedge Category", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Question / Fact Predicate", style="white")

    for item in res["decisions"]:
        fact_suffix = f" [WAIT: {item['fact_predicate']}]" if item.get("fact_predicate") else ""
        table.add_row(
            str(item.get("decision_id")),
            str(item.get("priority_tier")),
            f"|| {item.get('unblock_badge')} (U={item.get('unblock_weight')})",
            str(item.get("agent_id")),
            str(item.get("category_label", item.get("category"))),
            str(item.get("status")),
            f"{item.get('question')}{fact_suffix}",
        )
    console.print(table)


@decision_cmd.command("answer")
@click.argument("decision_id")
@click.option("--response", "-r", default="Approved", show_default=True, help="Operator answer or directive.")
@click.option("--operator", default=None, help="Operator identity.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_answer(
    decision_id: str,
    response: str,
    operator: Optional[str],
    as_json: bool,
) -> None:
    """Answer an open decision, sign boundary gates, and compound to MemoryGraph."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.answer_decision(decision_id=decision_id, answer=response, operator=operator)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        if not res.get("success"):
            raise click.exceptions.Exit(1)
        return
    if not res.get("success"):
        console.print(f"[bold red]✗ {res.get('error')}[/bold red]")
        raise click.exceptions.Exit(1)
    dec = res["decision"]
    console.print(
        f"[bold green]✓ Answered {dec['decision_id']}:[/bold green] '{dec['answer']}' "
        f"(unblocked: {', '.join(dec.get('unblocks', [])) or 'none'})"
    )


@decision_cmd.command("reject")
@click.argument("decision_id")
@click.option("--reason", "-r", default="Rejected by operator", show_default=True, help="Rejection reason.")
@click.option("--operator", default=None, help="Operator identity.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_reject(
    decision_id: str,
    reason: str,
    operator: Optional[str],
    as_json: bool,
) -> None:
    """Reject a waiting decision or boundary gate."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.reject_decision(decision_id=decision_id, reason=reason, operator=operator)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        if not res.get("success"):
            raise click.exceptions.Exit(1)
        return
    if not res.get("success"):
        console.print(f"[bold red]✗ {res.get('error')}[/bold red]")
        raise click.exceptions.Exit(1)
    console.print(f"[bold yellow]✓ Rejected {decision_id}:[/bold yellow] {reason}")


@decision_cmd.command("snooze")
@click.argument("decision_id")
@click.option("--fact", "-f", "fact_predicate", required=True, help="Fact predicate this question waits for.")
@click.option("--operator", default=None, help="Operator identity.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_snooze(
    decision_id: str,
    fact_predicate: str,
    operator: Optional[str],
    as_json: bool,
) -> None:
    """Bind a waiting question to a declarative fact predicate instead of a timer."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.snooze_on_fact(decision_id=decision_id, fact_predicate=fact_predicate, operator=operator)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        if not res.get("success"):
            raise click.exceptions.Exit(1)
        return
    if not res.get("success"):
        console.print(f"[bold red]✗ {res.get('error')}[/bold red]")
        raise click.exceptions.Exit(1)
    console.print(
        f"[bold cyan]✓ Decision {decision_id} now waits on fact:[/bold cyan] [bold white]{fact_predicate}[/bold white]"
    )


@decision_cmd.command("assert-fact")
@click.argument("fact_predicate")
@click.option("--reason", "-r", default="Fact verified by event bus", show_default=True, help="Settlement reason.")
@click.option("--source", default="cli", show_default=True, help="Event source identifier.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_assert_fact(
    fact_predicate: str,
    reason: str,
    source: str,
    as_json: bool,
) -> None:
    """Assert that a fact is true and automatically settle waiting questions."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.assert_fact(fact_predicate=fact_predicate, reason=reason, source=source, auto_settle=True)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    console.print(
        f"[bold green]✓ Fact asserted:[/bold green] {fact_predicate} "
        f"(auto-settled {res['settled_count']} waiting decision(s))"
    )


@decision_cmd.command("settle")
@click.option("--live-probes", is_flag=True, default=False, help="Enable live git/gh subprocess probes.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_settle(live_probes: bool, as_json: bool) -> None:
    """Evaluate all pending fact predicates and auto-settle satisfied questions."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.evaluate_and_settle_facts(live_probes=live_probes)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    console.print(
        f"[bold green]✓ Fact Settlement complete:[/bold green] "
        f"{res['settled_count']} settled by event, {res['remaining_open']} remaining open."
    )


@decision_cmd.command("approve-in")
@click.argument("agent_id")
@click.option("--intent", "-i", default="Execute scoped agent work", show_default=True, help="Work intent summary.")
@click.option("--budget", default=50000, type=int, show_default=True, help="Token budget cap.")
@click.option("--tools", default="read_file,edit_file,run_command", show_default=True, help="Permitted tools CSV.")
@click.option("--unblocks", "-u", default="", help="Downstream tasks unblocked.")
@click.option("--queue-only", is_flag=True, default=False, help="Queue input gate without immediate approval.")
@click.option(_SPLIT_WINDOW_FLAG, default=True, show_default=True, help=_SPLIT_WINDOW_HELP)
@click.option(_SPLIT_SIDE_OPT, default="right", show_default=True, help=_SPLIT_SIDE_HELP)
@click.option("--operator", default=None, help="Operator identity.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_approve_in(
    agent_id: str,
    intent: str,
    budget: int,
    tools: str,
    unblocks: str,
    queue_only: bool,
    split_window: bool,
    split_side: str,
    operator: Optional[str],
    as_json: bool,
) -> None:
    """Input Work Boundary Gate ('approve what goes into the work')."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    gate_req = bot.create_input_gate(
        agent_id=agent_id,
        intent=intent,
        token_budget=budget,
        tools=_split_csv(tools),
        unblocks=_split_csv(unblocks) or None,
        split_window=queue_only and split_window,
        split_side=split_side,
    )
    dec_id = str(gate_req["decision"]["decision_id"])
    res = (
        gate_req
        if queue_only
        else bot.answer_decision(decision_id=dec_id, answer="Approve Input Gate", operator=operator)
    )
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    dec = res["decision"]
    sig = (dec.get("boundary_payload") or {}).get("hmac_signature") or "pending"
    console.print(
        f"[bold green]✓ Input Boundary Gate ({dec['status']}):[/bold green] {dec_id} for {agent_id} "
        f"[dim](HMAC={str(sig)[:16]})[/dim]"
    )


@decision_cmd.command("approve-out")
@click.argument("agent_id")
@click.option("--summary", "-s", default="Deliverable artifact & diff ready", show_default=True, help="Delivery summary.")
@click.option("--diff", "diff_summary", default="", help="Unified diff summary.")
@click.option("--pr-draft", default="", help="PR title/body draft.")
@click.option("--unblocks", "-u", default="", help="Downstream release tasks unblocked.")
@click.option("--queue-only", is_flag=True, default=False, help="Queue output gate without immediate signoff.")
@click.option(_SPLIT_WINDOW_FLAG, default=True, show_default=True, help=_SPLIT_WINDOW_HELP)
@click.option(_SPLIT_SIDE_OPT, default="right", show_default=True, help=_SPLIT_SIDE_HELP)
@click.option("--operator", default=None, help="Operator identity.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_approve_out(
    agent_id: str,
    summary: str,
    diff_summary: str,
    pr_draft: str,
    unblocks: str,
    queue_only: bool,
    split_window: bool,
    split_side: str,
    operator: Optional[str],
    as_json: bool,
) -> None:
    """Output Work Boundary Gate ('approve what comes out of the work')."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    gate_req = bot.create_output_gate(
        agent_id=agent_id,
        summary=summary,
        diff_summary=diff_summary,
        pr_draft=pr_draft,
        unblocks=_split_csv(unblocks) or None,
        split_window=queue_only and split_window,
        split_side=split_side,
    )
    dec_id = str(gate_req["decision"]["decision_id"])
    res = (
        gate_req
        if queue_only
        else bot.answer_decision(decision_id=dec_id, answer="Accept & Sign Off", operator=operator)
    )
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return
    dec = res["decision"]
    sig = (dec.get("boundary_payload") or {}).get("hmac_signature") or "pending"
    console.print(
        f"[bold green]✓ Output Boundary Gate ({dec['status']}):[/bold green] {dec_id} for {agent_id} "
        f"[dim](HMAC={str(sig)[:16]})[/dim]"
    )


@decision_cmd.command("dep")
@click.option("--from", "upstream_task", required=True, help="Upstream task ID.")
@click.option("--to", "downstream_task", required=True, help="Downstream dependent task ID.")
@click.option("--weight", default=1.0, type=float, show_default=True, help="Task weight.")
@click.option("--criticality", default=1.0, type=float, show_default=True, help="Task criticality.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit machine-readable JSON.")
def decision_dep(
    upstream_task: str,
    downstream_task: str,
    weight: float,
    criticality: float,
    as_json: bool,
) -> None:
    """Register a task-to-task dependency edge in the Decision Graph DAG."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    res = bot.add_task_dependency(upstream_task, downstream_task, weight=weight, criticality=criticality)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        if not res.get("success"):
            raise click.exceptions.Exit(1)
        return
    if not res.get("success"):
        console.print(f"[bold red]✗ {res.get('error')}[/bold red]")
        raise click.exceptions.Exit(1)
    console.print(f"[bold green]✓ Added DAG dependency:[/bold green] {upstream_task} -> {downstream_task}")


@decision_cmd.command("tui")
@click.option("--operator", default="Mark", show_default=True, help="Operator display name.")
@click.option("--seed-demo", is_flag=True, default=False, help="Seed canonical Cruise Control reference topology.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit radar snapshot as JSON.")
def decision_tui(operator: str, seed_demo: bool, as_json: bool) -> None:
    """Render the Cruise Control Decision Radar in Rich Terminal TUI format."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    snapshot = bot.seed_demo_radar() if seed_demo else bot.get_radar_snapshot(operator_name=operator)
    if as_json:
        click.echo(json.dumps(snapshot, indent=2))
        return
    render_radar_tui(snapshot, console=console)


@decision_cmd.command("radar")
@click.option("--host", "-h", default="127.0.0.1", show_default=True, help="Host interface to bind HTTP server.")
@click.option("--port", "-p", default=DEFAULT_CRUISE_PORT, type=int, show_default=True, help="Port to bind HTTP server.")
@click.option("--operator", default="Mark", show_default=True, help="Operator identity in center hub.")
@click.option("--seed-demo", is_flag=True, default=False, help="Seed canonical Cruise Control reference topology.")
@click.option(_SPLIT_WINDOW_FLAG, default=True, show_default=True, help=_SPLIT_WINDOW_HELP)
@click.option(_SPLIT_SIDE_OPT, default="right", show_default=True, help=_SPLIT_SIDE_HELP)
@click.option("--daemon", "-d", is_flag=True, default=False, help="Run server in background daemon thread.")
@click.option("--no-serve", is_flag=True, default=False, help="Compute radar snapshot without blocking on HTTP server.")
@click.option("--json", "as_json", is_flag=True, default=False, help="Emit radar snapshot as JSON.")
def decision_radar(
    host: str,
    port: int,
    operator: str,
    seed_demo: bool,
    split_window: bool,
    split_side: str,
    daemon: bool,
    no_serve: bool,
    as_json: bool,
) -> None:
    """Launch the interactive Cruise Control Radial Sunburst Web Radar & SSE Server."""
    bot = DecisionRadarBot(cwd=Path.cwd())
    snapshot = bot.seed_demo_radar() if seed_demo else bot.get_radar_snapshot(operator_name=operator)

    if as_json or no_serve:
        if as_json:
            click.echo(json.dumps(snapshot, indent=2))
        else:
            render_radar_tui(snapshot, console=console)
        return

    server = HathorDecisionRadarServer(host=host, port=port, cwd=Path.cwd(), operator_name=operator)
    bound_port = server.start(daemon=True)
    radar_url = build_local_radar_url(port=bound_port, host=host)
    console.print(f"[bold green]Starting HATH0R Cruise Control[/bold green] at [cyan]{radar_url}[/cyan]")
    console.print("[dim]Serving Cruise Control Radial Sunburst UX, Unblock Reranker, and SSE stream.[/dim]")

    if split_window:
        top_decisions = snapshot.get("decisions") or []
        focus_id = str(top_decisions[0]["decision_id"]) if top_decisions else None
        win = launch_cruise_control_split_window(url=radar_url, decision_id=focus_id, side=split_side)
        console.print(
            f"[bold blue]◫ Split-window Cruise Control ({win.get('layout')}):[/bold blue] [cyan]{win.get('url')}[/cyan]"
        )

    if daemon:
        console.print("[green]Decision Radar server running in background daemon thread.[/green]")
        return

    console.print("[dim]Press Ctrl+C to stop radar server.[/dim]")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping Decision Radar server...[/yellow]")
        server.stop()
        console.print("[green]Radar server stopped.[/green]")
