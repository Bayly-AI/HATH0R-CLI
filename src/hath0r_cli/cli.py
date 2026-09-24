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
        for it in items:
            table.add_row(it["id"], it["name"], str(it["version"]), str(it["bots_count"]))
        console.print(table)

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
@click.option("--repo", default=None, help="Target GitHub repository (owner/repo).")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate execution without modifying git or GitHub.")
@click.pass_context
def factory_run(ctx: click.Context, factory_id: str, repo: str | None, dry_run: bool) -> None:
    """Execute all workflows defined in a factory."""
    from pathlib import Path

    import yaml

    from hath0r_cli.step_runner import BotRegistry, execute_workflow

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
    registry = BotRegistry(cwd=cli_repo_root)

    wf_results = []
    diagnostics = []

    for wf in workflows:
        wf_res = execute_workflow(wf, registry, repo=repo, dry_run=dry_run)
        wf_results.append(wf_res.to_dict())
        for st in wf_res.steps:
            if not st.success:
                diagnostics.append(
                    Diagnostic(
                        code="STEP_EXECUTION_FAILED",
                        message=f"[{wf_res.workflow_id}::{st.bot_id}] {st.error or 'Step execution failed'}",
                        severity="error",
                        provenance={"component": "hath0r-cli", "operation": "factory.run"},
                        details={"factory_id": factory_id, "workflow": wf_res.workflow_id, "bot": st.bot_id},
                    )
                )

    all_success = len(diagnostics) == 0
    state = "ok" if all_success else "error"

    response = _build_response(
        ctx,
        command="factory.run",
        state=state,
        dry_run=dry_run,
        data={
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
    integrations = [
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
        root = P(item["path"])
        item["present"] = (root / item["modules"][0].split("/")[0]).exists() if root.exists() else False
        # better present check
        item["present"] = all((root / m).is_file() for m in item["modules"]) if root.is_dir() else False

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


if __name__ == "__main__":
    main()

