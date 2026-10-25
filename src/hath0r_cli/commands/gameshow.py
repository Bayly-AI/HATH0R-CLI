"""Gameshow Continuous Calibration & Evaluation CLI commands for HATH0R."""

from __future__ import annotations

import os
from typing import Optional

import click
from rich.table import Table

from hath0r_cli.bots.gameshow_bot import HathorGameshowBot
from hath0r_cli.common import _build_response, _emit_response, console


@click.group("gameshow")
def gameshow_cmd() -> None:
    """Gameshow Continuous Calibration (CAG/RAG) tournament benchmark commands."""
    pass


@gameshow_cmd.command("status")
@click.option("--cache", default=None, help="Path to cag_calibration_cache.json")
@click.option("--deck", default=None, help="Path to tournament_deck.json")
@click.pass_context
def gameshow_status(ctx: click.Context, cache: Optional[str], deck: Optional[str]) -> None:
    """Display current active CAG calibration memories and deck status."""
    bot = HathorGameshowBot(deck_path=deck, cache_path=cache)
    if deck and os.path.exists(deck):
        bot.initialize_deck(deck)

    data = {
        "calibrated_memories_count": bot.calibration.count,
        "similarity_threshold": bot.calibration.similarity_threshold,
        "cache_file": bot.cache_file,
        "deck_file": bot.deck_file,
        "total_cards": len(bot.deck_state.cards) if bot.deck_state else 0,
        "completed_rounds": len(bot.deck_state.rounds) if bot.deck_state else 0,
    }

    response = _build_response(ctx, command="gameshow.status", state="ok", data=data)

    def _text() -> None:
        console.print("\n[bold cyan]⚡ HATH0R Gameshow CAG Calibration Status[/bold cyan]\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Active Calibrated Memories", str(data["calibrated_memories_count"]))
        table.add_row("Similarity Threshold", f"{data['similarity_threshold']:.2f}")
        table.add_row("Cache File Path", str(data["cache_file"]))
        table.add_row("Total Deck Cards", str(data["total_cards"]))
        table.add_row("Completed Rounds", str(data["completed_rounds"]))
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@gameshow_cmd.command("calibrate")
@click.option("--deck", required=True, help="Path to evaluation deck JSON file")
@click.option("--output", default=None, help="Output path for calibrated cache JSON")
@click.option("--threshold", default=0.85, type=float, help="Tokenized Jaccard similarity threshold")
@click.pass_context
def gameshow_calibrate(ctx: click.Context, deck: str, output: Optional[str], threshold: float) -> None:
    """Ingest evaluation cards from deck directly into CAG calibration registry."""
    bot = HathorGameshowBot(deck_path=deck, cache_path=output, similarity_threshold=threshold)
    deck_state = bot.initialize_deck(deck)

    added = 0
    if deck_state and deck_state.cards:
        cards_list = list(deck_state.cards.values())
        added = bot.calibration.calibrate_cards(cards_list)
        bot.calibration.save_to_disk()

    data = {
        "cards_ingested": added,
        "total_calibrated": bot.calibration.count,
        "cache_file": bot.cache_file,
    }

    response = _build_response(ctx, command="gameshow.calibrate", state="ok", data=data)

    def _text() -> None:
        console.print("\n[bold green]✓ Gameshow CAG Calibration Complete[/bold green]")
        console.print(f"Cards Ingested: [bold cyan]{added:,}[/bold cyan]")
        console.print(f"Total Active Memories: [bold yellow]{bot.calibration.count:,}[/bold yellow]")
        console.print(f"Cache File: [bold white]{bot.cache_file}[/bold white]\n")

    _emit_response(ctx, response, text_renderer=_text)


@gameshow_cmd.command("report")
@click.option("--deck", required=True, help="Path to tournament deck JSON file")
@click.option("--output", default=None, help="Path to output markdown report file")
@click.pass_context
def gameshow_report(ctx: click.Context, deck: str, output: Optional[str]) -> None:
    """Generate accuracy and calibration progression report from tournament deck."""
    bot = HathorGameshowBot(deck_path=deck)
    bot.initialize_deck(deck)
    report_text = bot.generate_report(output_path=output)

    data = {
        "report_length": len(report_text),
        "output_file": output,
    }

    response = _build_response(ctx, command="gameshow.report", state="ok", data=data)

    def _text() -> None:
        console.print(report_text)

    _emit_response(ctx, response, text_renderer=_text)
