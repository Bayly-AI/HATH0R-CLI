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


@memory.command("search")
@click.argument("query", default="")
@click.option(
    "--type",
    "-t",
    "node_type",
    type=click.Choice(["rule", "concept", "decision", "fact", "topic", "episode"], case_sensitive=False),
    default=None,
    help="Filter by memory node type.",
)
@click.option("--tag", default=None, help="Filter by tag.")
@click.option(
    "--relation",
    "-r",
    type=click.Choice(["ENFORCES", "REQUIRES", "DERIVES_FROM", "SUPERSEDES", "RELATES_TO", "RESOLVES", "PRECEDES"], case_sensitive=False),
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
