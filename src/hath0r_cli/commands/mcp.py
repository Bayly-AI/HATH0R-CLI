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


@mcp.command("route")
@click.option("--intent", "-i", required=True, help="Task intent or natural language prompt.")
@click.option("--top-k", "-k", default=5, type=int, help="Maximum number of tools to return.")
@click.option("--threshold", "-t", default=0.0, type=float, help="Minimum relevance score threshold.")
@click.option("--prune/--no-prune", default=True, help="Prune tool parameter schemas.")
@click.pass_context
def mcp_route(ctx: click.Context, intent: str, top_k: int, threshold: float, prune: bool) -> None:
    """Dynamically route and rank active tools matching task intent to avoid context bloat."""
    from hath0r_cli.mcp import DynamicToolRouter

    # Generate reference tools list
    sample_tools = [
        {"name": "git_branch_validate", "description": "Validate git branch naming and promotion path rules.", "parameters": {"type": "object", "properties": {"branch": {"type": "string"}}}},
        {"name": "gh_pr_create", "description": "Create a GitHub pull request targeting development.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "base": {"type": "string"}}}},
        {"name": "vision_inspect", "description": "Inspect and parse visual diagrams, images, and UI mockups.", "parameters": {"type": "object", "properties": {"image_path": {"type": "string"}}}},
        {"name": "kb_search", "description": "Search canonical knowledgebase and lessons learned documents.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}},
        {"name": "doctor_diagnose", "description": "Run diagnostic health checks on suite repos and tools.", "parameters": {"type": "object", "properties": {"verbose": {"type": "boolean"}}}},
    ]

    router = DynamicToolRouter(sample_tools)
    selected = router.route(intent=intent, top_k=top_k, threshold=threshold, prune=prune)

    response = _build_response(
        ctx,
        command="mcp.route",
        state="ok",
        data={
            "intent": intent,
            "top_k": top_k,
            "selected_tools_count": len(selected),
            "tools": selected,
        },
    )

    def _text() -> None:
        click.echo(f"Top {len(selected)} tools matching '{intent}':")
        for t in selected:
            click.echo(f"  • {t.get('name')}: {t.get('description', '')}")

    _emit_response(ctx, response, text_renderer=_text)


@mcp.command("prune")
@click.argument("schema_file", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def mcp_prune(ctx: click.Context, schema_file: str) -> None:
    """Prune and compress a tool JSON schema to minimize context token footprint."""
    from pathlib import Path

    from hath0r_cli.mcp import SchemaPruner

    p = Path(schema_file)
    try:
        raw_data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise click.BadParameter(f"Failed to parse JSON schema: {exc}")

    pruner = SchemaPruner()
    if isinstance(raw_data, list):
        pruned_data = [pruner.prune(item) for item in raw_data]
    else:
        pruned_data = pruner.prune(raw_data)

    orig_size = len(json.dumps(raw_data))
    pruned_size = len(json.dumps(pruned_data))
    reduction_pct = round((1.0 - (pruned_size / float(orig_size or 1))) * 100, 1)

    response = _build_response(
        ctx,
        command="mcp.prune",
        state="ok",
        data={
            "source_file": str(p),
            "original_bytes": orig_size,
            "pruned_bytes": pruned_size,
            "reduction_percent": reduction_pct,
            "pruned_schema": pruned_data,
        },
    )

    def _text() -> None:
        click.echo(f"Pruned {p.name}: {orig_size}B → {pruned_size}B ({reduction_pct}% reduction)")

    _emit_response(ctx, response, text_renderer=_text)


@mcp.command("connect")
@click.argument("name")
@click.option("--command", "-c", required=True, help="Command to launch the MCP server executable.")
@click.option("--env", "-e", multiple=True, help="Environment variables in KEY=VALUE format.")
@click.pass_context
def mcp_connect(ctx: click.Context, name: str, command: str, env: tuple[str, ...]) -> None:
    """Dynamically mount and register an MCP server connection."""
    from hath0r_cli.mcp_security import DynamicMCPManager

    env_dict = {}
    for item in env:
        if "=" in item:
            k, v = item.split("=", 1)
            env_dict[k.strip()] = v.strip()

    mgr = DynamicMCPManager()
    res = mgr.connect_server(name=name, command=command, env=env_dict)

    response = _build_response(
        ctx,
        command="mcp.connect",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Dynamically Mounted MCP Server:[/bold green] [cyan]{name}[/cyan]")
            console.print(f"  • Command: {command}")
        else:
            console.print(f"[bold red]✗ Failed to mount MCP server:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@mcp.command("inspect")
@click.option("--server", "-s", required=True, help="Target MCP server name.")
@click.option("--tool", "-t", required=True, help="Invoked tool name.")
@click.option("--args", "-a", "args_json", required=True, help="Tool arguments formatted as JSON string.")
@click.pass_context
def mcp_inspect(ctx: click.Context, server: str, tool: str, args_json: str) -> None:
    """Inspect in-flight MCP tool invocation against security policies."""
    from hath0r_cli.mcp_security import MCPSecurityPolicyEngine

    try:
        arguments = json.loads(args_json)
    except Exception as exc:
        raise click.BadParameter(f"Invalid JSON in --args: {exc}")

    engine = MCPSecurityPolicyEngine()
    verdict = engine.inspect_invocation(server_name=server, tool_name=tool, arguments=arguments)

    response = _build_response(
        ctx,
        command="mcp.inspect",
        state="ok" if verdict.allowed else "security_block",
        data={
            "server": server,
            "tool": tool,
            "arguments": arguments,
            "verdict": verdict.to_dict(),
        },
    )

    def _text() -> None:
        if verdict.allowed:
            console.print(f"[bold green]✓ In-Flight Tool Call ALLOWED:[/bold green] {server}::{tool}")
            console.print(f"  • Risk Level: [cyan]{verdict.risk_level}[/cyan]")
            console.print(f"  • Reason: {verdict.reason}")
        else:
            console.print(f"[bold red]✗ In-Flight Tool Call BLOCKED:[/bold red] {server}::{tool}")
            console.print(f"  • Rule Triggered: [bold yellow]{verdict.rule_triggered}[/bold yellow]")
            console.print(f"  • Risk Level: [bold red]{verdict.risk_level.upper()}[/bold red]")
            console.print(f"  • Violation: {verdict.reason}")

    _emit_response(ctx, response, text_renderer=_text)


@mcp.group("policy")
def mcp_policy() -> None:
    """Manage and inspect in-flight MCP tool execution security guardrails."""
    pass


@mcp_policy.command("list")
@click.pass_context
def mcp_policy_list(ctx: click.Context) -> None:
    """List all active MCP security guardrail policies."""
    from hath0r_cli.mcp_security import MCPSecurityPolicyEngine

    engine = MCPSecurityPolicyEngine()
    rules = engine.list_rules()

    response = _build_response(
        ctx,
        command="mcp.policy.list",
        state="ok",
        data={"rules": rules, "count": len(rules)},
    )

    def _text() -> None:
        table = Table(title="MCP Security Guardrails")
        table.add_column("Rule ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Risk Level", style="yellow")
        table.add_column("Description", style="white")

        for r in rules:
            risk_color = "red" if r["risk"] == "CRITICAL" else "yellow"
            table.add_row(
                r["id"],
                r["name"],
                f"[{risk_color}]{r['risk']}[/{risk_color}]",
                r["description"],
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@mcp.command("serve")
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport protocol (default: stdio).",
)
@click.option(
    "--install-claude",
    is_flag=True,
    help="Register hath0r-cli connector into Claude Desktop config and launch server.",
)
@click.option(
    "--install-claude-only",
    is_flag=True,
    help="Register hath0r-cli connector into Claude Desktop config and exit.",
)
@click.option(
    "--binary",
    type=click.Path(dir_okay=False),
    help="Explicit path to hath0r binary for Claude Desktop connector (need not exist yet).",
)
@click.pass_context
def mcp_serve(
    ctx: click.Context,
    transport: str,
    install_claude: bool,
    install_claude_only: bool,
    binary: str | None,
) -> None:
    """Run FastMCP server exposing HATH0R tools to Claude Desktop & external MCP clients."""
    from hath0r_cli.server.mcp_server import (
        create_mcp_server,
        install_claude_desktop_connector,
    )

    if install_claude or install_claude_only:
        install_res = install_claude_desktop_connector(hath0r_binary=binary)
        if install_claude_only:
            response = _build_response(
                ctx,
                command="mcp.serve",
                state="ok",
                data=install_res,
            )

            def _text() -> None:
                console.print("[bold green]✓ HATH0R CLI Connector Registered with Claude Desktop[/bold green]")
                console.print(f"  • Config File: [cyan]{install_res['config_path']}[/cyan]")
                console.print(f"  • Connector Name: [yellow]{install_res['server_name']}[/yellow]")
                console.print(f"  • Command: {install_res['command']} {' '.join(install_res['args'])}")
                console.print("\nRestart Claude Desktop to activate the connector.")

            _emit_response(ctx, response, text_renderer=_text)
            return

    try:
        server = create_mcp_server()
        server.run(transport=transport)
    except Exception as exc:
        diag = [Diagnostic(code="MCP_SERVER_ERROR", message=str(exc), severity="error")]
        response = _build_response(ctx, command="mcp.serve", state="error", diagnostics=diag)
        _emit_response(ctx, response)
        ctx.exit(1)




# ============================================================================
# Factory & Bot Suite Commands
# ============================================================================
