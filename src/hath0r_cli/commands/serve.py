"""HATH0R CLI embedded web dashboard server command."""

from __future__ import annotations

import time

import click
from rich.console import Console

from hath0r_cli.server.dashboard_server import HathorDashboardServer

console = Console()


@click.command("serve")
@click.option("--host", "-h", default="127.0.0.1", help="Host interface to bind HTTP server to.")
@click.option("--port", "-p", default=8080, type=int, help="Port to bind HTTP server to.")
@click.option("--daemon", "-d", is_flag=True, default=False, help="Run as background daemon process.")
def serve_cmd(host: str, port: int, daemon: bool) -> None:
    """Launch embedded lightweight web dashboard and SSE agent event stream."""
    server = HathorDashboardServer(host=host, port=port)
    console.print(f"[bold green]Starting HATH0R Web Dashboard[/bold green] at [cyan]http://{host}:{port}[/cyan]")
    console.print("[dim]Serving real-time telemetry, cognitive graphs, and SSE event stream.[/dim]")

    server.start(daemon=True)

    if daemon:
        console.print("[green]Server running in background daemon thread.[/green]")
        return

    console.print("[dim]Press Ctrl+C to terminate dashboard server.[/dim]")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down dashboard server...[/yellow]")
        server.stop()
        console.print("[green]Server stopped.[/green]")
