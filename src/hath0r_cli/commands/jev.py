"""Jev command for HATH0R CLI."""

from __future__ import annotations

import os
from typing import Any

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def jev() -> None:
    """JEV System One decision-layer status across the suite."""


@jev.command("status")
@click.pass_context
def jev_status(ctx: click.Context) -> None:
    """Report local JEV env mode and known MCP integration paths."""
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
