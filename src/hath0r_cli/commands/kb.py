"""Kb command for HATH0R CLI."""

from __future__ import annotations

import click

from hath0r_cli.catalog import CatalogError, parse_catalog
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    _kb_path,
    _output_mode,
    _quiet,
)
from hath0r_cli.envelope import Diagnostic
from hath0r_cli.output import progress_err


@click.group()
def kb() -> None:
    """Knowledgebase helpers (group hub)."""


@kb.command("path")
@click.pass_context
def kb_path(ctx: click.Context) -> None:
    """Print the canonical OpenSource group knowledgebase path."""
    path = _kb_path()
    available = path.is_dir()
    # configured is true whenever a path was resolved (env override or group root).
    configured = True
    diagnostics: list[Diagnostic] = []
    state = "ok" if available else "unavailable"
    if not available:
        diagnostics.append(
            Diagnostic(
                code="KNOWLEDGEBASE_NOT_FOUND",
                message="The canonical OpenSource knowledgebase is unavailable.",
                severity="error",
                remediation="Verify the group root and run hath0r doctor.",
                provenance={"component": "hath0r-cli", "operation": "kb.path"},
            )
        )

    data = {
        "configured": configured,
        "available": available,
        "path": str(path),
    }

    response = _build_response(
        ctx,
        command="kb.path",
        state=state,
        data=data,
        diagnostics=diagnostics,
    )

    def _text() -> None:
        click.echo(str(path))
        if not available:
            raise SystemExit(f"knowledgebase missing: {path}")

    if _output_mode(ctx) == "json":
        # Progress/status belongs on stderr and is suppressed by --quiet.
        progress_err("resolving knowledgebase path", quiet=_quiet(ctx))
        _emit_response(ctx, response)
        if not available:
            raise SystemExit(3)
    else:
        _emit_response(ctx, response, text_renderer=_text)


@kb.command("products")
@click.pass_context
def kb_products(ctx: click.Context) -> None:
    """List canonical suite products from the group catalog."""
    catalog = _kb_path() / "catalogs" / "suite-products.yaml"
    diagnostics: list[Diagnostic] = []
    state = "ok"
    data = None
    catalog_text = ""
    exit_code: int | None = None

    if not catalog.is_file():
        state = "unavailable"
        exit_code = 3
        diagnostics.append(
            Diagnostic(
                code="PRODUCT_CATALOG_NOT_FOUND",
                message="The suite products catalog is unavailable.",
                severity="error",
                remediation="Verify the knowledgebase path and run hath0r doctor.",
                provenance={"component": "hath0r-cli", "operation": "kb.products"},
            )
        )
    else:
        catalog_text = catalog.read_text(encoding="utf-8")
        try:
            parsed = parse_catalog(catalog)
            data = parsed.to_data()
        except CatalogError as exc:
            state = "unavailable" if exc.code == "PRODUCT_CATALOG_NOT_FOUND" else "error"
            exit_code = 3 if exc.code == "PRODUCT_CATALOG_NOT_FOUND" else 2
            diagnostics.append(
                Diagnostic(
                    code=exc.code,
                    message=exc.message,
                    severity="error",
                    remediation=exc.remediation,
                    provenance={"component": "hath0r-cli", "operation": "kb.products"},
                )
            )

    response = _build_response(
        ctx,
        command="kb.products",
        state=state,
        data=data,
        diagnostics=diagnostics,
    )

    def _text() -> None:
        if not catalog.is_file():
            raise SystemExit(f"catalog missing: {catalog}")
        click.echo(catalog_text)

    if _output_mode(ctx) == "json":
        _emit_response(ctx, response)
        if exit_code is not None:
            raise SystemExit(exit_code)
    else:
        _emit_response(ctx, response, text_renderer=_text)


@kb.command("index")
@click.option("--target-dir", "-d", default=None, help="Target documentation directory to index (defaults to KB path).")
@click.option("--rebuild", is_flag=True, default=False, help="Force complete rebuild of SQLite index.")
@click.pass_context
def kb_index(ctx: click.Context, target_dir: str | None, rebuild: bool) -> None:
    """Index or incrementally synchronize documentation into the SQLite FTS5 cache."""
    from pathlib import Path
    from hath0r_cli.kb_index import SQLiteIndexStore

    dir_to_index = Path(target_dir) if target_dir else _kb_path()
    store = SQLiteIndexStore()
    sync_stats = store.sync_directory(dir_to_index, force_rebuild=rebuild)

    response = _build_response(
        ctx,
        command="kb.index",
        state="ok",
        data={
            "target_dir": str(dir_to_index),
            "rebuild": rebuild,
            "stats": sync_stats,
            "database_path": str(store.db_path),
        },
    )

    def _text() -> None:
        click.echo(f"✓ SQLite FTS5 Index Synchronized ({dir_to_index.name}):")
        click.echo(f"  • Indexed: {sync_stats['indexed']}")
        click.echo(f"  • Updated: {sync_stats['updated']}")
        click.echo(f"  • Skipped: {sync_stats['skipped']}")

    _emit_response(ctx, response, text_renderer=_text)


@kb.command("search")
@click.option("--query", "-q", required=True, help="Search query string.")
@click.option("--limit", "-n", default=5, type=int, help="Maximum search results to return.")
@click.option("--hybrid/--fts-only", default=True, help="Enable hybrid FTS5 + neural reranking.")
@click.pass_context
def kb_search(ctx: click.Context, query: str, limit: int, hybrid: bool) -> None:
    """Search knowledgebase documents and playbooks using SQLite FTS5 and hybrid reranking."""
    from hath0r_cli.kb_index import SQLiteIndexStore

    store = SQLiteIndexStore()
    if hybrid:
        hits = store.search_hybrid(query, limit=limit)
    else:
        hits = store.search_fts(query, limit=limit)

    results_data = [h.to_dict() for h in hits]
    response = _build_response(
        ctx,
        command="kb.search",
        state="ok",
        data={
            "query": query,
            "hybrid": hybrid,
            "count": len(results_data),
            "results": results_data,
        },
    )

    def _text() -> None:
        click.echo(f"Found {len(hits)} results for '{query}':")
        for i, hit in enumerate(hits, start=1):
            click.echo(f"  {i}. [{hit.category}] {hit.title} (score: {hit.score:.3f})")
            click.echo(f"     Path: {hit.path}")
            if hit.snippet:
                click.echo(f"     Snippet: {hit.snippet}")

    _emit_response(ctx, response, text_renderer=_text)


@kb.command("status")
@click.pass_context
def kb_status(ctx: click.Context) -> None:
    """Display SQLite FTS5 knowledgebase index cache statistics."""
    from hath0r_cli.kb_index import SQLiteIndexStore

    store = SQLiteIndexStore()
    stats = store.get_stats()
    response = _build_response(ctx, command="kb.status", state="ok", data=stats)

    def _text() -> None:
        click.echo("SQLite FTS5 KnowledgeBase Cache Status:")
        click.echo(f"  • Database: {stats['database_path']}")
        click.echo(f"  • Size: {stats['size_bytes']} bytes")
        click.echo(f"  • Total Documents: {stats['total_documents']}")
        cats = stats.get("categories", {})
        if cats:
            click.echo("  • Categories:")
            for cat, count in cats.items():
                click.echo(f"    - {cat}: {count}")

    _emit_response(ctx, response, text_renderer=_text)



# --- ADR-003 surface discovery (F5) -----------------------------------------
# Full domain implementations land behind contracts over time. These commands
# expose the canonical surface with honest shipped|planned status so agents
# never invent verbs and never call legacy `customerSystem`.

_ADR003_PLANES = [
    {
        "id": "meta",
        "commands": ["help", "version", "schema", "doctor", "planes"],
        "status": "partial",
        "notes": "version/doctor/schema/planes shipped; help via click",
    },
    {
        "id": "kb",
        "commands": ["kb path", "kb products"],
        "status": "shipped",
        "notes": "read discovery only; search/write planned",
    },
    {
        "id": "process",
        "commands": ["process …"],
        "status": "planned",
        "notes": "HATHOR-ADR-003 hierarchy/orchestration runs",
    },
    {
        "id": "proctor",
        "commands": ["proctor …"],
        "status": "planned",
        "notes": "gates / policy / gateway admission",
    },
    {
        "id": "operator",
        "commands": ["operator …"],
        "status": "planned",
        "notes": "brokered external systems",
    },
    {
        "id": "tower",
        "commands": ["tower …"],
        "status": "planned",
        "notes": "control tower authority surface",
    },
    {
        "id": "knowledge",
        "commands": ["knowledge …"],
        "status": "planned",
        "notes": "write/search/promote; kb path/products cover hub discovery today",
    },
    {
        "id": "work",
        "commands": ["work …"],
        "status": "planned",
        "notes": "ticketing plane",
    },
    {
        "id": "repo",
        "commands": ["repo audit", "repo clean"],
        "status": "shipped",
        "notes": "Repository hygiene, root cleanliness, and configuration organization",
    },
    {
        "id": "delivery",
        "commands": ["delivery …"],
        "status": "planned",
        "notes": "PR / quality / release façade",
    },
    {
        "id": "validate",
        "commands": ["validate …"],
        "status": "planned",
        "notes": "continuous validation system",
    },
    {
        "id": "mcp",
        "commands": ["mcp list", "mcp check", "mcp call", "mcp sources list|test|fetch-sample"],
        "status": "shipped",
        "notes": "MCP connection management, live probe, tool execution, and 1-Nation vote-source operations",
    },
]

_SHIPPED_COMMANDS = [
    {
        "name": "version",
        "invocation": ["hath0r --version"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "doctor",
        "invocation": ["hath0r doctor"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "kb.path",
        "invocation": ["hath0r kb path"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "kb.products",
        "invocation": ["hath0r kb products"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "schema",
        "invocation": ["hath0r schema"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "planes",
        "invocation": ["hath0r planes"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "mcp.list",
        "invocation": ["hath0r mcp list"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "mcp.check",
        "invocation": ["hath0r mcp check"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "mcp.call",
        "invocation": ["hath0r mcp call"],
        "status": "shipped",
        "effects": "interactive",
        "output_kind": "data",
    },
    {
        "name": "mcp.sources",
        "invocation": ["hath0r mcp sources list|test|fetch-sample"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "repo.audit",
        "invocation": ["hath0r repo audit"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "repo.clean",
        "invocation": ["hath0r repo clean"],
        "status": "shipped",
        "effects": "modifying",
        "output_kind": "data",
    },
]
