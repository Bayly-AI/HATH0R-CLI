"""ATC (Air Traffic Control) commands for HATH0R CLI."""

from __future__ import annotations

import sys

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
@click.option("--container", is_flag=True, default=False, help="Install and start ATC shared Docker stack.")
@click.option("--image-url", default=None, help="Remote container image URL (if not supplied, falls back to local git build).")
@click.option("--prompt/--no-prompt", "interactive_prompt", default=True, help="Prompt operator for container image URL.")
@click.pass_context
def atc_install(
    ctx: click.Context,
    tag_or_version: str | None,
    container: bool,
    image_url: str | None,
    interactive_prompt: bool,
) -> None:
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

        c_res = bot.install_container("hath0r-atc", container_url=final_url)
        res["container"] = c_res
        if not c_res.get("success"):
            diagnostics.append(
                Diagnostic(
                    code="ATC_CONTAINER_FAILED",
                    message=str(c_res.get("error", "Container deployment failed.")),
                    severity="error",
                    remediation="Check Docker daemon or local compose configuration.",
                    provenance={"component": "hath0r-cli", "operation": "atc.install"},
                )
            )
            state = "error"

    response = _build_response(ctx, command="atc.install", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if res.get("success"):
            action = "Already installed" if res.get("already_installed") else "Successfully installed"
            console.print(f"[bold green]✓ {action}:[/bold green] {res.get('name')} at {res.get('path')}")
            if res.get("version"):
                console.print(f"  Version: [bold cyan]{res.get('version')}[/bold cyan]")
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


@atc.command("container")
@click.option("--image-url", default=None, help="Remote container image URL (if not supplied, falls back to local git build).")
@click.option("--prompt/--no-prompt", "interactive_prompt", default=True, help="Prompt operator for container image URL.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate container setup.")
@click.pass_context
def atc_container(
    ctx: click.Context,
    image_url: str | None,
    interactive_prompt: bool,
    dry_run: bool,
) -> None:
    """Deploy HATH0R ATC container stack. Prompts for container URL; falls back to local git build if not supplied."""
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

    res = bot.install_container("hath0r-atc", container_url=final_url, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    diagnostics: list[Diagnostic] = []
    if not res.get("success"):
        diagnostics.append(
            Diagnostic(
                code="ATC_CONTAINER_FAILED",
                message=str(res.get("error", "Failed to deploy ATC container stack.")),
                severity="error",
                remediation="Ensure Docker daemon is running or verify image URL.",
                provenance={"component": "hath0r-cli", "operation": "atc.container"},
            )
        )

    response = _build_response(ctx, command="atc.container", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if res.get("success"):
            if res.get("dry_run"):
                console.print(f"[bold yellow][DRY-RUN][/bold yellow] {res.get('action')}")
            else:
                source = "remote URL" if res.get("source") == "remote_url" else "local git version"
                console.print(f"[bold green]✓ HATH0R ATC container stack deployed from {source}.[/bold green]")
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

