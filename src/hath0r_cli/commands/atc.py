"""ATC (Air Traffic Control) commands for HATH0R CLI."""

from __future__ import annotations

from typing import Any

import click
from rich.table import Table

from hath0r_cli.bots.sibling_bot import SiblingManagerBot
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)
from hath0r_cli.envelope import Diagnostic


@click.group()
def atc() -> None:
    """Air Traffic Control (ATC): control tower infrastructure, observation, and Docker-group services."""


@atc.command("status")
@click.pass_context
def atc_status(ctx: click.Context) -> None:
    """Check ATC repository presence, version, and infrastructure status."""
    bot = SiblingManagerBot()
    root = bot.resolve_group_root()
    sibling_path = bot.locate_sibling("hath0r-atc", root)
    installed = sibling_path is not None
    version = bot.get_local_version(sibling_path) if sibling_path else None

    state = "ok" if installed else "error"
    diagnostics: list[Diagnostic] = []
    if not installed:
        diagnostics.append(
            Diagnostic(
                code="ATC_SIBLING_NOT_FOUND",
                message="HATH0R ATC is not installed as a sibling of CLI.",
                severity="error",
                remediation="Run 'hath0r atc install' or 'hath0r repo install hath0r-atc' to download and install.",
                provenance={"component": "hath0r-cli", "operation": "atc.status"},
                details={"expected_root": str(root / "hath0r-atc")},
            )
        )

    data = {
        "installed": installed,
        "product_id": "hath0r-atc",
        "path": str(sibling_path) if sibling_path else str(root / "hath0r-atc"),
        "version": version,
    }

    response = _build_response(ctx, command="atc.status", state=state, data=data, diagnostics=diagnostics)

    def _text() -> None:
        table = Table(title="HATH0R ATC Status")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Installed", "[green]Yes[/green]" if installed else "[red]No[/red]")
        table.add_row("Path", str(sibling_path) if sibling_path else str(root / "hath0r-atc"))
        table.add_row("Version", version or "Unknown")

        console.print(table)
        if not installed:
            console.print("\n[bold yellow]Offer:[/bold yellow] HATH0R ATC is not available locally.")
            console.print("Run [bold green]hath0r atc install[/bold green] to download and install it as a sibling.")

    _emit_response(ctx, response, text_renderer=_text)
    if not installed:
        ctx.exit(6)


@atc.command("install")
@click.option("--version", "tag_or_version", default=None, help="Specific version or tag to download.")
@click.pass_context
def atc_install(ctx: click.Context, tag_or_version: str | None) -> None:
    """Download the latest version of HATH0R ATC and install as a sibling of CLI."""
    bot = SiblingManagerBot()
    res = bot.download_and_install("hath0r-atc", version=tag_or_version)

    state = "ok" if res.get("success") else "error"
    diagnostics: list[Diagnostic] = []
    if not res.get("success"):
        diagnostics.append(
            Diagnostic(
                code="ATC_INSTALL_FAILED",
                message=str(res.get("error", "Failed to download and install HATH0R ATC.")),
                severity="error",
                remediation="Check internet connection, GitHub credentials, or run git clone manually.",
                provenance={"component": "hath0r-cli", "operation": "atc.install"},
            )
        )

    response = _build_response(ctx, command="atc.install", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if res.get("success"):
            action = "Already installed" if res.get("already_installed") else "Successfully installed"
            console.print(f"[bold green]✓ {action}:[/bold green] {res.get('name')} at {res.get('path')}")
            if res.get("version"):
                console.print(f"  Version: [bold cyan]{res.get('version')}[/bold cyan]")
        else:
            console.print(f"[bold red]✗ Installation failed:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
