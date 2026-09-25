"""HATH0R CLI entrypoint."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli import __version__
from hath0r_cli.catalog import CatalogError, parse_catalog
from hath0r_cli.doctor import diagnostics_for, run_checks
from hath0r_cli.envelope import CliResponse, Diagnostic, ResponseMeta
from hath0r_cli.output import OUTPUT_CHOICES, emit, progress_err, resolve_output_mode
from hath0r_cli.telemetry import get_current_trace_context, init_tracer, trace_span

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
    dry_run: bool | None = None,
) -> CliResponse:
    return CliResponse(
        command=command,
        generated_at=_utc_now(),
        state=state,
        data=data,
        diagnostics=list(diagnostics or []),
        meta=ResponseMeta(cli_version=__version__, duration_ms=_duration_ms(ctx), dry_run=dry_run),
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

    init_tracer()

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
@click.option(
    "--factories",
    "check_factories",
    is_flag=True,
    default=False,
    help="Include declarative factory specification schema and bot reference checks.",
)
@click.pass_context
def doctor(ctx: click.Context, check_mcp: bool, check_factories: bool) -> None:
    """Check group paths, control tower, member repos, and KB hub presence."""
    root = _group_root()
    kb = _kb_path()
    verbose = bool(ctx.obj.get("verbose", False))
    result = run_checks(root, kb, check_mcp=check_mcp, check_factories=check_factories)

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



# ============================================================================
# Factory & Bot Suite Commands
# ============================================================================

@main.group()
def factory() -> None:
    """Manage and execute Hath0r automation factories."""


@factory.command("list")
@click.pass_context
def factory_list(ctx: click.Context) -> None:
    """List available automation factories."""
    from pathlib import Path

    import yaml

    cli_repo_root = Path(__file__).resolve().parents[2]
    group_root = _discover_group_root() or cli_repo_root
    factories_dir = group_root / "cfg" / "factories"
    if not factories_dir.is_dir():
        factories_dir = cli_repo_root / "cfg" / "factories"

    items = []
    if factories_dir.is_dir():
        for f in factories_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "factory_id" in data:
                    items.append({
                        "id": data.get("factory_id"),
                        "name": data.get("name"),
                        "version": data.get("version"),
                        "description": data.get("description", "").strip(),
                        "bots_count": len(data.get("bots", [])),
                        "workflows_count": len(data.get("workflows", [])),
                        "file": str(f),
                    })
            except Exception:
                pass

    response = _build_response(ctx, command="factory.list", state="ok", data={"factories": items})

    def _text() -> None:
        if not items:
            click.echo("No factories found.")
            return
        table = Table(title="Hath0r Automation Factories")
        table.add_column("Factory ID", style="bold cyan")
        table.add_column("Name", style="green")
        table.add_column("Version", style="magenta")
        table.add_column("Bots", style="yellow")
        table.add_column("Workflows", style="blue")
        for it in items:
            table.add_row(
                it["id"], it["name"], str(it["version"]), str(it["bots_count"]), str(it["workflows_count"])
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@factory.command("info")
@click.argument("factory_id")
@click.pass_context
def factory_info(ctx: click.Context, factory_id: str) -> None:
    """Show detailed metadata and available workflows for a specific factory."""
    from pathlib import Path

    import yaml

    cli_repo_root = Path(__file__).resolve().parents[2]
    group_root = _discover_group_root() or cli_repo_root
    factories_dir = group_root / "cfg" / "factories"
    if not factories_dir.is_dir():
        factories_dir = cli_repo_root / "cfg" / "factories"

    factory_file = None
    for f in factories_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("factory_id") == factory_id:
                factory_file = f
                break
        except Exception:
            pass

    if not factory_file:
        response = _build_response(
            ctx,
            command="factory.info",
            state="error",
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FACTORY_NOT_FOUND",
                    message=f"Factory '{factory_id}' not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_data = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    response = _build_response(ctx, command="factory.info", state="ok", data=factory_data)

    def _text() -> None:
        console.print(f"[bold cyan]Factory:[/bold cyan] {factory_data.get('name')} ([dim]{factory_id}[/dim])")
        console.print(f"[bold]Version:[/bold] {factory_data.get('version')}")
        if factory_data.get("description"):
            console.print(f"[bold]Description:[/bold] {factory_data.get('description').strip()}")

        console.print("\n[bold yellow]Participating Bots:[/bold yellow]")
        for b in factory_data.get("bots", []):
            caps = ", ".join(b.get("capabilities", []))
            console.print(f"  • [cyan]{b.get('id')}[/cyan] ({b.get('name')}): {caps}")

        console.print("\n[bold green]Declared Workflows:[/bold green]")
        for wf in factory_data.get("workflows", []):
            sched = f" [dim](cron: {wf.get('schedule')})[/dim]" if wf.get("schedule") else ""
            console.print(f"  • [bold]{wf.get('id')}[/bold]: {wf.get('name')}{sched}")
            for st in wf.get("steps", []):
                console.print(f"      - {st.get('bot')} → {st.get('action')}")

    _emit_response(ctx, response, text_renderer=_text)


@factory.command("validate")
@click.argument("factory_id", required=False, default=None)
@click.pass_context
def factory_validate(ctx: click.Context, factory_id: str | None) -> None:
    """Validate factory configurations against schema contracts and bot integrity."""
    from hath0r_cli.factory_validation import validate_all_factories, validate_factory_file

    group_root = _discover_group_root()
    all_results = validate_all_factories(group_root)

    if factory_id:
        selected = [r for r in all_results if r.factory_id == factory_id]
        if not selected:
            # Check if factory_id is a file path
            candidate_path = Path(factory_id)
            if candidate_path.is_file():
                selected = [validate_factory_file(candidate_path)]
            else:
                response = _build_response(
                    ctx,
                    command="factory.validate",
                    state="error",
                    diagnostics=[
                        Diagnostic(
                            severity="error",
                            code="FACTORY_NOT_FOUND",
                            message=f"Factory '{factory_id}' not found.",
                        )
                    ],
                )
                _emit_response(ctx, response)
                ctx.exit(1)
        results = selected
    else:
        results = all_results

    all_valid = all(r.valid for r in results)
    state = "ok" if all_valid else "error"

    data = {
        "factories": [r.to_dict() for r in results],
        "total": len(results),
        "valid_count": sum(1 for r in results if r.valid),
        "invalid_count": sum(1 for r in results if not r.valid),
    }

    diagnostics: list[Diagnostic] = []
    for r in results:
        for err in r.errors:
            diagnostics.append(
                Diagnostic(
                    code="FACTORY_VALIDATION_ERROR",
                    message=f"[{r.factory_id}] {err}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "factory.validate"},
                    details={"factory_id": r.factory_id, "file": str(r.file_path)},
                )
            )
        for warn in r.warnings:
            diagnostics.append(
                Diagnostic(
                    code="FACTORY_VALIDATION_WARNING",
                    message=f"[{r.factory_id}] {warn}",
                    severity="warning",
                    provenance={"component": "hath0r-cli", "operation": "factory.validate"},
                    details={"factory_id": r.factory_id, "file": str(r.file_path)},
                )
            )

    response = _build_response(ctx, command="factory.validate", state=state, data=data, diagnostics=diagnostics)

    def _text() -> None:
        table = Table(title="Factory Specification Validation")
        table.add_column("Factory ID", style="bold cyan")
        table.add_column("Status")
        table.add_column("Bots", justify="right")
        table.add_column("Workflows", justify="right")
        table.add_column("Issues / Path")

        for r in results:
            status = "[green]VALID[/green]" if r.valid else "[red]INVALID[/red]"
            issues = []
            if r.errors:
                issues.append(f"[red]{len(r.errors)} error(s)[/red]")
            if r.warnings:
                issues.append(f"[yellow]{len(r.warnings)} warning(s)[/yellow]")
            issue_str = ", ".join(issues) if issues else "[dim]OK[/dim]"

            table.add_row(
                r.factory_id,
                status,
                str(r.bots_count),
                str(r.workflows_count),
                issue_str,
            )
        console.print(table)

        for r in results:
            if not r.valid:
                console.print(f"[bold red]Errors for {r.factory_id} ({r.file_path.name}):[/bold red]")
                for err in r.errors:
                    console.print(f"  [red]✗[/red] {err}")
            if r.warnings:
                console.print(f"[bold yellow]Warnings for {r.factory_id}:[/bold yellow]")
                for warn in r.warnings:
                    console.print(f"  [yellow]![/yellow] {warn}")

        if all_valid:
            console.print(f"[green]All {len(results)} factory specification(s) validated successfully.[/green]")
        else:
            console.print(
                f"[red]{data['invalid_count']} of {data['total']} factory specification(s) failed validation.[/red]"
            )

    _emit_response(ctx, response, text_renderer=_text)
    if not all_valid:
        ctx.exit(1)


@factory.command("run")
@click.argument("factory_id")
@click.option("--workflow", "-w", "workflow_id", default=None, help="Target specific workflow ID within the factory.")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without modifying git or GitHub.")
@click.pass_context
def factory_run(
    ctx: click.Context, factory_id: str, workflow_id: str | None, repo: str | None, dry_run: bool
) -> None:
    """Execute workflows defined in a factory."""
    import uuid
    from pathlib import Path

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    cli_repo_root = Path(__file__).resolve().parents[2]
    group_root = _discover_group_root() or cli_repo_root
    factories_dir = group_root / "cfg" / "factories"
    if not factories_dir.is_dir():
        factories_dir = cli_repo_root / "cfg" / "factories"

    factory_file = None
    for f in factories_dir.glob("*.yaml"):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("factory_id") == factory_id:
                factory_file = f
                break
        except Exception:
            pass

    if not factory_file:
        response = _build_response(ctx, command="factory.run", state="error", dry_run=dry_run, diagnostics=[
            Diagnostic(severity="error", code="FACTORY_NOT_FOUND", message=f"Factory '{factory_id}' not found.")
        ])
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_def = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    workflows = factory_def.get("workflows", [])

    if workflow_id:
        target_wfs = [w for w in workflows if w.get("id") == workflow_id]
        if not target_wfs:
            available = ", ".join(w.get("id", "") for w in workflows if w.get("id"))
            response = _build_response(
                ctx,
                command="factory.run",
                state="error",
                dry_run=dry_run,
                diagnostics=[
                    Diagnostic(
                        severity="error",
                        code="WORKFLOW_NOT_FOUND",
                        message=(
                            f"Workflow '{workflow_id}' not found in factory '{factory_id}'. "
                            f"Available workflows: {available or 'none'}"
                        ),
                        details={"factory_id": factory_id, "workflow": workflow_id},
                    )
                ],
            )
            _emit_response(ctx, response)
            ctx.exit(1)
        workflows = target_wfs

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    registry = BotRegistry(cwd=cli_repo_root)

    wf_results = []
    diagnostics = []

    for wf in workflows:
        wf_res = execute_workflow(wf, registry, repo=repo, dry_run=dry_run, run_id=run_id)
        wf_results.append(wf_res.to_dict())
        for st in wf_res.steps:
            if not st.success:
                diagnostics.append(
                    Diagnostic(
                        code="STEP_EXECUTION_FAILED",
                        message=f"[{wf_res.workflow_id}::{st.bot_id}] {st.error or 'Step execution failed'}",
                        severity="error",
                        provenance={"component": "hath0r-cli", "operation": "factory.run"},
                        details={
                            "factory_id": factory_id,
                            "workflow": wf_res.workflow_id,
                            "bot": st.bot_id,
                            "policy": st.policy,
                            "aborted": st.aborted,
                        },
                    )
                )

    all_success = len(diagnostics) == 0
    state = "ok" if all_success else "error"

    # Spool execution telemetry event (never blocks or errors CLI)
    spool_telemetry_event(
        event_type="factory.execution",
        payload={
            "run_id": run_id,
            "factory_id": factory_id,
            "state": state,
            "dry_run": dry_run,
            "workflows": wf_results,
        },
        base_dir=group_root,
    )

    response = _build_response(
        ctx,
        command="factory.run",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "factory_id": factory_id,
            "dry_run": dry_run,
            "workflows": wf_results,
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix}Executed factory '{factory_id}':")
        for w in wf_results:
            status_icon = "✓" if w["success"] else "✗"
            click.echo(f"  {status_icon} Workflow [{w['id']}]: {w['name']}")
            for st in w["steps"]:
                st_icon = "✓" if st["success"] else "✗"
                detail = st.get("data") or st.get("error")
                click.echo(f"    {st_icon} Bot [{st['bot']}] Action [{st['action']}]: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@factory.command("create")
@click.argument("factory_id")
@click.option("--name", default=None, help="Human-readable factory name.")
@click.option("--description", default="", help="Factory description.")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing factory file.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without writing.")
@click.pass_context
def factory_create(
    ctx: click.Context,
    factory_id: str,
    name: str | None,
    description: str,
    force: bool,
    dry_run: bool,
) -> None:
    """Create a new factory YAML under cfg/factories (Factory Manager bot)."""
    from hath0r_cli.factory_manager import FactoryManagerBot

    bot = FactoryManagerBot(cwd=Path.cwd(), group_root=_discover_group_root())
    res = bot.create(factory_id, name=name, description=description, force=force, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="factory.create", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(f"Created factory '{factory_id}' → {res.get('path')}")
        else:
            click.echo(f"Failed: {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@factory.command("update")
@click.argument("factory_id")
@click.option("--name", default=None)
@click.option("--description", default=None)
@click.option("--version", default=None)
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def factory_update(
    ctx: click.Context,
    factory_id: str,
    name: str | None,
    description: str | None,
    version: str | None,
    dry_run: bool,
) -> None:
    """Update factory metadata (name/description/version)."""
    from hath0r_cli.factory_manager import FactoryManagerBot

    bot = FactoryManagerBot(cwd=Path.cwd(), group_root=_discover_group_root())
    res = bot.update(factory_id, name=name, description=description, version=version, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="factory.update", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("path") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@factory.command("delete")
@click.argument("factory_id")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def factory_delete(ctx: click.Context, factory_id: str, dry_run: bool) -> None:
    """Delete a factory YAML manifest."""
    from hath0r_cli.factory_manager import FactoryManagerBot

    bot = FactoryManagerBot(cwd=Path.cwd(), group_root=_discover_group_root())
    res = bot.delete(factory_id, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="factory.delete", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or (f"Deleted {res.get('path')}" if res.get("success") else res.get("error")))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@factory.group("schedule")
def factory_schedule() -> None:
    """Manage and synchronize automation factory schedules."""


@factory_schedule.command("list")
@click.pass_context
def factory_schedule_list(ctx: click.Context) -> None:
    """List all declared cron schedules across automation factories."""
    from hath0r_cli.scheduler import discover_scheduled_workflows

    group_root = _discover_group_root()
    scheduled = discover_scheduled_workflows(group_root=group_root)

    items = [s.to_dict() for s in scheduled]
    response = _build_response(ctx, command="factory.schedule.list", state="ok", data={"schedules": items})

    def _text() -> None:
        if not items:
            console.print("[dim]No factory workflows with declared cron schedules found.[/dim]")
            return
        table = Table(title="Factory Automation Schedules")
        table.add_column("Factory ID", style="cyan")
        table.add_column("Workflow", style="bold green")
        table.add_column("Cron Expression", style="yellow")
        table.add_column("Next Estimated Run (UTC)", style="magenta")
        for s in items:
            table.add_row(
                s["factory_id"],
                f"{s['workflow_id']} ({s['workflow_name']})",
                s["schedule"],
                s.get("next_run") or "N/A",
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@factory_schedule.command("sync")
@click.option("--target-dir", default=None, help="Target repository root where .github/workflows/ lives.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate sync without creating or modifying files.")
@click.pass_context
def factory_schedule_sync(ctx: click.Context, target_dir: str | None, dry_run: bool) -> None:
    """Synchronize factory cron schedules into GitHub Actions workflows."""
    from pathlib import Path

    from hath0r_cli.scheduler import sync_factory_schedules_to_github

    cli_repo_root = Path(__file__).resolve().parents[2]
    group_root = _discover_group_root() or cli_repo_root
    dest_dir = Path(target_dir).resolve() if target_dir else group_root

    sync_results = sync_factory_schedules_to_github(dest_dir, group_root=group_root, dry_run=dry_run)

    response = _build_response(
        ctx,
        command="factory.schedule.sync",
        state="ok",
        dry_run=dry_run,
        data={
            "target_dir": str(dest_dir),
            "dry_run": dry_run,
            "synced_count": len(sync_results),
            "workflows": sync_results,
        },
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        if not sync_results:
            console.print(f"{prefix}[dim]No scheduled factory workflows found to synchronize.[/dim]")
            return
        console.print(
            f"{prefix}[bold green]Synchronized {len(sync_results)} schedule(s) to GitHub Actions:[/bold green]"
        )
        for item in sync_results:
            console.print(f"  • {item['action']} [cyan]{item['filename']}[/cyan] ({item['schedule']})")

    _emit_response(ctx, response, text_renderer=_text)



@main.group()
def branch() -> None:
    """Branch Bot: create, validate, and manage git branches."""


@branch.command("validate")
@click.argument("name")
@click.pass_context
def branch_validate(ctx: click.Context, name: str) -> None:
    """Validate branch name against governance taxonomy."""
    from hath0r_cli.bots import BranchBot
    bot = BranchBot()
    res = bot.validate_name(name)
    state = "ok" if res.get("valid") else "degraded"
    response = _build_response(ctx, command="branch.validate", state=state, data=res)

    def _text() -> None:
        color = "green" if res.get("valid") else "red"
        click.echo(click.style(res.get("message", ""), fg=color))

    _emit_response(ctx, response, text_renderer=_text)


@main.group()
def pr() -> None:
    """PR Bot: inspect, process Dependabot, and manage pull requests."""


@pr.command("dependabot")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--auto-merge/--no-auto-merge", default=True, help="Enable auto-merge if checks pass.")
@click.pass_context
def pr_dependabot(ctx: click.Context, pr_number: int, repo: str | None, auto_merge: bool) -> None:
    """Triage and automatically process Dependabot PRs."""
    from hath0r_cli.bots import PRBot
    bot = PRBot()
    res = bot.process_dependabot(pr_number, repo=repo, auto_merge=auto_merge)
    state = "ok" if res.get("status") == "processed" else "degraded"
    response = _build_response(ctx, command="pr.dependabot", state=state, data=res)

    def _text() -> None:
        click.echo(f"PR #{pr_number} Dependabot triage: {res.get('action') or res.get('status')}")

    _emit_response(ctx, response, text_renderer=_text)


@main.group()
def janitor() -> None:
    """Git Janitor Bot: audit and prune stale or merged branches."""


@janitor.command("scan")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.pass_context
def janitor_scan(ctx: click.Context, repo: str | None) -> None:
    """Scan for merged, closed, or stale branches."""
    from hath0r_cli.bots import GitJanitorBot
    bot = GitJanitorBot()
    res = bot.scan_stale_branches(repo=repo)
    response = _build_response(ctx, command="janitor.scan", state="ok", data=res)

    def _text() -> None:
        click.echo(
            f"Scanned {res.get('scanned_count', 0)} candidate branches. Found {res.get('stale_count', 0)} stale."
        )
        for b in res.get("stale_branches", []):
            click.echo(f"  - {b['branch']}: {b['reason']}")

    _emit_response(ctx, response, text_renderer=_text)


@janitor.command("prune")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate pruning without deleting branches.")
@click.pass_context
def janitor_prune(ctx: click.Context, repo: str | None, dry_run: bool) -> None:
    """Scan and prune all merged or closed branches."""
    from hath0r_cli.bots import GitJanitorBot
    bot = GitJanitorBot()
    scan = bot.scan_stale_branches(repo=repo)
    pruned = []
    for b in scan.get("stale_branches", []):
        res = bot.prune_branch(b["branch"], remote=True, dry_run=dry_run)
        pruned.append({
            "branch": b["branch"],
            "success": res.get("success"),
            "action": res.get("action"),
        })

    response = _build_response(ctx, command="janitor.prune", state="ok", dry_run=dry_run, data={
        "scanned": scan.get("scanned_count"),
        "dry_run": dry_run,
        "pruned": pruned,
    })

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix}Pruned {len(pruned)} stale branches.")
        for p in pruned:
            status = "✓" if p["success"] else "✗"
            act = f" ({p['action']})" if p.get("action") else ""
            click.echo(f"  {status} {p['branch']}{act}")

    _emit_response(ctx, response, text_renderer=_text)


@main.group()
def task() -> None:
    """Task Lifecycle: run canonical start and end-of-task automation and transitions."""


@task.command("start")
@click.option("--issue", "issue_number", default=None, type=int, help="Existing GitHub issue number.")
@click.option("--title", default=None, help="Issue title if creating a new ticket.")
@click.option("--slug", default=None, help="Short slug for branch name (<prefix>/<issue>-<slug>).")
@click.option(
    "--prefix",
    default="feature",
    type=click.Choice(["feature", "bugfix", "hotfix", "enhancement", "research", "fix", "chore"]),
    help="Branch taxonomy prefix.",
)
@click.option("--base", default="development", help="Base branch to branch off of.")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate issue creation/verification and branch checkout.",
)
@click.pass_context
def task_start(
    ctx: click.Context,
    issue_number: int | None,
    title: str | None,
    slug: str | None,
    prefix: str,
    base: str,
    repo: str | None,
    dry_run: bool,
) -> None:
    """Execute canonical start-of-task factory: enforce issue attachment & compliant work branch."""
    import uuid
    from pathlib import Path

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    cli_repo_root = Path(__file__).resolve().parents[2]
    factory_file = cli_repo_root / "cfg" / "factories" / "start-of-task-factory.yaml"
    if not factory_file.is_file():
        response = _build_response(
            ctx,
            command="task.start",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FACTORY_NOT_FOUND",
                    message="Canonical start-of-task-factory.yaml manifest not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    # If no issue number provided but title is given, create issue first
    if not issue_number and not title:
        response = _build_response(
            ctx,
            command="task.start",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="ISSUE_REQUIRED",
                    message="Either an existing --issue <number> or a new --title <string> is required.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_data = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    workflow_def = factory_data.get("workflows", [{}])[0]

    # Customize step args based on CLI flags
    clean_slug = (slug or title or "task").lower()
    clean_slug = "".join(c if c.isalnum() else "-" for c in clean_slug).strip("-")[:30]

    steps = []
    if not issue_number and title:
        # Step 1: create issue
        steps.append({
            "bot": "issue-guard-bot",
            "action": "create-issue",
            "args": {"title": title, "repo": repo},
            "on_failure": "abort",
        })
    else:
        # Step 1: verify issue
        steps.append({
            "bot": "issue-guard-bot",
            "action": "verify-issue",
            "args": {"issue_number": issue_number, "repo": repo},
            "on_failure": "abort",
        })

    # Step 2: ensure work branch
    steps.append({
        "bot": "branch-guard-bot",
        "action": "ensure-work-branch",
        "args": {
            "issue_number": issue_number,
            "slug": clean_slug,
            "prefix": prefix,
            "base": base,
        },
        "on_failure": "abort",
    })

    dynamic_wf = {
        "id": workflow_def.get("id", "start-of-task"),
        "name": workflow_def.get("name", "Canonical Start of Task Lifecycle"),
        "steps": steps,
    }

    registry = BotRegistry(cwd=Path.cwd())
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    exec_res = execute_workflow(dynamic_wf, registry, repo=repo, dry_run=dry_run, run_id=run_id)
    all_success = exec_res.success
    state = "ok" if all_success else "error"

    diagnostics = []
    for st in exec_res.steps:
        if not st.success:
            diagnostics.append(
                Diagnostic(
                    code="STEP_EXECUTION_FAILED",
                    message=f"[start-of-task::{st.bot_id}] {st.error or 'Step execution failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "task.start"},
                )
            )

    spool_telemetry_event(
        event_type="task.start",
        payload={
            "run_id": run_id,
            "state": state,
            "dry_run": dry_run,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        base_dir=_discover_group_root(),
    )

    response = _build_response(
        ctx,
        command="task.start",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "workflow": exec_res.to_dict(),
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix_str = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix_str}Completed Start of Task workflow ({'SUCCESS' if all_success else 'FAILED'}):")
        for st in exec_res.steps:
            icon = "✓" if st.success else "✗"
            detail = st.data if st.success else st.error
            click.echo(f"  {icon} [{st.bot_id}] {st.action}: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@task.command("finish")
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate PR creation, checks, merge, and branch pruning.")
@click.option(
    "--semver",
    default="patch",
    type=click.Choice(["major", "minor", "patch", "none"]),
    help="SemVer impact.",
)
@click.pass_context
def task_finish(ctx: click.Context, repo: str | None, dry_run: bool, semver: str) -> None:
    """Execute canonical end-of-task factory before completing an assignment."""
    import uuid
    from pathlib import Path

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    cli_repo_root = Path(__file__).resolve().parents[2]
    factory_file = cli_repo_root / "cfg" / "factories" / "end-of-task-factory.yaml"
    if not factory_file.is_file():
        response = _build_response(
            ctx,
            command="task.finish",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FACTORY_NOT_FOUND",
                    message="Canonical end-of-task-factory.yaml manifest not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    factory_data = yaml.safe_load(factory_file.read_text(encoding="utf-8"))
    workflow_def = factory_data.get("workflows", [{}])[0]

    registry = BotRegistry(cwd=Path.cwd())
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    exec_res = execute_workflow(workflow_def, registry, repo=repo, dry_run=dry_run, run_id=run_id)
    all_success = exec_res.success
    state = "ok" if all_success else "error"

    diagnostics = []
    for st in exec_res.steps:
        if not st.success:
            diagnostics.append(
                Diagnostic(
                    code="STEP_EXECUTION_FAILED",
                    message=f"[end-of-task::{st.bot_id}] {st.error or 'Step execution failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "task.finish"},
                )
            )

    spool_telemetry_event(
        event_type="task.finish",
        payload={
            "run_id": run_id,
            "state": state,
            "dry_run": dry_run,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        base_dir=_discover_group_root(),
    )

    response = _build_response(
        ctx,
        command="task.finish",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "workflow": exec_res.to_dict(),
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        click.echo(f"{prefix}Completed End of Task workflow ({'SUCCESS' if all_success else 'FAILED'}):")
        for st in exec_res.steps:
            icon = "✓" if st.success else "✗"
            detail = st.data if st.success else st.error
            click.echo(f"  {icon} [{st.bot_id}] {st.action}: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@main.group()
def jev() -> None:
    """JEV System One decision-layer status across the suite."""


@jev.command("status")
@click.pass_context
def jev_status(ctx: click.Context) -> None:
    """Report local JEV env mode and known MCP integration paths."""
    import os
    from pathlib import Path as P

    mode = (os.environ.get("JEV_MODE") or "off").strip().lower()
    enabled = mode in {"stub", "live"} or (os.environ.get("JEV_TOOL_GUARD_ENABLED") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
        "stub",
    }
    key_set = bool(
        (
            os.environ.get("JEV_API_KEY")
            or os.environ.get("TYPESAFE_API_KEY")
            or os.environ.get("AUTOJEV_API_KEY")
            or ""
        ).strip()
    )
    integrations: list[dict[str, Any]] = [
        {
            "repo": "BAI/MCP",
            "path": str(P.home() / "Development/BAI/MCP"),
            "role": "full tool-guard on mutating MCP tools",
            "modules": [
                "src/knowledgebase/core/jev_client.py",
                "src/knowledgebase/core/jev_tool_guard.py",
            ],
        },
        {
            "repo": "OpenSource/hath0r-mcp",
            "path": str(P.home() / "Development/OpenSource/hath0r-mcp"),
            "role": "tool-guard + suite_info/kb_search JEV metadata",
            "modules": [
                "src/knowledgebase/core/jev_client.py",
                "src/knowledgebase/core/jev_tool_guard.py",
            ],
        },
        {
            "repo": "1-Nation/MCP",
            "path": str(P.home() / "Development/1-Nation/MCP"),
            "role": "tool-guard + suite_info/kb_search JEV metadata",
            "modules": [
                "src/knowledgebase/core/jev_client.py",
                "src/knowledgebase/core/jev_tool_guard.py",
            ],
        },
        {
            "repo": "OpenSource/hath0r-framework",
            "path": str(P.home() / "Development/OpenSource/hath0r-framework"),
            "role": "canonical portable reference under lib/jev/",
            "modules": ["lib/jev/jev_client.py", "lib/jev/jev_tool_guard.py"],
        },
    ]
    for item in integrations:
        root = P(str(item["path"]))
        modules_list = item.get("modules")
        if isinstance(modules_list, list) and root.is_dir():
            item["present"] = all((root / str(m)).is_file() for m in modules_list)
        else:
            item["present"] = False

    data = {
        "local_env": {
            "JEV_MODE": mode,
            "enabled": enabled,
            "api_key_configured": key_set,
            "endpoint": os.environ.get("JEV_ENDPOINT") or "https://www.jevai.org/api/v1/decisions/tool-guard",
            "on_error": os.environ.get("JEV_ON_ERROR") or "allow",
        },
        "integrations": integrations,
        "docs": "Each MCP: docs/jev-tool-guard-poc.md — enable with JEV_MODE=stub|live",
    }
    response = _build_response(ctx, command="jev.status", state="ok", data=data)

    def _text() -> None:
        click.echo(f"JEV mode={mode} enabled={enabled} api_key_set={key_set}")
        for item in integrations:
            mark = "ok" if item["present"] else "missing"
            click.echo(f"  [{mark}] {item['repo']}: {item['role']}")

    _emit_response(ctx, response, text_renderer=_text)


@main.group()
def docker() -> None:
    """Docker Bot & Factory: validate and execute container workflows, monitor and diagnose stacks."""


@docker.group("workflow")
def docker_workflow() -> None:
    """Manage and execute Hath0r Docker workflow documents."""


@docker_workflow.command("validate")
@click.argument("workflow_file")
@click.pass_context
def docker_workflow_validate(ctx: click.Context, workflow_file: str) -> None:
    """Validate a Docker workflow document JSON against schema contract."""
    import json
    from pathlib import Path

    from hath0r_cli.bots import DockerBot

    wf_path = Path(workflow_file).resolve()
    if not wf_path.is_file():
        response = _build_response(
            ctx,
            command="docker.workflow.validate",
            state="error",
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FILE_NOT_FOUND",
                    message=f"Workflow file '{workflow_file}' not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    try:
        wf_data = json.loads(wf_path.read_text(encoding="utf-8"))
    except Exception as exc:
        response = _build_response(
            ctx,
            command="docker.workflow.validate",
            state="error",
            diagnostics=[
                Diagnostic(severity="error", code="INVALID_JSON", message=f"Failed to parse JSON: {exc}")
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    bot = DockerBot()
    res = bot.validate_workflow(wf_data)

    state = "ok" if res.get("valid") else "error"
    diagnostics = [
        Diagnostic(severity="error", code="WORKFLOW_SCHEMA_ERROR", message=err)
        for err in res.get("errors", [])
    ]
    response = _build_response(
        ctx,
        command="docker.workflow.validate",
        state=state,
        data=res,
        diagnostics=diagnostics,
    )

    def _text() -> None:
        if res.get("valid"):
            console.print(f"[bold green]✓ Workflow '{res.get('workflow_id')}' is valid.[/bold green]")
        else:
            console.print(f"[bold red]✗ Workflow '{res.get('workflow_id')}' failed schema validation:[/bold red]")
            for err in res.get("errors", []):
                console.print(f"  [red]•[/red] {err}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("valid"):
        ctx.exit(1)


@docker_workflow.command("run")
@click.argument("workflow_file")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate workflow steps without modifying Docker state.")
@click.pass_context
def docker_workflow_run(ctx: click.Context, workflow_file: str, dry_run: bool) -> None:
    """Validate and execute a Docker workflow via Docker Factory."""
    import json
    import uuid
    from pathlib import Path

    from hath0r_cli.bots import DockerBot
    from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event

    wf_path = Path(workflow_file).resolve()
    if not wf_path.is_file():
        response = _build_response(
            ctx,
            command="docker.workflow.run",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(
                    severity="error",
                    code="FILE_NOT_FOUND",
                    message=f"Workflow file '{workflow_file}' not found.",
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    try:
        wf_data = json.loads(wf_path.read_text(encoding="utf-8"))
    except Exception as exc:
        response = _build_response(
            ctx,
            command="docker.workflow.run",
            state="error",
            dry_run=dry_run,
            diagnostics=[
                Diagnostic(severity="error", code="INVALID_JSON", message=f"Failed to parse JSON: {exc}")
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    # 1. Validation phase
    bot = DockerBot()
    val_res = bot.validate_workflow(wf_data)
    if not val_res.get("valid"):
        response = _build_response(
            ctx,
            command="docker.workflow.run",
            state="error",
            dry_run=dry_run,
            data={"validation": val_res},
            diagnostics=[
                Diagnostic(severity="error", code="WORKFLOW_SCHEMA_ERROR", message=err)
                for err in val_res.get("errors", [])
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    # 2. Convert DockerWorkflow spec into executable factory workflow definition
    spec = wf_data.get("spec", {})
    metadata = wf_data.get("metadata", {})
    wf_id = metadata.get("id", "docker-workflow")
    factory_steps = []

    for step in spec.get("steps", []):
        op = step.get("op")
        params = dict(step.get("params") or {})
        # Map op to docker-bot action
        if op == "validate":
            action = "validate"
            params["workflow"] = wf_data
        elif op == "build":
            action = "build"
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
        elif op == "up":
            action = "up"
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
            params.setdefault("services", spec.get("services"))
        elif op == "healthcheck":
            action = "healthcheck"
            params.setdefault("container", spec.get("container", {}).get("name"))
        elif op == "diagnose":
            action = "diagnose"
            params.setdefault("container", spec.get("container", {}).get("name"))
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
        elif op == "down":
            action = "down"
            params.setdefault("compose_file", spec.get("compose", {}).get("file"))
        else:
            action = op

        factory_steps.append({
            "bot": "docker-bot",
            "action": action,
            "args": params,
            "on_failure": step.get("on_failure", "abort"),
        })

    factory_wf_def = {
        "id": wf_id,
        "name": metadata.get("name", wf_id),
        "steps": factory_steps,
    }

    cli_repo_root = Path(__file__).resolve().parents[2]
    registry = BotRegistry(cwd=cli_repo_root)
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    exec_res = execute_workflow(factory_wf_def, registry, dry_run=dry_run, run_id=run_id)
    all_success = exec_res.success
    state = "ok" if all_success else "error"

    diagnostics = []
    for st in exec_res.steps:
        if not st.success:
            diagnostics.append(
                Diagnostic(
                    code="DOCKER_STEP_FAILED",
                    message=f"[{st.action}] {st.error or 'Operation failed'}",
                    severity="error",
                    provenance={"component": "hath0r-cli", "operation": "docker.workflow.run"},
                    details={"op": st.action, "policy": st.policy},
                )
            )

    spool_telemetry_event(
        event_type="docker.workflow.execution",
        payload={
            "run_id": run_id,
            "workflow_id": wf_id,
            "state": state,
            "dry_run": dry_run,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        base_dir=cli_repo_root,
    )

    response = _build_response(
        ctx,
        command="docker.workflow.run",
        state=state,
        dry_run=dry_run,
        data={
            "run_id": run_id,
            "workflow_id": wf_id,
            "dry_run": dry_run,
            "success": all_success,
            "steps": [s.to_dict() for s in exec_res.steps],
        },
        diagnostics=diagnostics,
    )

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        status_icon = "✓" if all_success else "✗"
        console.print(f"{prefix}{status_icon} Docker Workflow [{wf_id}]: {metadata.get('name')}")
        for st in exec_res.steps:
            st_icon = "✓" if st.success else "✗"
            detail = st.data or st.error
            console.print(f"    {st_icon} Step [{st.action}]: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_success:
        ctx.exit(1)


@docker.command("diagnose")
@click.argument("container_name", required=False, default=None)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate diagnostic check.")
@click.pass_context
def docker_diagnose(ctx: click.Context, container_name: str | None, dry_run: bool) -> None:
    """Diagnose container health and configuration issues without printing secrets."""
    from hath0r_cli.bots import DockerBot

    bot = DockerBot()
    res = bot.diagnose(container_name=container_name, dry_run=dry_run)
    state = "ok" if res.get("healthy") else "degraded"
    response = _build_response(ctx, command="docker.diagnose", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("healthy"):
            console.print(f"[bold green]✓ Container '{container_name or 'all'}' is healthy.[/bold green]")
        else:
            console.print(f"[bold yellow]! Diagnostic findings for '{container_name}':[/bold yellow]")
            for f in res.get("findings", []):
                console.print(f"  [yellow]•[/yellow] {f}")
            if res.get("remediation"):
                console.print(f"\n[cyan]Remediation:[/cyan] {res['remediation']}")

    _emit_response(ctx, response, text_renderer=_text)


# ============================================================================
# Quality / preflight / deploy / release / docs bots (#66–#71)
# ============================================================================


@main.group()
def quality() -> None:
    """PR Quality Gates bot — aggregate hard gates including SonarCloud."""


@quality.command("check")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="owner/repo")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def quality_check(ctx: click.Context, pr_number: int, repo: str | None, dry_run: bool) -> None:
    """Evaluate PR status checks against configured hard gates."""
    from hath0r_cli.bots.quality import QualityGateBot

    bot = QualityGateBot(cwd=Path.cwd())
    res = bot.check_pr(pr_number, repo=repo, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="quality.check", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or json.dumps(res, indent=2))
        if res.get("hard_failures"):
            click.echo(f"Hard failures: {', '.join(res['hard_failures'])}")
        if res.get("hard_missing"):
            click.echo(f"Missing gates: {', '.join(res['hard_missing'])}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@main.group()
def preflight() -> None:
    """Pre-PR thresholds bot — run before opening a pull request."""


@preflight.command("run")
@click.option("--skip-tests", is_flag=True, default=False, help="Only check branch + VERSION.")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def preflight_run(ctx: click.Context, skip_tests: bool, dry_run: bool) -> None:
    """Block PR open until branch taxonomy, VERSION, and local gates pass."""
    from hath0r_cli.bots.quality import PreflightBot

    bot = PreflightBot(cwd=Path.cwd())
    res = bot.run(skip_tests=skip_tests, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="preflight.run", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or "preflight complete")
        for c in res.get("checks", []):
            icon = "✓" if c.get("ok") else "✗"
            detail = (
                c.get("error")
                or c.get("message")
                or c.get("version")
                or c.get("branch")
                or ""
            )
            click.echo(f"  {icon} {c.get('check')}: {detail}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@main.group()
def deploy() -> None:
    """Pre/post-deploy test bot (counts toward coverage narrative)."""


@deploy.command("pre")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def deploy_pre(ctx: click.Context, dry_run: bool) -> None:
    """Run pre-deploy test suite from cfg/quality-gates.json."""
    from hath0r_cli.bots.quality import DeployTestBot

    bot = DeployTestBot(cwd=Path.cwd())
    res = bot.run_pre_deploy(dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="deploy.pre", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("action"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@deploy.command("post")
@click.option("--base-url", default=None, help="Optional smoke URL when no cfg commands set.")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def deploy_post(ctx: click.Context, base_url: str | None, dry_run: bool) -> None:
    """Run post-deploy smoke checks."""
    from hath0r_cli.bots.quality import DeployTestBot

    bot = DeployTestBot(cwd=Path.cwd())
    res = bot.run_post_deploy(base_url=base_url, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="deploy.post", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("action") or "post-deploy complete")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@main.group()
def release() -> None:
    """Version + release notes + GitHub tag/release bot."""


@release.command("validate")
@click.pass_context
def release_validate(ctx: click.Context) -> None:
    """Validate VERSION SemVer and CHANGELOG alignment."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.validate()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.validate", state=state, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("notes")
@click.option("--version", default=None, help="Override VERSION file.")
@click.pass_context
def release_notes(ctx: click.Context, version: str | None) -> None:
    """Generate release notes from CHANGELOG section."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.generate_notes(version=version)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.notes", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(res.get("notes"))
        else:
            click.echo(res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("publish")
@click.option("--repo", default=None)
@click.option("--skip-github-release", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def release_publish(
    ctx: click.Context, repo: str | None, skip_github_release: bool, dry_run: bool
) -> None:
    """Create annotated tag and optional GitHub Release."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.tag_and_release(repo=repo, dry_run=dry_run, skip_github_release=skip_github_release)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.publish", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("tag") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@main.group()
def docs() -> None:
    """Documentation / wiki / knowledge-share bots."""


@docs.command("wiki")
@click.option("--repo", required=True, help="owner/repo with GitHub wiki enabled")
@click.option("--title", required=True, help="Wiki page title")
@click.option("--body", default=None, help="Markdown body (or stdin)")
@click.option("--pr", "pr_number", type=int, default=None)
@click.option("--force", is_flag=True, default=False, help="Ignore wiki.enabled=false")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def docs_wiki(
    ctx: click.Context,
    repo: str,
    title: str,
    body: str | None,
    pr_number: int | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Sync a PR page to the GitHub wiki when cfg enables it."""
    from hath0r_cli.bots import DocumentationBot

    content = body
    if content is None and not click.get_text_stream("stdin").isatty():
        content = click.get_text_stream("stdin").read()
    content = content or f"# {title}\n\n(empty body)\n"

    bot = DocumentationBot(cwd=Path.cwd())
    res = bot.sync_to_wiki(repo, title, content, pr_number=pr_number, dry_run=dry_run, force=force)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="docs.wiki", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("skipped"):
            click.echo(f"Skipped: {res.get('reason')}")
        else:
            click.echo(res.get("action") or res.get("status") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@docs.command("share")
@click.option("--summary", default=None, help="Knowledge summary text")
@click.option("--pr", "pr_number", type=int, default=None)
@click.option("--repo", default=None)
@click.option("--target-kb", default=None, help="Override local KB path")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def docs_share(
    ctx: click.Context,
    summary: str | None,
    pr_number: int | None,
    repo: str | None,
    target_kb: str | None,
    dry_run: bool,
) -> None:
    """Post-PR knowledge share → project MCP / group KB (idempotent by PR)."""
    from hath0r_cli.bots import DocumentationBot

    bot = DocumentationBot(cwd=Path.cwd())
    res = bot.share_knowledge(
        summary=summary
        or (f"Knowledge share for PR #{pr_number}" if pr_number else "Knowledge share"),
        pr_number=pr_number,
        repo=repo,
        target_kb=target_kb,
        dry_run=dry_run,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="docs.share", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("path") or res.get("reason") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


if __name__ == "__main__":
    main()


