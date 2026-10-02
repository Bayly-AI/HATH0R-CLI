"""Planes and Schema commands for HATH0R CLI."""

from __future__ import annotations

import click
from rich.table import Table

from hath0r_cli import __version__
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)

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
    {
        "name": "agentgraph.status",
        "invocation": ["hath0r agentgraph status"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "agentgraph.query",
        "invocation": ["hath0r agentgraph query <query>"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "agentgraph.validate",
        "invocation": ["hath0r agentgraph validate"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "agentgraph.sync",
        "invocation": ["hath0r agentgraph sync"],
        "status": "shipped",
        "effects": "modifying",
        "output_kind": "data",
    },
    {
        "name": "agentgraph.route",
        "invocation": ["hath0r agentgraph route --role <role>"],
        "status": "shipped",
        "effects": "read_only",
        "output_kind": "data",
    },
    {
        "name": "agentgraph.bot",
        "invocation": ["hath0r agentgraph bot"],
        "status": "shipped",
        "effects": "modifying",
        "output_kind": "data",
    },
    {
        "name": "agentgraph.migrate",
        "invocation": ["hath0r agentgraph migrate"],
        "status": "shipped",
        "effects": "modifying",
        "output_kind": "data",
    },
]


@click.command("planes")
@click.pass_context
def planes(ctx: click.Context) -> None:
    """List ADR-003 control-plane domains and implementation status."""
    data = {
        "status": "ok",
        "hidden_root": ".hath0r/",
        "legacy_forbidden": [".customerSystem/", ".ai/", ".infraOS/", "customerSystem binary"],
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
        console.print("Operator binary: hath0r — never customerSystem. Hidden root: .hath0r/ only.")

    _emit_response(ctx, response, text_renderer=_text)


@click.command("schema")
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
            "binaries": ["customerSystem"],
            "hidden_roots": [".customerSystem/", ".ai/", ".infraOS/"],
            "canonical_hidden_root": ".hath0r/",
        },
        "notes": [
            "Planned domains are discoverable here but not executable until implemented behind contracts.",
            "Do not invent hath0r process/work/validate verbs until status becomes shipped.",
        ],
    }
    response = _build_response(ctx, command="schema", state="ok", data=data)

    def _text() -> None:
        table = Table(title="HATH0R CLI commands (ADR-003 bounded surface)")
        table.add_column("Command")
        table.add_column("Status")
        table.add_column("Effects")
        color_map = {"shipped": "green", "partial": "yellow", "planned": "cyan"}
        for cmd in commands:
            status = str(cmd["status"])
            color = color_map.get(status, "white")
            table.add_row(str(cmd["name"]), f"[{color}]{status}[/{color}]", str(cmd["effects"]))
        console.print(table)
        console.print(f"Total commands listed: {len(commands)} (filter: {status_filter})")

    _emit_response(ctx, response, text_renderer=_text)
