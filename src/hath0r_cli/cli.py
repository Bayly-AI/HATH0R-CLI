"""HATH0R CLI entrypoint."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli import __version__
from hath0r_cli.catalog import CatalogError, parse_catalog
from hath0r_cli.doctor import diagnostics_for, run_checks
from hath0r_cli.envelope import CliResponse, Diagnostic, ResponseMeta
from hath0r_cli.output import OUTPUT_CHOICES, emit, progress_err, resolve_output_mode

console = Console()

# Soft fallback only — used when it looks like a real group root.
_SOFT_FALLBACK_GROUP_ROOT = Path.home() / "Development" / "OpenSource"

_GROUP_MARKER = "hath0r-opensource"
_GROUP_ROOT_ERROR = (
    "Could not determine HATHOR OpenSource group root.\n"
    "Remediation:\n"
    "  1. Set HATH0R_GROUP_ROOT to the directory that contains AGENTS.md "
    f"(with '{_GROUP_MARKER}') and a .hath0r/ directory, or\n"
    "  2. Run the CLI from inside that group tree so walk-up discovery can find it, or\n"
    "  3. Place the group at ~/Development/OpenSource with the same markers."
)


def _looks_like_group_root(path: Path) -> bool:
    """Return True if path has AGENTS.md containing the group marker and a .hath0r/ dir."""
    agents = path / "AGENTS.md"
    hath0r_dir = path / ".hath0r"
    if not agents.is_file() or not hath0r_dir.is_dir():
        return False
    try:
        return _GROUP_MARKER in agents.read_text(encoding="utf-8")
    except OSError:
        return False


def _discover_group_root(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for a group root.

    When multiple ancestors match (member checkout nested under the group),
    prefer the outermost match so the true group root wins.
    """
    current = (start or Path.cwd()).resolve()
    found: Path | None = None
    for candidate in (current, *current.parents):
        if _looks_like_group_root(candidate):
            found = candidate
    return found


def _group_root() -> Path:
    """Resolve the OpenSource group root.

    Discovery order:
    1. HATH0R_GROUP_ROOT environment variable (if set)
    2. Walk up from cwd for AGENTS.md containing 'hath0r-opensource' plus .hath0r/
    3. Soft fallback ~/Development/OpenSource if it looks like the group root
    4. Clear error with remediation
    """
    env = os.environ.get("HATH0R_GROUP_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    found = _discover_group_root()
    if found is not None:
        return found

    soft = _SOFT_FALLBACK_GROUP_ROOT.expanduser()
    if _looks_like_group_root(soft):
        return soft.resolve()

    raise click.ClickException(_GROUP_ROOT_ERROR)


def _kb_path() -> Path:
    override = os.environ.get("HATH0R_KB_PATH")
    if override:
        return Path(override).expanduser()
    return _group_root() / ".hath0r" / "knowledgebase"


def _utc_now() -> str:
    """RFC 3339 UTC timestamp with second precision and Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _duration_ms(ctx: click.Context) -> int:
    started = ctx.obj.get("started_at", time.perf_counter())
    return max(0, int((time.perf_counter() - started) * 1000))


def _output_mode(ctx: click.Context) -> str:
    return resolve_output_mode(ctx.obj.get("output", "auto"))


def _quiet(ctx: click.Context) -> bool:
    return bool(ctx.obj.get("quiet", False))


def _build_response(
    ctx: click.Context,
    *,
    command: str,
    state: str = "ok",
    data: dict | None = None,
    diagnostics: list[Diagnostic] | None = None,
) -> CliResponse:
    return CliResponse(
        command=command,
        generated_at=_utc_now(),
        state=state,
        data=data,
        diagnostics=list(diagnostics or []),
        meta=ResponseMeta(cli_version=__version__, duration_ms=_duration_ms(ctx)),
    )


def _emit_response(
    ctx: click.Context,
    response: CliResponse,
    *,
    text_renderer=None,
) -> None:
    mode = ctx.obj.get("output", "auto")
    emit(response, mode, console, text_renderer=text_renderer)


@click.group(invoke_without_command=True)
@click.option(
    "--output",
    "-o",
    type=click.Choice(OUTPUT_CHOICES, case_sensitive=False),
    default="auto",
    show_default=True,
    help="Output format: json, text, or auto (TTY→text, non-TTY→json).",
)
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Suppress stderr progress/warnings (especially in json mode).",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Include absolute local paths in structured doctor diagnostics.",
)
@click.option(
    "--version",
    is_flag=True,
    default=False,
    help="Show the hath0r version and exit.",
)
@click.pass_context
def main(ctx: click.Context, output: str, quiet: bool, verbose: bool, version: bool) -> None:
    """HATH0R CLI — control plane for the HATHOR OpenSource group."""
    ctx.ensure_object(dict)
    ctx.obj["output"] = output.lower()
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["started_at"] = time.perf_counter()

    if version:
        _emit_version(ctx)
        ctx.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def _emit_version(ctx: click.Context) -> None:
    response = _build_response(
        ctx,
        command="version",
        state="ok",
        data={
            "binary": "hath0r",
            "package": "hath0r-cli",
            "version": __version__,
        },
    )

    def _text() -> None:
        click.echo(f"hath0r, version {__version__}")

    _emit_response(ctx, response, text_renderer=_text)


@main.command()
@click.option(
    "--mcp",
    "check_mcp",
    is_flag=True,
    default=False,
    help="Include live MCP server connection checks (BaylyAI, 1-Nation, Hath0r).",
)
@click.pass_context
def doctor(ctx: click.Context, check_mcp: bool) -> None:
    """Check group paths, control tower, member repos, and KB hub presence."""
    root = _group_root()
    kb = _kb_path()
    verbose = bool(ctx.obj.get("verbose", False))
    result = run_checks(root, kb, check_mcp=check_mcp)

    diagnostics = [
        Diagnostic(
            code=d["code"],
            message=d["message"],
            severity=d["severity"],
            remediation=d.get("remediation"),
            provenance=d.get("provenance"),
            details=d.get("details"),
        )
        for d in diagnostics_for(result)
    ]
    response = _build_response(
        ctx,
        command="doctor",
        state=result.overall_state,
        data=result.to_data(verbose=verbose),
        diagnostics=diagnostics,
    )

    def _text() -> None:
        table = Table(title="HATH0R doctor — OpenSource control tower")
        table.add_column("Check")
        table.add_column("Path / detail")
        table.add_column("Status")
        for c in result.checks:
            detail = c.path if (verbose and c.path) else (c.detail or c.message)
            status = "[green]ok[/green]" if c.state == "ok" else f"[red]{c.state}[/red]"
            table.add_row(c.label, detail or "", status)
        console.print(table)
        console.print(f"hath0r {__version__}")
        if result.failed_count:
            console.print(f"[red]doctor failed: {result.failed_count} check(s)[/red]")
        else:
            console.print("[green]doctor passed: OpenSource control tower configuration ok[/green]")

    _emit_response(ctx, response, text_renderer=_text)
    if result.failed_count:
        # Exit 6 = dependency unhealthy (Framework exit-code contract).
        raise SystemExit(6)


@main.group()
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


# --- ADR-003 surface discovery (F5) -----------------------------------------
# Full domain implementations land behind contracts over time. These commands
# expose the canonical surface with honest shipped|planned status so agents
# never invent verbs and never call legacy `aegis`.

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
        "commands": ["repo …"],
        "status": "planned",
        "notes": "UPL validate/init beyond bootstrap scripts",
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
        "commands": ["mcp list", "mcp check", "mcp call"],
        "status": "shipped",
        "notes": "MCP connection management, live probe, and tool execution (BaylyAI, 1-Nation, Hath0r)",
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
]


@main.command("planes")
@click.pass_context
def planes(ctx: click.Context) -> None:
    """List ADR-003 control-plane domains and implementation status."""
    data = {
        "binary": "hath0r",
        "cli_version": __version__,
        "authority": "HATHOR-ADR-003",
        "hidden_root": ".hath0r/",
        "legacy_forbidden": [".aegis/", ".ai/", ".infraOS/", "aegis binary"],
        "planes": list(_ADR003_PLANES),
        "counts": {
            "total": len(_ADR003_PLANES),
            "shipped": sum(1 for p in _ADR003_PLANES if p["status"] == "shipped"),
            "partial": sum(1 for p in _ADR003_PLANES if p["status"] == "partial"),
            "planned": sum(1 for p in _ADR003_PLANES if p["status"] == "planned"),
        },
    }
    response = _build_response(ctx, command="planes", state="ok", data=data)

    def _text() -> None:
        table = Table(title="HATH0R planes (ADR-003)")
        table.add_column("Plane")
        table.add_column("Status")
        table.add_column("Notes")
        color_map = {"shipped": "green", "partial": "yellow", "planned": "cyan"}
        for plane in _ADR003_PLANES:
            status = str(plane["status"])
            color = color_map.get(status, "white")
            plane_id = str(plane["id"])
            notes = str(plane.get("notes") or "")
            table.add_row(plane_id, f"[{color}]{status}[/{color}]", notes)
        console.print(table)
        console.print("Operator binary: hath0r — never aegis. Hidden root: .hath0r/ only.")

    _emit_response(ctx, response, text_renderer=_text)


@main.command("schema")
@click.option(
    "--status",
    "status_filter",
    type=click.Choice(["all", "shipped", "partial", "planned"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Filter commands/planes by implementation status.",
)
@click.pass_context
def schema(ctx: click.Context, status_filter: str) -> None:
    """Dump bounded CLI surface schema (shipped + planned ADR-003 domains)."""
    status_filter = status_filter.lower()
    commands = [c for c in _SHIPPED_COMMANDS if status_filter == "all" or c["status"] == status_filter]
    plane_rows = [plane for plane in _ADR003_PLANES if status_filter == "all" or plane["status"] == status_filter]
    data = {
        "clispec": "hath0r-surface/0.2",
        "binary": "hath0r",
        "package": "hath0r-cli",
        "version": __version__,
        "output": {"tty": "text", "piped": "json", "flag": "--output"},
        "global_args": [
            {
                "name": "--output",
                "short": "-o",
                "type": "string",
                "enum": ["auto", "text", "json"],
                "default": "auto",
            },
            {"name": "--quiet", "type": "boolean", "default": False},
            {"name": "--verbose", "type": "boolean", "default": False},
            {"name": "--version", "type": "boolean", "default": False},
        ],
        "commands": commands,
        "planes": plane_rows,
        "forbidden_legacy": {
            "binaries": ["aegis"],
            "hidden_roots": [".aegis/", ".ai/", ".infraOS/"],
            "canonical_hidden_root": ".hath0r/",
        },
        "notes": [
            "Planned domains are discoverable here but not executable until implemented behind contracts.",
            "Do not invent hath0r process/work/validate verbs until status becomes shipped.",
        ],
    }
    response = _build_response(ctx, command="schema", state="ok", data=data)

    def _text() -> None:
        click.echo(f"hath0r schema {__version__} (filter={status_filter})")
        click.echo("commands:")
        for c in commands:
            click.echo(f"  - {c['name']}: {c['status']} :: {' '.join(c['invocation'])}")
        click.echo("planes:")
        for plane in plane_rows:
            click.echo(f"  - {plane['id']}: {plane['status']}")

    _emit_response(ctx, response, text_renderer=_text)


# ============================================================================
# MCP (Model Context Protocol) Connection Plane
# ============================================================================

@main.group()
def mcp() -> None:
    """Model Context Protocol (MCP) server connections and tool operations."""


@mcp.command("list")
@click.pass_context
def mcp_list(ctx: click.Context) -> None:
    """List configured MCP servers (BaylyAI, 1-Nation, Hath0r)."""
    from hath0r_cli.mcp import load_mcp_connections

    root = _discover_group_root()
    servers = load_mcp_connections(root)
    response = _build_response(
        ctx,
        command="mcp.list",
        state="ok",
        data={"servers": servers, "count": len(servers)},
    )

    def _text() -> None:
        table = Table(title="Configured MCP Servers")
        table.add_column("ID", style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Group", style="magenta")
        table.add_column("Transport", style="blue")
        table.add_column("Base URL", style="yellow")
        table.add_column("Enabled")
        for s in servers:
            table.add_row(
                s.get("id", ""),
                s.get("name", ""),
                s.get("group", ""),
                s.get("transport", ""),
                s.get("base_url", ""),
                "[green]yes[/green]" if s.get("enabled", True) else "[red]no[/red]",
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@mcp.command("check")
@click.option("--timeout", default=2.5, type=float, help="Probe timeout in seconds per server.")
@click.pass_context
def mcp_check(ctx: click.Context, timeout: float) -> None:
    """Verify live connectivity and tool discovery across all MCP connections."""
    from hath0r_cli.mcp import check_all_mcp_connections

    root = _discover_group_root()
    results = check_all_mcp_connections(group_root=root, timeout=timeout)

    all_ok = all(r.state == "ok" for r in results)
    state = "ok" if all_ok else ("degraded" if any(r.state == "ok" for r in results) else "error")

    data = {
        "servers": [r.to_dict() for r in results],
        "total": len(results),
        "ok_count": sum(1 for r in results if r.state == "ok"),
        "failed_count": sum(1 for r in results if r.state != "ok"),
    }

    diagnostics: list[Diagnostic] = []
    for r in results:
        if r.state != "ok":
            diagnostics.append(
                Diagnostic(
                    code="MCP_CONNECTION_FAILED",
                    message=f"MCP server '{r.name}' failed check: {r.message}",
                    severity="warning" if r.state == "degraded" else "error",
                    remediation=f"Ensure {r.name} container or process is running at {r.base_url}.",
                    provenance={"component": "hath0r-cli", "operation": "mcp.check"},
                    details={"server_id": r.server_id, "url": r.base_url},
                )
            )

    response = _build_response(ctx, command="mcp.check", state=state, data=data, diagnostics=diagnostics)

    def _text() -> None:
        table = Table(title="MCP Server Connection Health")
        table.add_column("Server", style="bold cyan")
        table.add_column("Status")
        table.add_column("Latency")
        table.add_column("Tools", justify="right")
        table.add_column("Endpoint / Detail")

        for r in results:
            if r.state == "ok":
                status = "[green]OK[/green]"
            elif r.state == "degraded":
                status = "[yellow]DEGRADED[/yellow]"
            else:
                status = "[red]UNREACHABLE[/red]"

            table.add_row(
                r.name,
                status,
                f"{r.latency_ms}ms",
                str(r.tools_count),
                r.base_url if r.state == "ok" else r.message,
            )
        console.print(table)
        if all_ok:
            console.print("[green]All MCP connections active and responding.[/green]")
        else:
            msg = f"{data['failed_count']} of {data['total']} MCP server(s) degraded or unreachable."
            console.print(f"[yellow]{msg}[/yellow]")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_ok and state == "error":
        raise SystemExit(6)


@mcp.command("call")
@click.argument("server_id")
@click.argument("tool_name")
@click.option("--args", "json_args", default="{}", help="Tool arguments as JSON string.")
@click.pass_context
def mcp_call(ctx: click.Context, server_id: str, tool_name: str, json_args: str) -> None:
    """Execute an MCP tool on a specified server."""
    import json

    from hath0r_cli.mcp import call_mcp_tool

    try:
        parsed_args = json.loads(json_args)
    except Exception as exc:
        raise click.BadParameter(f"Invalid JSON in --args: {exc}")

    root = _discover_group_root()
    try:
        result = call_mcp_tool(server_id, tool_name, arguments=parsed_args, group_root=root)
        response = _build_response(
            ctx,
            command="mcp.call",
            state="ok",
            data={"server_id": server_id, "tool": tool_name, "result": result},
        )

        def _text() -> None:
            click.echo(json.dumps(result, indent=2))

        _emit_response(ctx, response, text_renderer=_text)
    except Exception as exc:
        diag = [Diagnostic(code="MCP_CALL_FAILED", message=str(exc), severity="error")]
        response = _build_response(ctx, command="mcp.call", state="error", diagnostics=diag)
        _emit_response(ctx, response)
        ctx.exit(1)


if __name__ == "__main__":
    main()
