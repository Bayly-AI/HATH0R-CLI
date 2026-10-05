"""GAIN Federated Agent-to-Agent (A2A) Mesh CLI Group for Hath0r."""

from __future__ import annotations

import json
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..bots.mesh_manager_bot import mesh_manager_bot

console = Console()


@click.group("mesh", help="GAIN Federated Agent-to-Agent (A2A) Mesh Subsystem.")
def mesh_cmd() -> None:
    """GAIN federated mesh command group."""
    pass


@mesh_cmd.command("status", help="Inspect local GAIN mesh node and peer network status.")
@click.option("--json", "as_json", is_flag=True, help="Output status as JSON.")
def mesh_status(as_json: bool) -> None:
    """Inspect local mesh node status."""
    st = mesh_manager_bot.status()
    if as_json:
        click.echo(json.dumps(st, indent=2))
        return

    table = Table(title="GAIN Mesh Node Status Diagnostics", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="green")

    table.add_row("Node Status", str(st.get("status")))
    table.add_row("Bot Name", str(st.get("bot_name")))
    table.add_row("Local Agent ID", str(st.get("local_agent_id")))
    table.add_row("Peer Count", str(st.get("peer_count")))
    table.add_row("Journal Length", str(st.get("journal_length")))
    table.add_row("Supported Intents", ", ".join(st.get("supported_intents", [])))

    console.print(table)


@mesh_cmd.command("peers", help="List registered peer agent nodes in the federation mesh.")
@click.option("--json", "as_json", is_flag=True, help="Output peers as JSON.")
def mesh_peers(as_json: bool) -> None:
    """List registered peers."""
    peers = mesh_manager_bot.list_peers()
    if as_json:
        click.echo(json.dumps(peers, indent=2))
        return

    table = Table(title=f"GAIN Mesh Registered Peers ({len(peers)})", border_style="magenta")
    table.add_column("Peer ID", style="bold cyan")
    table.add_column("Endpoint", style="white")
    table.add_column("Capabilities", style="yellow")
    table.add_column("Last Seen", style="green")

    for p in peers:
        table.add_row(
            str(p.get("peer_id")),
            str(p.get("endpoint")),
            ", ".join(p.get("capabilities", [])),
            str(p.get("last_seen")),
        )

    console.print(table)


@mesh_cmd.command("ping", help="Ping a peer node to verify cryptographic signature health.")
@click.option("--peer-id", required=True, help="Target peer node ID.")
@click.option("--json", "as_json", is_flag=True, help="Output ping result as JSON.")
def mesh_ping(peer_id: str, as_json: bool) -> None:
    """Ping peer node."""
    res = mesh_manager_bot.ping_peer(peer_id)
    if as_json:
        click.echo(json.dumps(res, indent=2))
        return

    status = res.get("status", "UNKNOWN")
    color = "green" if status == "ONLINE" else "red"
    console.print(
        Panel(
            f"[bold cyan]Peer ID:[/bold cyan] {res.get('peer_id')}\n"
            f"[bold cyan]Status:[/bold cyan] [{color}]{status}[/{color}]\n"
            f"[bold cyan]Latency:[/bold cyan] {res.get('latency_ms')} ms\n"
            f"[bold cyan]Envelope ID:[/bold cyan] {res.get('envelope_id')}\n"
            f"[bold cyan]HMAC Verified:[/bold cyan] {'✅ Yes' if res.get('signature_verified') else '❌ No'}",
            title="[bold yellow]GAIN Mesh Peer Ping Diagnostic[/bold yellow]",
            border_style=color,
        )
    )


@mesh_cmd.command("route", help="Route cross-workspace AgentGraph query through GAIN mesh.")
@click.option("--peer-id", required=True, help="Target peer node ID.")
@click.option("--query", required=True, help="Topic query string.")
def mesh_route(peer_id: str, query: str) -> None:
    """Route query to peer node."""
    res = mesh_manager_bot.route_query(peer_id=peer_id, topic_query=query)
    click.echo(json.dumps(res, indent=2))


@mesh_cmd.command("bot-run", help="Execute MeshManagerBot conversational query.")
@click.argument("intent_text")
def mesh_bot_run(intent_text: str) -> None:
    """Run MeshManagerBot conversational query."""
    res = mesh_manager_bot.handle_conversational_intent(intent_text)
    click.echo(json.dumps(res, indent=2))
