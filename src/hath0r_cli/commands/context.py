"""Context command for HATH0R CLI."""

from __future__ import annotations

import click
from rich.table import Table
from rich.tree import Tree

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def context() -> None:
    """Manage Hyper Context and ContextGraph runtime architecture."""
    pass


@context.command("spread")
@click.option("--target", required=True, help="Target directory for hyper context (e.g. src/hath0r_cli/bots)")
@click.option("--feature-name", required=True, help="Human-readable name of the feature (e.g. 'Bots Subsystem')")
@click.pass_context
def context_spread(ctx: click.Context, target: str, feature_name: str) -> None:
    """Spread localized AGENTS.md, rules.md, and canonical.md to a sub-folder."""
    from hath0r_cli.bots.hyper_context import HyperContextBot

    bot = HyperContextBot()
    res = bot.spread_context(target, feature_name)

    response = _build_response(
        ctx,
        command="context.spread",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ {res['message']}[/bold green]")
            for f in res.get("files_created", []):
                console.print(f"  • {f}")
        else:
            console.print(f"[bold red]✗ Failed to spread context:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@context.command("query")
@click.option(
    "--filter", "-f", "filter_query", default=None, help="Filter query substring for node id, label, or tool."
)
@click.option(
    "--type",
    "-t",
    "node_type",
    type=click.Choice(
        ["agent", "subagent", "task", "tool_invocation", "jev_guard", "context_slice", "artifact"], case_sensitive=False
    ),
    default=None,
    help="Filter by node type.",
)
@click.option("--session-id", "-s", default=None, help="Specific session ID to query.")
@click.option("--file", "file_path", default=None, help="Path to context JSON snapshot file.")
@click.option("--depth", "-d", default=1, type=int, help="Neighborhood traversal depth.")
@click.pass_context
def context_query(
    ctx: click.Context,
    filter_query: str | None,
    node_type: str | None,
    session_id: str | None,
    file_path: str | None,
    depth: int,
) -> None:
    """Query active ContextGraph runtime session state, subagent hierarchies, and JEV guards."""
    from hath0r_cli.bots.context_manager import ContextManagerBot

    bot = ContextManagerBot()
    res = bot.query_context(
        session_id=session_id,
        node_type=node_type,
        filter_query=filter_query,
        file_path=file_path,
        depth=depth,
    )

    response = _build_response(
        ctx,
        command="context.query",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if not res.get("success"):
            console.print(f"[bold red]✗ Query failed:[/bold red] {res.get('error')}")
            return

        nodes = res.get("nodes", [])
        edges = res.get("edges", [])
        summary = res.get("summary", {})

        if not nodes:
            console.print(f"[yellow]{res.get('message', 'No matching context nodes found.')}[/yellow]")
            return

        console.print(f"[bold cyan]Session ID:[/bold cyan] {res.get('session_id')}")
        if res.get("active_subagent_id"):
            console.print(f"[bold cyan]Active Subagent:[/bold cyan] {res.get('active_subagent_id')}")

        table = Table(title="Context Nodes")
        table.add_column("Node ID", style="bold")
        table.add_column("Type")
        table.add_column("Label")
        table.add_column("State")
        table.add_column("Details")

        type_colors = {
            "agent": "magenta",
            "subagent": "cyan",
            "task": "blue",
            "tool_invocation": "yellow",
            "jev_guard": "green",
            "artifact": "white",
        }

        for n in nodes:
            ntype = n.get("type", "unknown")
            color = type_colors.get(ntype, "white")
            props = n.get("properties", {})
            props_str = ", ".join(f"{k}={v}" for k, v in props.items()) if props else ""
            table.add_row(
                n.get("id", ""),
                f"[{color}]{ntype}[/{color}]",
                n.get("label", ""),
                n.get("state", ""),
                props_str,
            )
        console.print(table)

        if edges:
            tree = Tree("[bold]Execution & Relationship Edges[/bold]")
            for e in edges:
                src = e.get("source", "")
                tgt = e.get("target", "")
                rel = e.get("relation", "")
                tree.add(f"[cyan]{src}[/cyan] ──([bold yellow]{rel}[/bold yellow])──▶ [green]{tgt}[/green]")
            console.print(tree)

        console.print(
            f"Summary: [bold]{summary.get('total_nodes', 0)}[/bold] nodes "
            f"({summary.get('subagents', 0)} agents/subagents, "
            f"{summary.get('tool_invocations', 0)} tools, "
            f"{summary.get('jev_guards', 0)} JEV guards), "
            f"[bold]{len(edges)}[/bold] edges."
        )

    _emit_response(ctx, response, text_renderer=_text)


@context.command("compress")
@click.option("--query", "-q", required=True, help="Active user query or instruction string.")
@click.option("--context", "-c", "context_text", default=None, help="Inline context string to compress.")
@click.option(
    "--file", "-f", "file_path", default=None, type=click.Path(exists=True), help="Path to document file to compress."
)
@click.option("--threshold", "-t", default=0.5, type=float, help="Relevance score compression threshold (0.0 - 1.0).")
@click.option(
    "--local", "force_local", is_flag=True, default=False, help="Force local deterministic compression without network."
)
@click.pass_context
def context_compress(
    ctx: click.Context,
    query: str,
    context_text: str | None,
    file_path: str | None,
    threshold: float,
    force_local: bool,
) -> None:
    """Compress extensive prompt or RAG context against query using SuperCompress."""
    import sys
    from pathlib import Path

    from hath0r_cli.bots.supercompress_bot import SuperCompressBot

    target_text = context_text
    if file_path:
        target_text = Path(file_path).read_text(encoding="utf-8")
    elif not target_text:
        if not sys.stdin.isatty():
            target_text = sys.stdin.read()
        else:
            raise click.UsageError("Must provide --context, --file, or piped input via stdin.")

    bot = SuperCompressBot()
    res = bot.compress(
        query=query,
        context=target_text,
        threshold=threshold,
        force_local=force_local,
    )

    response = _build_response(
        ctx,
        command="context.compress",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        console.print(
            f"[bold green]✓ Context Compressed via {res.get('engine')}[/bold green] ({res.get('latency_ms', 0)}ms):"
        )
        console.print(f"  • Original Tokens: [bold]{res.get('original_tokens')}[/bold]")
        console.print(f"  • Compressed Tokens: [bold cyan]{res.get('compressed_tokens')}[/bold cyan]")
        console.print(f"  • Token Savings: [bold green]{res.get('savings_pct')}%[/bold green]")
        ver = res.get("verifier", {})
        if ver:
            console.print(
                f"  • Verifier: Quality={ver.get('quality_score')}, EntityRecall={ver.get('entity_recall')}, KeywordRecall={ver.get('keyword_recall')}"
            )
        console.print("\n[bold]Compressed Text Output:[/bold]")
        console.print(res.get("compressed_text", ""))

    _emit_response(ctx, response, text_renderer=_text)


@context.command("pack")
@click.option("--cag", is_flag=True, default=True, help="Pack full workspace context for Context-Augmented Generation.")
@click.option("--path", "-p", default=".", help="Workspace root path.")
@click.pass_context
def context_pack(ctx: click.Context, cag: bool, path: str) -> None:
    """Aggregate full workspace source files, AGENTS.md, and AgentGraph into a CAG context envelope."""
    from hath0r_cli.bots.cag_engine import cag_engine
    from pathlib import Path
    res = cag_engine.pack_context(Path(path))

    response = _build_response(
        ctx,
        command="context.pack",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Context-Augmented Generation (CAG) Envelope Packed[/bold green]")
        console.print(f"Workspace: [bold cyan]{res['workspace_name']}[/bold cyan]")
        console.print(f"Total Files Packed: [bold white]{res['total_files']}[/bold white]")
        console.print(f"Estimated Tokens: [bold white]{res['estimated_tokens']}[/bold white]")
        console.print(f"Prompt Caching: [bold green]Ephemeral Anchored ({res['prompt_caching']['provider']})[/bold green]")
        console.print(f"KV Pre-Warm Hash: [bold yellow]{res['context_hash']}[/bold yellow]")

    _emit_response(ctx, response, text_renderer=_text)
