"""HATH0R CLI interactive terminal user interface (TUI) command."""

from __future__ import annotations

import click
from rich.console import Console

from hath0r_cli.ui.tui_app import HathorTUIApp


@click.command("tui")
@click.option("--mode", "-m", type=click.Choice(["live", "snapshot"]), default="snapshot", help="Display mode.")
def tui_cmd(mode: str) -> None:
    """Launch the interactive terminal dashboard for cognitive and security status."""
    console = Console()
    app = HathorTUIApp(console=console)
    app.display()
