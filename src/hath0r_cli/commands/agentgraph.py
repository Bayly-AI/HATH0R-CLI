"""AgentGraph command group for HATH0R CLI."""

from __future__ import annotations

from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.bots.agentgraph_bot import AgentGraphBot
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def agentgraph() -> None:
    """Unified AgentGraph cognitive substrate, policy governance, and tool RBAC control plane."""
    pass


@agentgraph.command("status")
@click.option("--path", "-p", default=".", help="Repository root path.")
@click.pass_context
def agentgraph_status(ctx: click.Context, path: str) -> None:
    """Inspect active Knowledge, Context, Memory, and Rules node/edge statistics."""
    bot = AgentGraphBot()
    res = bot.get_status(path=path)

    response = _build_response(
        ctx,
        command="agentgraph.status",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        stat = res["status"]
        console.print(f"\n[bold cyan]AgentGraph Topology Status[/bold cyan] (Graph ID: [green]{res['graph_id']}[/green])")
        if res.get("snapshot_path"):
            console.print(f"  [dim]Snapshot: {res['snapshot_path']}[/dim]\n")
        else:
            console.print("  [dim yellow]No saved snapshot file found on disk. Run 'hath0r agentgraph sync' to initialize.[/dim yellow]\n")

        # Planes Table
        p_table = Table(title="Cognitive Planes Breakdown", show_header=True, header_style="bold magenta")
        p_table.add_column("Plane", style="cyan")
        p_table.add_column("Total Nodes", justify="right")
        p_table.add_column("Active Nodes", justify="right")

        planes = stat.get("planes", {})
        if planes:
            for plane, count in sorted(planes.items()):
                p_table.add_row(plane.capitalize(), str(count), str(count))
        else:
            p_table.add_row("None (empty)", "0", "0")
        console.print(p_table)

        # Edges Table
        e_table = Table(title="Relational Edges Summary", show_header=True, header_style="bold blue")
        e_table.add_column("Relation / Edge Type", style="yellow")
        e_table.add_column("Count", justify="right")

        edges = stat.get("edge_types", {})
        if edges:
            for etype, count in sorted(edges.items()):
                e_table.add_row(etype, str(count))
        else:
            e_table.add_row("None (empty)", "0")
        console.print(e_table)

        console.print(
            f"[bold]Total Entities:[/bold] {stat['total_nodes']} nodes | "
            f"[bold]Total Relations:[/bold] {stat['total_edges']} edges\n"
        )

    _emit_response(ctx, response, text_renderer=_text)


@agentgraph.command("query")
@click.argument("query_str")
@click.option("--top-k", "-k", default=5, type=int, help="Maximum number of results to return.")
@click.option(
    "--plane",
    type=click.Choice(["rules", "knowledge", "context", "memory", "extensible"], case_sensitive=False),
    default=None,
    help="Filter search to specific graph plane.",
)
@click.option("--all", "include_inactive", is_flag=True, default=False, help="Include bitemporally inactive/deprecated nodes.")
@click.option("--path", "-p", default=".", help="Repository root path.")
@click.pass_context
def agentgraph_query(
    ctx: click.Context,
    query_str: str,
    top_k: int,
    plane: Optional[str],
    include_inactive: bool,
    path: str,
) -> None:
    """Execute hybrid search across the unified AgentGraph planes."""
    bot = AgentGraphBot()
    res = bot.query(
        query_str=query_str,
        top_k=top_k,
        plane=plane,
        active_only=not include_inactive,
        path=path,
    )

    response = _build_response(
        ctx,
        command="agentgraph.query",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        qdata = res["query"]
        results = qdata["results"]
        console.print(f"\n[bold cyan]AgentGraph Search Results[/bold cyan] for '[bold yellow]{query_str}[/bold yellow]':")

        if not results:
            console.print("  [dim yellow]No matching nodes found across graph planes.[/dim yellow]\n")
            return

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Rank", justify="right", style="dim", width=5)
        table.add_column("Score", justify="right", style="cyan", width=8)
        table.add_column("Plane", style="magenta", width=12)
        table.add_column("Type", style="yellow", width=14)
        table.add_column("ID / Label", style="bold")
        table.add_column("Snippet", style="dim")

        for idx, item in enumerate(results, start=1):
            table.add_row(
                str(idx),
                str(item["score"]),
                item["plane"],
                item["type"],
                f"{item['label']} ({item['id']})",
                item["snippet"].replace("\n", " ")[:60],
            )
        console.print(table)
        console.print(f"  [dim]Showing top {len(results)} of {qdata['results_count']} results.[/dim]\n")

    _emit_response(ctx, response, text_renderer=_text)


@agentgraph.command("validate")
@click.option("--path", "-p", default=".", help="Repository root path.")
@click.option("--strict", is_flag=True, default=False, help="Fail if any warnings or unlinked references exist.")
@click.pass_context
def agentgraph_validate(ctx: click.Context, path: str, strict: bool) -> None:
    """Perform deterministic rule constraint, cycle, and contradiction validation."""
    bot = AgentGraphBot()
    res = bot.validate(path=path, strict=strict)
    is_valid = res["validation"]["valid"]

    response = _build_response(
        ctx,
        command="agentgraph.validate",
        state="ok" if is_valid else "error",
        data=res,
    )

    def _text() -> None:
        v = res["validation"]
        if is_valid:
            console.print(
                f"\n[bold green]✓ AgentGraph Validation PASSED[/bold green] "
                f"({v['nodes_validated']} nodes, {v['edges_validated']} edges checked)"
            )
            console.print("  • Zero cyclic dependencies detected.")
            console.print("  • Zero role/rule contradictions found.")
            if v.get("warnings"):
                console.print(f"  [yellow]• {len(v['warnings'])} warnings reported:[/yellow]")
                for w in v["warnings"]:
                    console.print(f"    - {w}")
            console.print("")
        else:
            console.print(
                f"\n[bold red]✗ AgentGraph Validation FAILED[/bold red] "
                f"({len(v['errors'])} errors detected)"
            )
            for err in v["errors"]:
                console.print(f"  [red]• {err}[/red]")
            console.print("")

    _emit_response(ctx, response, text_renderer=_text)


@agentgraph.command("sync")
@click.option("--path", "-p", default=".", help="Repository root path.")
@click.option("--persist/--no-persist", default=True, help="Persist snapshot to .hath0r/agentgraph/snapshot.json.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate sync without writing files.")
@click.pass_context
def agentgraph_sync(ctx: click.Context, path: str, persist: bool, dry_run: bool) -> None:
    """Ingest local repository rules, docs, and contracts into the AgentGraph."""
    bot = AgentGraphBot()
    res = bot.sync(path=path, persist=persist, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="agentgraph.sync",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        s = res["sync"]
        mode = "[yellow](DRY-RUN)[/yellow] " if dry_run else ""
        console.print(f"\n[bold green]✓ {mode}AgentGraph Sync Completed[/bold green]")
        console.print(f"  • Scanned sources: [bold]{s['sources_scanned']}[/bold]")
        console.print(f"  • Indexed nodes: [bold]{s['nodes_indexed']}[/bold]")
        console.print(f"  • Ingested relational edges: [bold]{s['edges_indexed']}[/bold]")
        if res.get("snapshot_file"):
            console.print(f"  • Snapshot saved: [cyan]{res['snapshot_file']}[/cyan]")
        console.print("")

    _emit_response(ctx, response, text_renderer=_text)


@agentgraph.command("route")
@click.option("--role", "-r", required=True, help="Agent role identifier (e.g. 'role:developer' or 'developer').")
@click.option("--task", "-t", default=None, help="Optional task description.")
@click.option("--tool", default=None, help="Check authorization for a specific tool name.")
@click.option("--path", "-p", default=".", help="Repository root path.")
@click.pass_context
def agentgraph_route(
    ctx: click.Context,
    role: str,
    task: Optional[str],
    tool: Optional[str],
    path: str,
) -> None:
    """Resolve active rule constraints, tool authorization, and RBAC for an agent role."""
    bot = AgentGraphBot()
    res = bot.route(role=role, task=task, tool=tool, path=path)

    response = _build_response(
        ctx,
        command="agentgraph.route",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        r = res["routing"]
        role_label = r["role"]
        found = r.get("role_found", False)

        status_text = "[green]Active[/green]" if found else "[yellow]Synthesized / Default[/yellow]"
        console.print(f"\n[bold cyan]AgentGraph Role RBAC Routing[/bold cyan] for [bold yellow]{role_label}[/bold yellow] ({status_text}):")

        if r.get("inherited_roles"):
            console.print(f"  [dim]Inherits From:[/dim] {', '.join(r['inherited_roles'])}")

        # Authorized Tools Panel
        auth_tools = r.get("authorized_tools", [])
        auth_str = ", ".join(auth_tools) if auth_tools else "[dim]None[/dim]"
        console.print(Panel(auth_str, title="[bold green]Authorized Tools[/bold green]", expand=False))

        # Forbidden Tools & Restrictions
        forbid_tools = r.get("forbidden_tools", [])
        if forbid_tools:
            console.print(f"  [red]Forbidden Tools:[/red] {', '.join(forbid_tools)}")

        rest_acts = r.get("restricted_actions", [])
        if rest_acts:
            console.print(f"  [red]Restricted Actions:[/red] {', '.join(rest_acts)}")

        # Specific tool check
        if tool:
            is_auth = r.get("tool_authorized")
            if is_auth:
                console.print(f"\n  [bold green]✓ Tool '{tool}' is AUTHORIZED for role '{role_label}'.[/bold green]")
            else:
                console.print(f"\n  [bold red]✗ Tool '{tool}' is NOT AUTHORIZED for role '{role_label}'.[/bold red]")
        console.print("")

    _emit_response(ctx, response, text_renderer=_text)


@agentgraph.command("bot")
@click.option("--run", is_flag=True, default=False, help="Run autonomous sync and healing loop.")
@click.option("--audit", is_flag=True, default=False, help="Execute health and policy audit.")
@click.option("--path", "-p", default=".", help="Repository root path.")
@click.pass_context
def agentgraph_bot_cmd(ctx: click.Context, run: bool, audit: bool, path: str) -> None:
    """AgentGraph-bot autonomous management and audit surface."""
    bot = AgentGraphBot()
    if run:
        # Run sync followed by audit
        sync_res = bot.sync(path=path)
        audit_res = bot.run_bot_audit(path=path)
        data = {"action": "run", "sync": sync_res["sync"], "audit": audit_res}
    else:
        # Default to audit
        data = bot.run_bot_audit(path=path)

    response = _build_response(
        ctx,
        command="agentgraph.bot",
        state="ok" if data.get("success", True) else "error",
        data=data,
    )

    def _text() -> None:
        console.print(f"\n[bold cyan]AgentGraph-bot Report[/bold cyan] (Health: [bold green]{data.get('health', 'ok')}[/bold green])")
        if "sync" in data:
            console.print(f"  • Sync: Indexed {data['sync']['nodes_indexed']} nodes, {data['sync']['edges_indexed']} edges.")
        console.print(f"  • Valid: {data.get('validation', {}).get('valid', True)}")
        console.print("")

    _emit_response(ctx, response, text_renderer=_text)
