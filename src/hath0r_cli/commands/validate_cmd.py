"""HATH0R CLI command to validate and verify UI, Script, and Text changes."""

from __future__ import annotations

from typing import Tuple

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli.bots.change_validation import ChangeValidationBot

console = Console()


@click.command("validate-change")
@click.argument("files", nargs=-1, type=str)
def validate_change_cmd(files: Tuple[str, ...]) -> None:
    """Validate and verify UI, Script, and Text changes before task completion announcement."""
    bot = ChangeValidationBot()
    file_list = list(files) if files else None

    console.print("[bold cyan]Running Change Validation Gate...[/bold cyan]")
    res = bot.validate_all(files=file_list)

    if res["status"] == "valid":
        summary = res.get("summary", {})
        table = Table(title="Validation Gate Summary", border_style="green")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="bold green")

        table.add_row("Total Files Inspected", str(summary.get("total_files", 0)))
        table.add_row("UI Assets Verified", str(summary.get("ui_files", 0)))
        table.add_row("Scripts / Code Verified", str(summary.get("script_files", 0)))
        table.add_row("Text / Configs Verified", str(summary.get("text_files", 0)))

        console.print(table)
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
    else:
        console.print("[bold red]✗ Validation Gate Failed![/bold red]")
        for err in res.get("errors", []):
            console.print(f"  [red]• {err}[/red]")
        console.print(f"\n[yellow]Remediation: {res.get('remediation_hint')}[/yellow]")
        raise click.ClickException("Validation failed. Please resolve errors before task completion.")
