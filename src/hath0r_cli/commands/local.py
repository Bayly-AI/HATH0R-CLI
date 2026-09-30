"""HATH0R CLI local model management and offline inference commands."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli.bots.local_model import LocalModelBot

console = Console()


@click.group("local")
def local_group() -> None:
    """Manage offline local LLM runtimes, Ollama, and Apple MLX acceleration."""
    pass


@local_group.command("status")
@click.option("--url", default="http://localhost:11434", help="Ollama endpoint URL.")
def local_status(url: str) -> None:
    """Display host acceleration status, Ollama daemon, and local model weights."""
    bot = LocalModelBot(ollama_url=url)
    status = bot.detect_hardware()

    table = Table(title="HATH0R Local Hardware & LLM Runtimes")
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Details", style="green")
    table.add_column("Status", style="bold")

    table.add_row("Operating System", f"{status.os_name} ({status.architecture})", "[green]detected[/green]")
    table.add_row(
        "Apple Silicon (Metal)",
        "Unified Memory GPU" if status.has_metal else "Not applicable",
        "[green]active[/green]" if status.has_metal else "[dim]unavailable[/dim]",
    )
    table.add_row(
        "NVIDIA CUDA",
        "CUDA GPU Core" if status.has_cuda else "Not detected",
        "[green]active[/green]" if status.has_cuda else "[dim]unavailable[/dim]",
    )
    table.add_row(
        "Apple MLX (mlx-lm)",
        "Metal optimized local inference" if status.mlx_available else "Package not installed",
        "[green]installed[/green]" if status.mlx_available else "[yellow]optional[/yellow]",
    )
    table.add_row(
        "Ollama Daemon",
        status.ollama_url,
        "[green]running[/green]" if status.ollama_running else "[yellow]offline[/yellow]",
    )
    table.add_row(
        "Installed Local Models",
        ", ".join(status.installed_models) if status.installed_models else "None detected",
        f"[cyan]{len(status.installed_models)} models[/cyan]",
    )

    console.print(table)


@local_group.command("list")
@click.option("--url", default="http://localhost:11434", help="Ollama endpoint URL.")
def local_list(url: str) -> None:
    """List all downloaded local LLM model weights."""
    bot = LocalModelBot(ollama_url=url)
    running, models = bot.check_ollama()
    if not running:
        console.print("[yellow]Ollama server is offline at[/yellow] [cyan]" + url + "[/cyan]")
        console.print("Start Ollama or install models with [bold]ollama run llama3.2[/bold]")
        return

    if not models:
        console.print("[yellow]No local models found on Ollama server.[/yellow]")
        return

    table = Table(title="Installed Local LLM Models")
    table.add_column("Model Name", style="cyan")
    table.add_column("Runtime", style="green")

    for m in models:
        table.add_row(m, "Ollama Local")

    console.print(table)


@local_group.command("run")
@click.argument("prompt")
@click.option("--model", "-m", default="llama3.2", help="Local model name.")
@click.option("--url", default="http://localhost:11434", help="Ollama endpoint URL.")
@click.option("--system", "-s", default=None, help="System prompt context.")
@click.option("--temperature", "-t", default=0.7, type=float, help="Sampling temperature.")
def local_run(prompt: str, model: str, url: str, system: str | None, temperature: float) -> None:
    """Execute local inference against Ollama or offline fallback."""
    bot = LocalModelBot(ollama_url=url)
    with console.status(f"[bold green]Running local inference ({model})...[/bold green]"):
        result = bot.generate(prompt=prompt, model=model, system=system, temperature=temperature)

    console.print(f"\n[bold cyan]Model:[/bold cyan] {result['model']} [dim]({result['backend']})[/dim]")
    console.print(
        f"[bold cyan]Latency:[/bold cyan] {result['latency_seconds']}s | [bold cyan]Speed:[/bold cyan] {result['tokens_per_second']} tok/s"
    )
    console.print(
        f"[bold cyan]Tokens:[/bold cyan] Prompt: {result['prompt_tokens']}, Completion: {result['completion_tokens']}"
    )
    console.print("\n[bold green]Response:[/bold green]")
    console.print(result["response"])
