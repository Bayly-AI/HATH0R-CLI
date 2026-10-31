"""Mcp command for HATH0R CLI."""

from __future__ import annotations

import json
import sys
from typing import Any, cast

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


@mcp.command("init")
@click.option("--group", default=None, help="Override detected Hath0r MCP group (hath0r-opensource, bai, ray, 1-nation).")
@click.option("--dry-run", is_flag=True, default=False, help="Preview .hath0r/mcp.json provisioning without writing.")
@click.pass_context
def mcp_init(ctx: click.Context, group: str | None, dry_run: bool) -> None:
    """Provision canonical .hath0r/mcp.json in the current repository with its group Hath0r MCP as Priority 1."""
    from pathlib import Path

    from hath0r_cli.mcp import ensure_repo_mcp_config

    res = ensure_repo_mcp_config(Path.cwd(), group=group, sync_cfg=True, dry_run=dry_run)
    response = _build_response(
        ctx,
        command="mcp.init",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        console.print(
            f"[bold green]✓ Provisioned canonical Hath0r MCP config:[/bold green] {res['mcp_file']} "
            f"(group=[cyan]{res['group']}[/cyan], default=[yellow]{res['default_server']}[/yellow] -> {res['default_url']})"
        )

    _emit_response(ctx, response, text_renderer=_text)


@mcp.command("ensure-all")
@click.option(
    "--root",
    "root_dir",
    default="/Users/raybayly/Development",
    show_default=True,
    help="Root directory to scan for Git repositories.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Preview fleet .hath0r/mcp.json provisioning without writing.")
@click.pass_context
def mcp_ensure_all(ctx: click.Context, root_dir: str, dry_run: bool) -> None:
    """Provision and verify canonical .hath0r/mcp.json across all repositories under --root."""
    from pathlib import Path

    from hath0r_cli.mcp import ensure_all_repos_mcp_config

    res = ensure_all_repos_mcp_config(Path(root_dir), sync_cfg=True, dry_run=dry_run)
    response = _build_response(
        ctx,
        command="mcp.ensure_all",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        table = Table(title=f"Hath0r MCP Fleet Provisioning ({res['repos_count']} Repositories)")
        table.add_column("Repository", style="bold cyan")
        table.add_column("Group", style="magenta")
        table.add_column("Default MCP", style="green")
        table.add_column("Base URL", style="yellow")
        table.add_column("Un-Ignored")
        for r in res.get("repos", []):
            table.add_row(
                str(r.get("repo", "")),
                str(r.get("group", "")),
                str(r.get("default_server", "")),
                str(r.get("default_url", "")),
                "[green]yes[/green]" if r.get("mcp_not_ignored", True) else "[red]no[/red]",
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
        {
            "name": "git_branch_validate",
            "description": "Validate git branch naming and promotion path rules.",
            "parameters": {"type": "object", "properties": {"branch": {"type": "string"}}},
        },
        {
            "name": "gh_pr_create",
            "description": "Create a GitHub pull request targeting development.",
            "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "base": {"type": "string"}}},
        },
        {
            "name": "vision_inspect",
            "description": "Inspect and parse visual diagrams, images, and UI mockups.",
            "parameters": {"type": "object", "properties": {"image_path": {"type": "string"}}},
        },
        {
            "name": "kb_search",
            "description": "Search canonical knowledgebase and lessons learned documents.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        },
        {
            "name": "doctor_diagnose",
            "description": "Run diagnostic health checks on suite repos and tools.",
            "parameters": {"type": "object", "properties": {"verbose": {"type": "boolean"}}},
        },
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
    pruned_data: Any
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
        server.run(transport=cast(Any, transport))
    except Exception as exc:
        diag = [Diagnostic(code="MCP_SERVER_ERROR", message=str(exc), severity="error")]
        response = _build_response(ctx, command="mcp.serve", state="error", diagnostics=diag)
        _emit_response(ctx, response)
        ctx.exit(1)


@mcp.command("install")
@click.option("--version", "tag_or_version", default=None, help="Specific version or tag to download.")
@click.option("--container", is_flag=True, default=False, help="Install and start as Docker container.")
@click.option("--image-url", default=None, help="Remote container image URL (if not supplied, falls back to local git build).")
@click.option("--prompt/--no-prompt", "interactive_prompt", default=True, help="Prompt operator for container image URL.")
@click.pass_context
def mcp_install(
    ctx: click.Context,
    tag_or_version: str | None,
    container: bool,
    image_url: str | None,
    interactive_prompt: bool,
) -> None:
    """Download the latest version of HATH0R MCP and install as a sibling of CLI."""
    from hath0r_cli.bots.sibling_bot import SiblingManagerBot

    bot = SiblingManagerBot()
    res = bot.download_and_install("hath0r-mcp", version=tag_or_version)

    state = "ok" if res.get("success") else "error"
    diagnostics: list[Diagnostic] = []
    if not res.get("success"):
        diagnostics.append(
            Diagnostic(
                code="MCP_INSTALL_FAILED",
                message=str(res.get("error", "Failed to download and install HATH0R MCP.")),
                severity="error",
                remediation="Check internet connection, GitHub credentials, or run git clone manually.",
                provenance={"component": "hath0r-cli", "operation": "mcp.install"},
            )
        )
        response = _build_response(ctx, command="mcp.install", state=state, data=res, diagnostics=diagnostics)
        _emit_response(ctx, response)
        ctx.exit(1)

    # Optional container deployment
    if container:
        final_url = image_url
        if not final_url and interactive_prompt and sys.stdin.isatty():
            console.print("\n[bold cyan]Container Image Configuration[/bold cyan]")
            entered = click.prompt(
                "Container registry URL (press Enter to install locally from latest git version)",
                default="",
                show_default=False,
            )
            if entered.strip():
                final_url = entered.strip()

        c_res = bot.install_container("hath0r-mcp", container_url=final_url)
        res["container"] = c_res
        if not c_res.get("success"):
            diagnostics.append(
                Diagnostic(
                    code="MCP_CONTAINER_FAILED",
                    message=str(c_res.get("error", "Container deployment failed.")),
                    severity="error",
                    remediation="Check Docker daemon or local git build configuration.",
                    provenance={"component": "hath0r-cli", "operation": "mcp.install"},
                )
            )
            state = "error"

    response = _build_response(ctx, command="mcp.install", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if res.get("success"):
            action = "Already installed" if res.get("already_installed") else "Successfully installed"
            console.print(f"[bold green]✓ {action}:[/bold green] {res.get('name')} at {res.get('path')}")
            if res.get("version"):
                console.print(f"  Version: [bold cyan]{res.get('version')}[/bold cyan]")
            if res.get("installed_deps"):
                console.print("  [bold green]✓ Python editable package installed successfully.[/bold green]")
            if "container" in res:
                c = res["container"]
                if c.get("success"):
                    src = "remote URL" if c.get("source") == "remote_url" else "local git version"
                    console.print(f"  [bold green]✓ Container deployed from {src}:[/bold green] {c.get('container_name')}")
                else:
                    console.print(f"  [bold red]✗ Container deployment failed:[/bold red] {c.get('error')}")
        else:
            console.print(f"[bold red]✗ Installation failed:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if state != "ok":
        ctx.exit(1)


@mcp.command("container")
@click.option("--image-url", default=None, help="Remote container image URL (if not supplied, falls back to local git build).")
@click.option("--prompt/--no-prompt", "interactive_prompt", default=True, help="Prompt operator for container image URL.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate container setup.")
@click.pass_context
def mcp_container(
    ctx: click.Context,
    image_url: str | None,
    interactive_prompt: bool,
    dry_run: bool,
) -> None:
    """Deploy HATH0R MCP container. Prompts for container URL; falls back to local git build if not supplied."""
    from hath0r_cli.bots.sibling_bot import SiblingManagerBot

    bot = SiblingManagerBot()
    final_url = image_url
    if not final_url and interactive_prompt and sys.stdin.isatty() and not dry_run:
        console.print("[bold cyan]Container Image Configuration[/bold cyan]")
        entered = click.prompt(
            "Container registry URL (press Enter to install locally from latest git version)",
            default="",
            show_default=False,
        )
        if entered.strip():
            final_url = entered.strip()

    res = bot.install_container("hath0r-mcp", container_url=final_url, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    diagnostics: list[Diagnostic] = []
    if not res.get("success"):
        diagnostics.append(
            Diagnostic(
                code="MCP_CONTAINER_FAILED",
                message=str(res.get("error", "Failed to deploy MCP container.")),
                severity="error",
                remediation="Ensure Docker daemon is running or verify image URL.",
                provenance={"component": "hath0r-cli", "operation": "mcp.container"},
            )
        )

    response = _build_response(ctx, command="mcp.container", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if res.get("success"):
            if res.get("dry_run"):
                console.print(f"[bold yellow][DRY-RUN][/bold yellow] {res.get('action')}")
            else:
                source = "remote URL" if res.get("source") == "remote_url" else "local git version"
                console.print(f"[bold green]✓ HATH0R MCP container deployed from {source}.[/bold green]")
                if res.get("container_url"):
                    console.print(f"  Image URL: [bold cyan]{res.get('container_url')}[/bold cyan]")
                console.print(f"  Container: [bold cyan]{res.get('container_name')}[/bold cyan]")
                if res.get("status"):
                    console.print(f"  Status: [green]{res.get('status')}[/green]")
        else:
            console.print(f"[bold red]✗ Container deployment failed:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@mcp.command("audit")
@click.option("--config", "config_path", type=click.Path(), default=None, help="Optional MCP servers JSON path.")
@click.pass_context
def mcp_audit(ctx: click.Context, config_path: str | None) -> None:
    """Run BITE (Behavioral Integrity & Transparency Evaluation) audit on MCP server definitions."""
    from pathlib import Path

    from hath0r_cli.bots.bite_verifier_bot import BITEVerifierBot

    bot = BITEVerifierBot(workspace_root=Path.cwd())
    res = bot.audit_mcp_servers(Path(config_path) if config_path else None)
    state = "ok" if res.get("passed") else "error"
    response = _build_response(ctx, command="mcp.audit", state=state, data=res)

    def _text() -> None:
        table = Table(title="BITE MCP Supply-Chain Audit")
        table.add_column("Artifact", style="bold cyan")
        table.add_column("Verdict", style="bold")
        table.add_column("SHA-256", style="dim")
        table.add_column("Findings", justify="right")
        for art in res.get("artifacts", []):
            v = art.get("verdict", "CLEAN")
            color = "green" if v == "CLEAN" else ("yellow" if v == "RISKY" else "red")
            table.add_row(
                str(art.get("path", "")),
                f"[{color}]{v}[/{color}]",
                str(art.get("sha256", ""))[:16],
                str(len(art.get("behaviors", []))),
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("passed"):
        ctx.exit(1)


@mcp.command("parity")
@click.pass_context
def mcp_parity(ctx: click.Context) -> None:
    """Audit Level 1 (HATH0R-MCP) & Level 2 (HATH0R-CLI/Memory) parity and Service-Bot ownership on AgentGraph."""
    from pathlib import Path

    from hath0r_cli.bots.mcp_centralization_bot import MCPCentralizationBot

    bot = MCPCentralizationBot(cwd=Path.cwd())
    res = bot.audit_parity()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="mcp.parity", state=state, data=res)

    def _text() -> None:
        console.print(
            f"[bold cyan]MCP Level 1 / Level 2 Parity Audit ({res['standard']}):[/bold cyan] "
            f"{'[green]PASS[/green]' if res['success'] else '[red]FAIL[/red]'}"
        )
        console.print(f"  • Level 1 MCP Tools Mapped: {res['level1_mcp_tools_count']}")
        console.print(f"  • Level 2 CLI Commands Mapped: {res['level2_cli_commands_count']}")
        console.print(f"  • Registered Bots in BotRegistry: {res['registered_bots_count']}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@mcp.command("pin-schemas")
@click.option("--dry-run", is_flag=True, default=False, help="Preview without writing .hath0r/security/mcp-schema-pins.json.")
@click.pass_context
def mcp_pin_schemas(ctx: click.Context, dry_run: bool) -> None:
    """Prune Level 1 MCP tool schemas and pin SHA-256 digests in .hath0r/security/mcp-schema-pins.json."""
    from pathlib import Path

    from hath0r_cli.bots.mcp_centralization_bot import MCPCentralizationBot

    bot = MCPCentralizationBot(cwd=Path.cwd())
    res = bot.prune_and_pin_schemas(dry_run=dry_run)
    response = _build_response(ctx, command="mcp.pin-schemas", state="ok", dry_run=dry_run, data=res)

    def _text() -> None:
        console.print(
            f"[bold green]✓ Pinned {res['tools_pinned']} MCP Tool Schemas:[/bold green] {res['pin_file']} "
            f"({res['reduction_percent']}% schema pruning reduction)"
        )

    _emit_response(ctx, response, text_renderer=_text)


# ============================================================================
# Factory & Bot Suite Commands
# ============================================================================
