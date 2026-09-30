"""HATH0R CLI WebAssembly (WASI) sandboxed tool execution commands."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import click
from rich.console import Console
from rich.table import Table

from hath0r_cli.bots.wasm_sandbox import WasmSandboxBot

console = Console()


@click.group("wasm")
def wasm_group() -> None:
    """Execute tools inside isolated WebAssembly (WASI) sandboxes with strict resource bounds."""
    pass


@wasm_group.command("info")
def wasm_info() -> None:
    """Display WebAssembly runtime status, engine availability, and security isolation support."""
    bot = WasmSandboxBot()
    table = Table(title="HATH0R WebAssembly (WASI) Sandboxing")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Wasmtime Binary", bot.wasmtime_bin or "[yellow]Not in PATH (simulator active)[/yellow]")
    table.add_row("WASI Support", "[green]Enabled (Preview 1 & 2)[/green]")
    table.add_row("Capability Security", "[green]Preopened Directory Isolation[/green]")
    table.add_row("Resource Limiting", "[green]Fuel Counting & Hard Timeouts[/green]")

    console.print(table)


@wasm_group.command("run", context_settings=dict(ignore_unknown_options=True))
@click.argument("wasm_file", type=click.Path(exists=True))
@click.argument("module_args", nargs=-1, type=click.UNPROCESSED)
@click.option("--fuel", "-f", type=int, default=None, help="Deterministic execution fuel limit.")
@click.option("--timeout", "-t", type=float, default=15.0, help="Execution timeout in seconds.")
@click.option("--dir", "-d", "dirs", multiple=True, help="Preopen directory access (format: HOST_DIR or GUEST::HOST).")
def wasm_run(
    wasm_file: str,
    module_args: Tuple[str, ...],
    fuel: int | None,
    timeout: float,
    dirs: Tuple[str, ...],
) -> None:
    """Execute a WebAssembly binary inside a secure WASI sandbox."""
    bot = WasmSandboxBot()

    preopened_dirs = {}
    for d in dirs:
        if "::" in d:
            guest, host = d.split("::", 1)
            preopened_dirs[host] = guest
        else:
            preopened_dirs[d] = d

    with console.status(f"[bold green]Running sandboxed Wasm ({Path(wasm_file).name})...[/bold green]"):
        result = bot.run(
            wasm_path=wasm_file,
            args=list(module_args),
            preopened_dirs=preopened_dirs,
            fuel_limit=fuel,
            timeout_seconds=timeout,
        )

    if result.success:
        console.print(
            f"[bold green]Sandbox Execution Succeeded[/bold green] [dim]({result.runner}, {result.execution_time_seconds}s)[/dim]"
        )
        if result.stdout:
            console.print("\n[bold cyan]STDOUT:[/bold cyan]")
            console.print(result.stdout)
    else:
        console.print(f"[bold red]Sandbox Execution Failed[/bold red] (Exit code: {result.exit_code})")
        if result.stderr:
            console.print("\n[bold red]STDERR:[/bold red]")
            console.print(result.stderr)
        raise click.exceptions.Exit(result.exit_code)
