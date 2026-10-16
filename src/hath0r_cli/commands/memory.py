"""Memory command for HATH0R CLI."""

from __future__ import annotations

import click
from rich.markdown import Markdown
from rich.table import Table
from rich.tree import Tree

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)

NODE_TYPES = ["rule", "concept", "decision", "fact", "topic", "episode", "insight", "session"]
RELATION_TYPES = ["ENFORCES", "REQUIRES", "DERIVES_FROM", "SUPERSEDES", "RELATES_TO", "RESOLVES", "PRECEDES"]


@click.group()
def memory() -> None:
    """Manage canonical Local Memory Space and semantic memory graphs for agents."""
    pass


@memory.command("init")
@click.option("--dry-run", is_flag=True, help="Simulate initialization.")
@click.pass_context
def memory_init(ctx: click.Context, dry_run: bool) -> None:
    """Initialize the core local memory spaces and memory graph."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.initialize_memory(dry_run=dry_run)

    response = _build_response(
        ctx,
        command="memory.init",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[green]✓ {res['message']}[/green]")
            for f in res.get("files", []):
                console.print(f"  • {f}")
        else:
            console.print(f"[red]✗ {res.get('error')}[/red]")

    _emit_response(ctx, response, text_renderer=_text)


@memory.command("read")
@click.argument("topic", default="core")
@click.pass_context
def memory_read(ctx: click.Context, topic: str) -> None:
    """Read a canonical memory topic."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.read_memory(topic=topic)

    response = _build_response(
        ctx,
        command="memory.read",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(Markdown(res["content"]))
        else:
            console.print(f"[red]✗ {res.get('error')}[/red]")

    _emit_response(ctx, response, text_renderer=_text)


@memory.command("update")
@click.argument("topic")
@click.argument("content")
@click.option("--dry-run", is_flag=True, help="Simulate update.")
@click.pass_context
def memory_update(ctx: click.Context, topic: str, content: str, dry_run: bool) -> None:
    """Update a canonical memory topic."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.update_memory(topic=topic, content=content, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="memory.update",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[green]✓ {res['message']}[/green]")
        else:
            console.print(f"[red]✗ {res.get('error')}[/red]")

    _emit_response(ctx, response, text_renderer=_text)


@memory.command("compound")
@click.option("--id", "node_id", default=None, help="Explicit node ID (e.g. episode:issue-287-fix).")
@click.option(
    "--type",
    "-t",
    "node_type",
    type=click.Choice(NODE_TYPES, case_sensitive=False),
    default="episode",
    help="Memory node type.",
)
@click.option("--label", "-l", required=True, help="Short descriptive title for the memory node.")
@click.option("--content", "-c", required=True, help="Detailed knowledge, decision, or episode summary.")
@click.option("--importance", "-i", default=0.8, type=float, help="Importance weight in [0.0, 1.0].")
@click.option("--tags", default="", help="Comma-separated list of semantic tags.")
@click.option("--relates-to", default="", help="Comma-separated target node IDs to link to.")
@click.option(
    "--relation",
    "-r",
    type=click.Choice(RELATION_TYPES, case_sensitive=False),
    default="DERIVES_FROM",
    help="Relational edge type.",
)
@click.option("--supersedes", default=None, help="Existing node ID bitemporally superseded by this node.")
@click.option("--no-sync", is_flag=True, help="Skip immediate AgentGraph synchronization.")
@click.option("--dry-run", is_flag=True, help="Simulate compounding without writing to disk.")
@click.pass_context
def memory_compound(
    ctx: click.Context,
    node_id: str | None,
    node_type: str,
    label: str,
    content: str,
    importance: float,
    tags: str,
    relates_to: str,
    relation: str,
    supersedes: str | None,
    no_sync: bool,
    dry_run: bool,
) -> None:
    """Compound structured task knowledge into .hath0r/memory/graph.json prior to announcing complete."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    target_list = [t.strip() for t in relates_to.split(",") if t.strip()] if relates_to else []

    bot = MemoryManagerBot()
    res = bot.compound_memory(
        label=label,
        content=content,
        node_type=node_type,
        node_id=node_id,
        importance=importance,
        tags=tag_list,
        relates_to=target_list,
        relation=relation,
        supersedes=supersedes,
        sync_agentgraph=not no_sync,
        dry_run=dry_run,
    )

    response = _build_response(
        ctx,
        command="memory.compound",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        if res.get("success"):
            node = res.get("node", {})
            console.print(f"[green]✓ {res.get('message')}[/green]")
            console.print(f"  • Node ID: [bold cyan]{node.get('id')}[/bold cyan] ({node.get('type')})")
            console.print(f"  • Edges Added: {len(res.get('edges_added', []))}")
            insights = res.get("reflection", {}).get("insights_generated", 0)
            console.print(f"  • Synthesized Insights: {insights}")
            console.print(f"  • AgentGraph Synced: {res.get('agentgraph_synced')}")
        else:
            console.print(f"[red]✗ {res.get('error')}[/red]")

    _emit_response(ctx, response, text_renderer=_text)


@memory.command("reflect")
@click.option("--threshold", default=2, type=int, help="Minimum cluster size to synthesize an insight.")
@click.option("--max-insights", default=5, type=int, help="Maximum insights to generate per pass.")
@click.option("--dry-run", is_flag=True, help="Simulate reflection synthesis.")
@click.pass_context
def memory_reflect(ctx: click.Context, threshold: int, max_insights: int, dry_run: bool) -> None:
    """Run sleep-cycle reflection consolidation across MemoryGraph clusters."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.reflect_memory(cluster_threshold=threshold, max_insights=max_insights, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="memory.reflect",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        count = res.get("insights_generated", 0)
        console.print(f"[green]✓ Memory Reflection Complete: {count} new insight(s) synthesized.[/green]")
        for ins in res.get("insights", []):
            console.print(f"  • [bold magenta]{ins.get('id')}[/bold magenta]: {ins.get('label')}")

    _emit_response(ctx, response, text_renderer=_text)


@memory.command("verify")
@click.option("--since", default=None, help="Verify knowledge compounded at or after ISO timestamp.")
@click.option("--task", "task_id", default=None, help="Verify knowledge compounded for a specific task/issue.")
@click.option("--no-session", is_flag=True, help="Skip micro memory session read/write check.")
@click.pass_context
def memory_verify(ctx: click.Context, since: str | None, task_id: str | None, no_session: bool) -> None:
    """Verify CR-MEMORY-COMPOUND-001 pre-announcement gate on .hath0r/memory/graph.json and micro session."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.verify_compounded(since=since, task_id=task_id, require_session=not no_session)
    ok = bool(res.get("compounded"))

    response = _build_response(
        ctx,
        command="memory.verify",
        state="ok" if ok else "error",
        data=res,
    )

    def _text() -> None:
        if ok:
            latest = res.get("latest_node") or {}
            sess = res.get("session") or {}
            console.print("[bold green]✓ MemoryGraph & Micro Session Pre-Announcement Gate PASSED (CR-MEMORY-COMPOUND-001)[/bold green]")
            console.print(
                f"  • Total Nodes: {res.get('total_nodes')} | Compounded Nodes: {res.get('compounded_nodes_count')} | Edges: {res.get('total_edges')}"
            )
            console.print(
                f"  • Micro Session: [cyan]{sess.get('session_id')}[/cyan] "
                f"(reads={sess.get('read_count', 0)}, writes={sess.get('write_count', 0)}, {sess.get('byte_size', 0)}B / 2048B)"
            )
            console.print(f"  • Latest Compounded Node: [cyan]{latest.get('id')}[/cyan] — {latest.get('label')}")
        else:
            console.print(f"[bold red]✗ {res.get('error')}[/bold red]")

    _emit_response(ctx, response, text_renderer=_text)
    if not ok:
        ctx.exit(1)


@memory.command("ensure-all")
@click.option("--root", "root_dir", default=None, help="Workspace root directory to scan for repositories.")
@click.option("--no-sync", is_flag=True, help="Skip AgentGraph synchronization across repositories.")
@click.option("--dry-run", is_flag=True, help="Simulate provisioning without writing to disk.")
@click.pass_context
def memory_ensure_all(ctx: click.Context, root_dir: str | None, no_sync: bool, dry_run: bool) -> None:
    """Provision and verify .hath0r/memory/graph.json and micro sessions across all active repositories."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.ensure_all_repos(root_dir=root_dir, sync_agentgraph=not no_sync, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="memory.ensure_all",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        table = Table(title=f"MemoryGraph & Micro Session Provisioning Across {res.get('repos_count', 0)} Repositories")
        table.add_column("Repository", style="bold")
        table.add_column("Compounded", justify="center")
        table.add_column("Session R/W", justify="center")
        table.add_column("Nodes", justify="right")
        table.add_column("Edges", justify="right")
        table.add_column("AgentGraph Synced", justify="center")

        for r in res.get("repos", []):
            comp = "[green]✓[/green]" if r.get("compounded") else "[red]✗[/red]"
            rw_ok = r.get("session_read_verified") and r.get("session_write_verified")
            rw_str = "[green]✓[/green]" if rw_ok else "[red]✗[/red]"
            ag = "[green]✓[/green]" if r.get("agentgraph_synced") else "[yellow]-[/yellow]"
            table.add_row(
                str(r.get("repo")),
                comp,
                rw_str,
                str(r.get("total_nodes", 0)),
                str(r.get("total_edges", 0)),
                ag,
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@memory.command("search")
@click.argument("query", default="")
@click.option(
    "--type",
    "-t",
    "node_type",
    type=click.Choice(NODE_TYPES, case_sensitive=False),
    default=None,
    help="Filter by memory node type.",
)
@click.option("--tag", default=None, help="Filter by tag.")
@click.option(
    "--relation",
    "-r",
    type=click.Choice(RELATION_TYPES, case_sensitive=False),
    default=None,
    help="Filter edge relationship traversal.",
)
@click.option("--depth", "-d", default=1, type=int, help="Graph neighborhood traversal depth.")
@click.pass_context
def memory_search(
    ctx: click.Context,
    query: str,
    node_type: str | None,
    tag: str | None,
    relation: str | None,
    depth: int,
) -> None:
    """Search and traverse the semantic working memory graph."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.search_memory(
        query=query,
        node_type=node_type,
        tag=tag,
        depth=depth,
        relation=relation,
    )

    response = _build_response(
        ctx,
        command="memory.search",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        nodes = res.get("nodes", [])
        edges = res.get("edges", [])
        total = res.get("total_matches", 0)

        if not nodes:
            console.print(f"[yellow]No memory nodes found matching query '{query}'.[/yellow]")
            return

        table = Table(title=f"Memory Search Results (Matches: {total})")
        table.add_column("Node ID", style="bold")
        table.add_column("Type")
        table.add_column("Label")
        table.add_column("Importance")
        table.add_column("Tags")
        table.add_column("Preview")

        type_colors = {
            "rule": "red",
            "decision": "magenta",
            "concept": "cyan",
            "topic": "blue",
            "fact": "green",
            "episode": "yellow",
            "insight": "bright_magenta",
            "session": "bright_cyan",
        }

        for n in nodes:
            ntype = str(n.get("type", "unknown"))
            color = type_colors.get(ntype, "white")
            content = str(n.get("content", "")).replace("\n", " ").strip()
            preview = (content[:50] + "...") if len(content) > 50 else content
            tags = ", ".join(n.get("tags", []))
            imp = str(n.get("importance", ""))
            table.add_row(
                n.get("id", ""),
                f"[{color}]{ntype}[/{color}]",
                n.get("label", ""),
                imp,
                tags,
                preview,
            )
        console.print(table)

        if edges:
            tree = Tree("[bold]Traversed Semantic Relations[/bold]")
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                rel = e.get("relation", "")
                tree.add(f"[cyan]{src}[/cyan] ──([bold yellow]{rel}[/bold yellow])──▶ [green]{tgt}[/green]")
            console.print(tree)

    _emit_response(ctx, response, text_renderer=_text)


@memory.group("session")
def memory_session() -> None:
    """Manage true Micro Memory Sessions (.hath0r/memory/sessions/) read and written on every session."""
    pass


@memory_session.command("start")
@click.option("--focus", "-f", default=None, help="Initial focus or objective for this micro memory session.")
@click.option("--session-id", "--id", "-s", "session_id", default=None, help="Explicit session ID.")
@click.option("--task", "task_id", default=None, help="Optional task or issue identifier.")
@click.option("--role", default=None, help="Optional operator or agent role.")
@click.option("--new", "force_new", is_flag=True, help="Force creation of a new session linked to prior session.")
@click.option("--top-k", default=5, type=int, help="Number of top active MemoryGraph nodes to recall.")
@click.option("--dry-run", is_flag=True, help="Simulate session start without writing to disk.")
@click.pass_context
def memory_session_start(
    ctx: click.Context,
    focus: str | None,
    session_id: str | None,
    task_id: str | None,
    role: str | None,
    force_new: bool,
    top_k: int,
    dry_run: bool,
) -> None:
    """Start a new Micro Memory Session (.hath0r/memory/sessions/current.json) and recall top nodes."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.session_start(
        focus=focus,
        session_id=session_id,
        task_id=task_id,
        role=role,
        force_new=force_new,
        top_k=top_k,
        dry_run=dry_run,
    )

    response = _build_response(
        ctx,
        command="memory.session.start",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        sess = res.get("session", {})
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
        console.print(f"  • Session ID: [cyan]{sess.get('session_id')}[/cyan] (Prior: {sess.get('prior_session_id') or 'none'})")
        console.print(f"  • Focus: {sess.get('active_focus')}")
        console.print(f"  • Reads: {sess.get('read_count')} | Writes: {sess.get('write_count')} | Size: {res.get('byte_size')}B / 2048B")
        console.print(f"  • Recalled Nodes: {len(sess.get('recalled_nodes', []))}")

    _emit_response(ctx, response, text_renderer=_text)


@memory_session.command("read")
@click.option("--focus", "-f", default=None, help="Optional focus query to refresh recalled MemoryGraph nodes.")
@click.option("--note", "-n", default=None, help="Optional note for this session read.")
@click.option("--top-k", default=5, type=int, help="Number of top active MemoryGraph nodes to recall.")
@click.option("--dry-run", is_flag=True, help="Simulate session read without writing to disk.")
@click.pass_context
def memory_session_read(
    ctx: click.Context,
    focus: str | None,
    note: str | None,
    top_k: int,
    dry_run: bool,
) -> None:
    """Read the active Micro Memory Session capsule (<2KB), auto-starting if absent."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.session_read(focus=focus, note=note, top_k=top_k, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="memory.session.read",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        sess = res.get("session", {})
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
        console.print(f"  • Focus: [bold]{sess.get('active_focus')}[/bold]")
        if sess.get("prior_summary"):
            console.print(f"  • Prior Summary: {sess.get('prior_summary')}")
        recalled = sess.get("recalled_nodes", [])
        if recalled:
            console.print("  • Recalled MemoryGraph Nodes:")
            for rn in recalled:
                console.print(f"    - [cyan]{rn.get('id')}[/cyan] ({rn.get('type')}): {rn.get('label')}")
        entries = sess.get("micro_entries", [])
        if entries:
            console.print("  • Session Micro-Entries:")
            for me in entries:
                console.print(f"    - [{me.get('kind')}] {me.get('summary')}")

    _emit_response(ctx, response, text_renderer=_text)


@memory_session.command("write")
@click.argument("summary_arg", required=False, default=None)
@click.option("--summary", "-m", "summary_opt", default=None, help="Summary of the micro-memory observation or decision.")
@click.option(
    "--kind",
    "-k",
    type=click.Choice(
        ["observation", "decision", "finding", "action", "note", "tool", "hypothesis", "blocker", "milestone", "compound"],
        case_sensitive=False,
    ),
    default="observation",
    help="Kind of micro-memory entry.",
)
@click.option("--tag", "tags_tuple", multiple=True, help="Tag(s) to attach (can be specified multiple times).")
@click.option("--tags", default="", help="Comma-separated list of tags.")
@click.option("--focus", "-f", default=None, help="Update active session focus.")
@click.option("--next-step", "next_steps_tuple", multiple=True, help="Next step action item(s).")
@click.option("--node-id", default=None, help="Optional compounded MemoryGraph node ID to link.")
@click.option("--dry-run", is_flag=True, help="Simulate micro-session write without writing to disk.")
@click.pass_context
def memory_session_write(
    ctx: click.Context,
    summary_arg: str | None,
    summary_opt: str | None,
    kind: str,
    tags_tuple: tuple[str, ...],
    tags: str,
    focus: str | None,
    next_steps_tuple: tuple[str, ...],
    node_id: str | None,
    dry_run: bool,
) -> None:
    """Write a compact micro-memory entry into .hath0r/memory/sessions/current.json (<2KB)."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    resolved_summary = (summary_opt or summary_arg or "").strip()
    if not resolved_summary:
        raise click.UsageError("Provide a micro-memory summary via argument or --summary / -m.")

    tag_list = list(tags_tuple) + ([t.strip() for t in tags.split(",") if t.strip()] if tags else [])
    next_steps = list(next_steps_tuple) if next_steps_tuple else None

    bot = MemoryManagerBot()
    res = bot.session_write(
        summary=resolved_summary,
        kind=kind,
        tags=tag_list,
        focus=focus,
        next_steps=next_steps,
        node_id=node_id,
        dry_run=dry_run,
    )

    response = _build_response(
        ctx,
        command="memory.session.write",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@memory_session.command("end")
@click.option("--summary", "-m", default=None, help="Final milestone summary for the micro-session.")
@click.option("--next-step", "next_steps_tuple", multiple=True, help="Handoff next step(s) for the following session.")
@click.option("--no-sync", is_flag=True, help="Skip immediate AgentGraph synchronization.")
@click.option("--dry-run", is_flag=True, help="Simulate session flush without writing to disk.")
@click.pass_context
def memory_session_end(
    ctx: click.Context,
    summary: str | None,
    next_steps_tuple: tuple[str, ...],
    no_sync: bool,
    dry_run: bool,
) -> None:
    """Flush and finalize the active Micro Memory Session into .hath0r/memory/sessions/ and graph.json."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    next_steps = list(next_steps_tuple) if next_steps_tuple else None
    bot = MemoryManagerBot()
    res = bot.session_end(
        summary=summary,
        next_steps=next_steps,
        sync_agentgraph=not no_sync,
        dry_run=dry_run,
    )

    response = _build_response(
        ctx,
        command="memory.session.end",
        state="ok" if res.get("success") else "error",
        data=res,
        dry_run=dry_run,
    )

    def _text() -> None:
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@memory_session.command("status")
@click.pass_context
def memory_session_status(ctx: click.Context) -> None:
    """Check active Micro Memory Session read/write counts and <2KB budget status."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.session_status()
    ok = bool(res.get("read_verified") and res.get("write_verified"))

    response = _build_response(
        ctx,
        command="memory.session.status",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        color = "green" if ok else "yellow"
        console.print(f"[bold {color}]Micro Memory Session Status ({res.get('status')})[/bold {color}]")
        console.print(f"  • Session ID: [cyan]{res.get('session_id')}[/cyan] (Prior: {res.get('prior_session_id') or 'none'})")
        console.print(f"  • Read Count: {res.get('read_count')} (Verified: {res.get('read_verified')})")
        console.print(f"  • Write Count: {res.get('write_count')} (Verified: {res.get('write_verified')})")
        console.print(f"  • Capsule Size: {res.get('byte_size')}B / {res.get('max_bytes')}B (Within Budget: {res.get('within_budget')})")
        console.print(f"  • Active Focus: {res.get('active_focus')}")

    _emit_response(ctx, response, text_renderer=_text)

