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

NODE_TYPES = ["rule", "concept", "decision", "fact", "topic", "episode", "insight"]
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
@click.pass_context
def memory_verify(ctx: click.Context, since: str | None, task_id: str | None) -> None:
    """Verify CR-MEMORY-COMPOUND-001 pre-announcement gate on .hath0r/memory/graph.json."""
    from hath0r_cli.bots.memory_manager import MemoryManagerBot

    bot = MemoryManagerBot()
    res = bot.verify_compounded(since=since, task_id=task_id)
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
            console.print("[bold green]✓ MemoryGraph Pre-Announcement Gate PASSED (CR-MEMORY-COMPOUND-001)[/bold green]")
            console.print(
                f"  • Total Nodes: {res.get('total_nodes')} | Compounded Nodes: {res.get('compounded_nodes_count')} | Edges: {res.get('total_edges')}"
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
    """Provision and verify .hath0r/memory/graph.json across all active repositories."""
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
        table = Table(title=f"MemoryGraph Provisioning Across {res.get('repos_count', 0)} Repositories")
        table.add_column("Repository", style="bold")
        table.add_column("Compounded", justify="center")
        table.add_column("Nodes", justify="right")
        table.add_column("Edges", justify="right")
        table.add_column("AgentGraph Synced", justify="center")

        for r in res.get("repos", []):
            comp = "[green]✓[/green]" if r.get("compounded") else "[red]✗[/red]"
            ag = "[green]✓[/green]" if r.get("agentgraph_synced") else "[yellow]-[/yellow]"
            table.add_row(
                str(r.get("repo")),
                comp,
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
