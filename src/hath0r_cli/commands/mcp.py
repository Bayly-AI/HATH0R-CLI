"""Mcp command for HATH0R CLI."""

from __future__ import annotations

import json

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _discover_group_root,
    _emit_response,
    console,
)
from hath0r_cli.envelope import Diagnostic


@click.group()
def mcp() -> None:
    """Model Context Protocol (MCP) server connections and tool operations."""


@mcp.group("sources")
def mcp_sources() -> None:
    """Use bounded 1-Nation MCP tools for federal vote-source operations."""


def _mcp_source_operation(
    ctx: click.Context,
    *,
    command: str,
    operation: str,
    source_id: str | None,
    server_id: str,
) -> None:
    from hath0r_cli.mcp import call_vote_source_operation

    root = _discover_group_root()
    try:
        result = call_vote_source_operation(
            operation,
            source_id,
            server_id=server_id,
            group_root=root,
        )
    except Exception as exc:
        response = _build_response(
            ctx,
            command=command,
            state="error",
            diagnostics=[
                Diagnostic(
                    code="VOTE_SOURCE_MCP_CALL_FAILED",
                    message=str(exc),
                    severity="error",
                    remediation="Run hath0r mcp check and verify the configured 1-Nation MCP server.",
                    provenance={"component": "hath0r-cli", "operation": command},
                    details={"server_id": server_id, "source_id": source_id},
                )
            ],
        )
        _emit_response(ctx, response)
        ctx.exit(1)

    source_state = str(result.get("state", "ok" if operation == "list" else "error"))
    state = "ok" if source_state == "ok" else "degraded"
    diagnostics: list[Diagnostic] = []
    if source_state != "ok":
        diagnostics.append(
            Diagnostic(
                code=f"VOTE_SOURCE_{source_state.upper()}",
                message=f"Vote source operation returned {source_state}.",
                severity="warning",
                remediation=(
                    "Configure the external credential through the documented credentials file."
                    if source_state == "credential_required"
                    else "Inspect the structured source response and follow the ATC vote-source procedure."
                ),
                provenance={"component": "hath0r-cli", "operation": command},
                details={"server_id": server_id, "source_id": source_id, "source_state": source_state},
            )
        )

    response = _build_response(
        ctx,
        command=command,
        state=state,
        data={"server_id": server_id, "operation": operation, "result": result},
        diagnostics=diagnostics,
    )

    def _text() -> None:
        click.echo(json.dumps(result, indent=2))

    _emit_response(ctx, response, text_renderer=_text)
    if source_state not in {"ok", "credential_required"}:
        ctx.exit(6)


@mcp_sources.command("list")
@click.option("--server", "server_id", default="1-nation-mcp", show_default=True)
@click.pass_context
def mcp_sources_list(ctx: click.Context, server_id: str) -> None:
    """List configured federal vote sources through 1N-MCP."""
    _mcp_source_operation(
        ctx,
        command="mcp.sources.list",
        operation="list",
        source_id=None,
        server_id=server_id,
    )


@mcp_sources.command("test")
@click.argument("source_id")
@click.option("--server", "server_id", default="1-nation-mcp", show_default=True)
@click.pass_context
def mcp_sources_test(ctx: click.Context, source_id: str, server_id: str) -> None:
    """Test a catalog-declared federal vote source through 1N-MCP."""
    _mcp_source_operation(
        ctx,
        command="mcp.sources.test",
        operation="test",
        source_id=source_id,
        server_id=server_id,
    )


@mcp_sources.command("fetch-sample")
@click.argument("source_id")
@click.option("--server", "server_id", default="1-nation-mcp", show_default=True)
@click.pass_context
def mcp_sources_fetch_sample(ctx: click.Context, source_id: str, server_id: str) -> None:
    """Fetch a bounded sample from a catalog-declared vote source through 1N-MCP."""
    _mcp_source_operation(
        ctx,
        command="mcp.sources.fetch-sample",
        operation="fetch_sample",
        source_id=source_id,
        server_id=server_id,
    )


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



