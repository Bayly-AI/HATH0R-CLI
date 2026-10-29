"""Repository Threat-Model-as-Code (`THREATMODEL.md`) Bot & CLI Commands (CR-AGENTIC-SEC-001 / WS5)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from hath0r_cli.common import _build_response, _emit_response

console = Console()

REQUIRED_THREATMODEL_SECTIONS = (
    "## Deployment & Runtime Mode",
    "## External Attack Surface",
    "## Trusted vs. Untrusted Inputs",
    "## Out-of-Scope Threat Assumptions",
)

FORBIDDEN_PERMISSIVE_PATTERNS = (
    re.compile(r"trust_all_inputs\s*:\s*true", re.IGNORECASE),
    re.compile(r"allow_unauthenticated_shell\s*:\s*true", re.IGNORECASE),
    re.compile(r"bypass_bite_verification\s*:\s*true", re.IGNORECASE),
)

DEFAULT_THREATMODEL_TEMPLATE = """# THREATMODEL.md — Repository Security & Attack Surface Specification

> Governed by `CR-AGENTIC-SEC-001` (OpenAnt Constrained Attacker Persona & BITE Verification).

## Deployment & Runtime Mode
- **Mode**: `hybrid_cli_and_mcp`
- **Privilege Boundary**: Non-root operator execution; secrets isolated in external credential store.

## External Attack Surface
- **CLI Entrypoints**: `@click.command` and `@click.group` handlers accepting operator arguments.
- **MCP Tool Entrypoints**: `@mcp.tool` JSON-RPC handlers exposed over Streamable HTTP / stdio.
- **HTTP Routes**: FastAPI health, readiness, and API endpoints.

## Trusted vs. Untrusted Inputs
- **Trusted**: Local repository configuration (`cfg/*.yaml`) verified by SHA-256 hash manifest.
- **Untrusted**: External web payloads, third-party `SKILL.md` / plugin manifests, unverified RAG documents, and remote JSON-RPC tool arguments.

## Out-of-Scope Threat Assumptions
- `local_cli_only`: Attacks requiring pre-existing local root/shell compromise on the developer workstation.
- `assumes_admin_or_local_shell`: Findings that assume an attacker already controls local environment variables or OS process table.
"""


class ThreatModelBot:
    """Manages and validates `THREATMODEL.md` with fail-closed security semantics."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    @property
    def threatmodel_path(self) -> Path:
        return self.workspace_root / "THREATMODEL.md"

    def init_threatmodel(self, overwrite: bool = False) -> dict[str, Any]:
        path = self.threatmodel_path
        if path.exists() and not overwrite:
            return {"created": False, "path": str(path), "message": "THREATMODEL.md already exists"}
        path.write_text(DEFAULT_THREATMODEL_TEMPLATE, encoding="utf-8")
        return {"created": True, "path": str(path), "message": "Initialized canonical THREATMODEL.md"}

    def validate_threatmodel(self, path: Path | None = None) -> dict[str, Any]:
        """Fail-closed validation of THREATMODEL.md structure and policy constraints."""
        target = path or self.threatmodel_path
        if not target.exists():
            return {
                "valid": False,
                "fail_closed": True,
                "path": str(target),
                "errors": ["THREATMODEL.md does not exist (fail-closed default enforced)"],
            }
        try:
            content = target.read_text(encoding="utf-8")
        except OSError as exc:
            return {
                "valid": False,
                "fail_closed": True,
                "path": str(target),
                "errors": [f"Unable to read THREATMODEL.md: {exc}"],
            }

        errors: list[str] = []
        for section in REQUIRED_THREATMODEL_SECTIONS:
            if section not in content:
                errors.append(f"Missing required section: '{section}'")

        for pat in FORBIDDEN_PERMISSIVE_PATTERNS:
            if pat.search(content):
                errors.append(f"Overly permissive directive matched forbidden pattern: '{pat.pattern}'")

        return {
            "valid": len(errors) == 0,
            "fail_closed": len(errors) > 0,
            "path": str(target),
            "errors": errors,
        }


@click.group("threatmodel")
def threatmodel_cmd() -> None:
    """Initialize and validate repository THREATMODEL.md specifications."""


@threatmodel_cmd.command("init")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing THREATMODEL.md.")
@click.pass_context
def threatmodel_init(ctx: click.Context, overwrite: bool) -> None:
    """Scaffold canonical THREATMODEL.md in the current repository."""
    bot = ThreatModelBot(workspace_root=Path.cwd())
    res = bot.init_threatmodel(overwrite=overwrite)
    response = _build_response(ctx, command="threatmodel.init", state="ok", data=res)
    _emit_response(ctx, response, text_renderer=lambda: console.print(f"[green]✓ {res['message']}[/green] ({res['path']})"))


@threatmodel_cmd.command("validate")
@click.option("--path", "file_path", type=click.Path(), default=None, help="Optional path to THREATMODEL.md.")
@click.pass_context
def threatmodel_validate(ctx: click.Context, file_path: str | None) -> None:
    """Validate THREATMODEL.md with fail-closed checks for missing or permissive rules."""
    bot = ThreatModelBot(workspace_root=Path.cwd())
    res = bot.validate_threatmodel(Path(file_path) if file_path else None)
    state = "ok" if res["valid"] else "error"
    response = _build_response(ctx, command="threatmodel.validate", state=state, data=res)

    def _text() -> None:
        if res["valid"]:
            console.print(f"[bold green]✓ THREATMODEL.md Validated:[/bold green] {res['path']}")
        else:
            console.print(f"[bold red]✗ THREATMODEL.md Failed Fail-Closed Validation:[/bold red] {res['path']}")
            for err in res["errors"]:
                console.print(f"  • [red]{err}[/red]")

    _emit_response(ctx, response, text_renderer=_text)
    if not res["valid"]:
        ctx.exit(1)
