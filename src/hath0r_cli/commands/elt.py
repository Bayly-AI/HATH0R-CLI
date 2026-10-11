"""Embedded ELT command group for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("elt")
def elt() -> None:
    """Embedded ELT (Extract, Load, Transform) data pipeline and projection management."""


@elt.command("extract")
@click.option("--source", "-s", required=True, help="Source path or URI (e.g. docs/, mcp://server, git).")
@click.option(
    "--type",
    "-t",
    "source_type",
    type=click.Choice(["docs", "mcp", "git", "telemetry", "raw"], case_sensitive=False),
    default="docs",
    help="Type of data source to extract.",
)
@click.option("--glob", "glob_pattern", default="**/*.md", help="Glob pattern for doc extraction (default **/*.md).")
@click.option("--commits", type=int, default=25, help="Max commits to extract for git source.")
@click.pass_context
def elt_extract(
    ctx: click.Context,
    source: str,
    source_type: str,
    glob_pattern: str,
    commits: int,
) -> None:
    """Extract raw inputs and load them into raw staging without destructive parsing."""
    from hath0r_cli.bots.embedded_elt_bot import EmbeddedELTBot

    bot = EmbeddedELTBot(cwd=Path.cwd())
    source_type_lower = source_type.lower()
    data: dict = {}

    if source_type_lower == "docs":
        res = bot.extract_and_stage_docs(target_dir=source, glob_pattern=glob_pattern)
        data = res.to_dict()
    elif source_type_lower == "git":
        res = bot.extract_and_stage_git(repo_dir=source if source != "git" else None, max_commits=commits)
        data = res.to_dict()
    elif source_type_lower == "mcp":
        server_id = source.replace("mcp://", "").split("/")[0]
        source_id = source.split("/")[1] if "/" in source.replace("mcp://", "") else None
        res_mcp = bot.extract_and_stage_mcp(server_id=server_id, source_id=source_id)
        data = res_mcp
    else:
        # Raw / telemetry direct file read
        p = Path(source)
        if p.is_file():
            content = p.read_text(encoding="utf-8", errors="ignore")
            res_raw = bot.stage_raw(source_uri=str(p), source_type=source_type_lower, raw_payload=content)
            data = res_raw
        else:
            ctx.fail(f"Source file does not exist: {source}")

    response = _build_response(ctx, command="elt.extract", state="ok", data=data)

    def _text() -> None:
        if source_type_lower in ("docs", "git"):
            scanned = data.get("total_scanned", 0)
            new_staged = data.get("staged_new", 0)
            dups = data.get("duplicates_skipped", 0)
            console.print(f"[bold green]✓ Extraction Complete ({source_type_lower}):[/bold green]")
            console.print(f"  • Total Scanned: {scanned}")
            console.print(f"  • Newly Staged: {new_staged}")
            console.print(f"  • Duplicates Skipped (Idempotent): {dups}")
            if data.get("errors"):
                for err in data["errors"]:
                    console.print(f"  [red]• Error: {err}[/red]")
        else:
            rec_id = data.get("record_id")
            sha = data.get("content_sha256", "")[:12]
            is_dup = data.get("is_duplicate", False)
            console.print(f"[bold green]✓ Record Staged:[/bold green] ID #{rec_id} (SHA-256: {sha}...) [duplicate={is_dup}]")

    _emit_response(ctx, response, text_renderer=_text)


@elt.command("load")
@click.option("--source", "-s", required=True, help="Canonical source URI identifier.")
@click.option("--type", "-t", "source_type", default="raw", help="Source type (e.g. raw, api, telemetry).")
@click.option("--file", "-f", "file_path", type=click.Path(exists=True), help="Load payload from file.")
@click.option("--raw", "-r", "raw_payload", help="Raw string or JSON payload to stage.")
@click.pass_context
def elt_load(
    ctx: click.Context,
    source: str,
    source_type: str,
    file_path: Optional[str],
    raw_payload: Optional[str],
) -> None:
    """Load raw payload into staging store."""
    from hath0r_cli.bots.embedded_elt_bot import EmbeddedELTBot

    if not file_path and not raw_payload:
        ctx.fail("Either --file or --raw must be specified.")

    payload = ""
    if file_path:
        payload = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    elif raw_payload:
        payload = raw_payload

    bot = EmbeddedELTBot(cwd=Path.cwd())
    res = bot.stage_raw(source_uri=source, source_type=source_type, raw_payload=payload)
    response = _build_response(ctx, command="elt.load", state="ok", data=res)

    def _text() -> None:
        rec_id = res.get("record_id")
        sha = res.get("content_sha256", "")[:12]
        is_dup = res.get("is_duplicate", False)
        console.print(f"[bold green]✓ Loaded Raw Record:[/bold green] ID #{rec_id} ({source}) [SHA: {sha}..., duplicate={is_dup}]")

    _emit_response(ctx, response, text_renderer=_text)


@elt.command("transform")
@click.option(
    "--projection",
    "-p",
    type=click.Choice(["fts5", "colpali", "agentgraph", "finops", "all"], case_sensitive=False),
    default="all",
    help="Target projection to synchronize.",
)
@click.option("--rebuild", is_flag=True, default=False, help="Force full rebuild of projection from raw staging.")
@click.option("--limit", type=int, default=100, help="Max records to project in this run.")
@click.pass_context
def elt_transform(
    ctx: click.Context,
    projection: str,
    rebuild: bool,
    limit: int,
) -> None:
    """Transform staged records into downstream views, indexes, and graphs."""
    from hath0r_cli.bots.transformation_pipeline_bot import TransformationPipelineBot

    bot = TransformationPipelineBot(cwd=Path.cwd())
    proj_lower = projection.lower()

    if proj_lower == "all":
        data = bot.transform_all(force_rebuild=rebuild, limit=limit)
    else:
        res = bot.transform_projection(proj_lower, force_rebuild=rebuild, limit=limit)
        data = {proj_lower: res.to_dict()}

    response = _build_response(ctx, command="elt.transform", state="ok", data=data)

    def _text() -> None:
        table = Table(title="Embedded ELT Projection Execution")
        table.add_column("Projection", style="bold cyan")
        table.add_column("Processed", style="yellow")
        table.add_column("Success", style="green")
        table.add_column("Errors", style="red")
        table.add_column("Duration (ms)", style="magenta")

        for name, details in data.items():
            table.add_row(
                name,
                str(details.get("processed_count", 0)),
                str(details.get("success_count", 0)),
                str(details.get("error_count", 0)),
                str(details.get("duration_ms", 0.0)),
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@elt.command("status")
@click.pass_context
def elt_status(ctx: click.Context) -> None:
    """Inspect raw staging storage health, database sizes, and projection queues."""
    from hath0r_cli.bots.transformation_pipeline_bot import TransformationPipelineBot

    bot = TransformationPipelineBot(cwd=Path.cwd())
    data = bot.get_pipeline_status()
    response = _build_response(ctx, command="elt.status", state="ok", data=data)

    def _text() -> None:
        stats = data.get("store_stats", {})
        console.print(Panel(
            f"[bold white]Database:[/bold white] {stats.get('database_path')}\n"
            f"[bold white]Size:[/bold white] {stats.get('database_size_bytes', 0):,} bytes\n"
            f"[bold white]Total Raw Records:[/bold white] {stats.get('total_records', 0):,}\n"
            f"[bold white]Total Content Volume:[/bold white] {stats.get('total_content_bytes', 0):,} bytes",
            title="Embedded ELT Staging Store",
            border_style="cyan",
        ))

        # Sources table
        src_table = Table(title="Staged Sources Breakdown")
        src_table.add_column("Source Type", style="bold yellow")
        src_table.add_column("Record Count", style="green")
        for src, cnt in stats.get("source_types", {}).items():
            src_table.add_row(src, str(cnt))
        console.print(src_table)

        # Projections table
        proj_table = Table(title="Downstream Projections Health")
        proj_table.add_column("Projection", style="bold cyan")
        proj_table.add_column("Pending / Dirty Queue", style="yellow")
        proj_table.add_column("Synced Status", style="green")

        for proj, pdata in data.get("projections", {}).items():
            pending = pdata.get("pending_or_dirty", 0)
            synced_str = json.dumps(pdata.get("synced_status", {}))
            proj_table.add_row(proj, str(pending), synced_str)
        console.print(proj_table)

    _emit_response(ctx, response, text_renderer=_text)


@elt.command("prune")
@click.option("--retention", "-r", type=int, default=30, help="Retention period in days (default 30).")
@click.pass_context
def elt_prune(ctx: click.Context, retention: int) -> None:
    """Prune historical raw staging records older than retention period."""
    from hath0r_cli.bots.embedded_elt_bot import EmbeddedELTBot

    bot = EmbeddedELTBot(cwd=Path.cwd())
    res = bot.prune(retention_days=retention)
    response = _build_response(ctx, command="elt.prune", state="ok", data=res)

    def _text() -> None:
        console.print(f"[bold green]✓ Pruning Complete:[/bold green] Deleted {res.get('records_deleted', 0)} records older than {retention} days.")

    _emit_response(ctx, response, text_renderer=_text)
