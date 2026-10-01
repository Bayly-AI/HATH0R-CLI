"""Doctor command for HATH0R CLI."""

from __future__ import annotations

import click
from rich.table import Table

from hath0r_cli import __version__
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    _group_root,
    _kb_path,
    console,
)
from hath0r_cli.doctor import diagnostics_for, run_checks
from hath0r_cli.envelope import Diagnostic


@click.command()
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
@click.option(
    "--vision",
    "check_vision",
    is_flag=True,
    default=False,
    help="Include Vision Transformer backend and configuration checks.",
)
@click.pass_context
def doctor(ctx: click.Context, check_mcp: bool, check_factories: bool, check_vision: bool) -> None:
    """Check group paths, control tower, member repos, and KB hub presence."""
    root = _group_root()
    kb = _kb_path()
    verbose = bool(ctx.obj.get("verbose", False))
    result = run_checks(
        root,
        kb,
        check_mcp=check_mcp,
        check_factories=check_factories,
        check_vision=check_vision,
    )

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
