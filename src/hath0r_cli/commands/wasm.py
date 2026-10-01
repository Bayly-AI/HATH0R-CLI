"""WASM micro-runtime sandboxing command group for Hath0r CLI."""

from __future__ import annotations

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def wasm() -> None:
    """Manage capability-based WASM micro-runtime agent sandboxes."""
    pass


@wasm.command("run")
@click.argument("module_path", type=click.Path(exists=True))
@click.option("--allow-read", "-r", multiple=True, help="Granted filesystem read directory roots.")
@click.option("--allow-write", "-w", multiple=True, help="Granted filesystem write directory roots.")
@click.option("--allow-net", "-n", multiple=True, help="Granted network hosts.")
@click.option("--memory-mb", "-m", default=64, type=int, help="Memory ceiling cap in MB.")
@click.option("--fuel", "-f", default=100_000_000, type=int, help="Maximum execution fuel instruction limit.")
@click.option("--entry", "-e", default="_start", help="WASM entrypoint function.")
@click.pass_context
def wasm_run(
    ctx: click.Context,
    module_path: str,
    allow_read: tuple[str, ...],
    allow_write: tuple[str, ...],
    allow_net: tuple[str, ...],
    memory_mb: int,
    fuel: int,
    entry: str,
) -> None:
    """Execute a WASM binary inside the capability-governed sandbox."""
    from hath0r_cli.bots.wasm_runtime_bot import WasmCapabilities, WasmRuntimeBot

    caps = WasmCapabilities(
        allow_read=list(allow_read),
        allow_write=list(allow_write),
        allow_net=list(allow_net),
        max_memory_mb=memory_mb,
        fuel_limit=fuel,
    )

    bot = WasmRuntimeBot()
    res = bot.execute_module(module_path, capabilities=caps, entry_func=entry)

    response = _build_response(
        ctx,
        command="wasm.run",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("success"):
            console.print("Sandbox Execution Succeeded")
            console.print(f"[bold green]✓ WASM Executed ({res.get('engine')}, {res.get('latency_ms')}ms):[/bold green]")
            console.print(f"  • Module: {res.get('module_path')}")
            console.print(f"  • Fuel Consumed: {res.get('fuel_consumed')} / {fuel}")
            console.print(f"  • Memory Used: {res.get('memory_used_mb')} MB")
            console.print(f"\n[bold]Output:[/bold]\n{res.get('stdout')}")
        else:
            console.print(f"[bold red]✗ Sandbox Execution Failed:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@wasm.command("info")
@click.pass_context
def wasm_info(ctx: click.Context) -> None:
    """Display WebAssembly (WASI) runtime and sandbox engine capabilities."""
    from hath0r_cli.bots.wasm_runtime_bot import WasmRuntimeBot

    bot = WasmRuntimeBot()
    status = dict(bot.get_runtime_status())
    status["title"] = "HATH0R WebAssembly (WASI) Sandboxing"
    status["wasi_support"] = "WASI Support: Enabled"

    response = _build_response(
        ctx,
        command="wasm.info",
        state="ok",
        data=status,
    )

    def _text() -> None:
        console.print("[bold cyan]HATH0R WebAssembly (WASI) Sandboxing[/bold cyan]")
        console.print("  • WASI Support: Enabled")
        console.print(f"  • Active Engine: {status.get('engine')}")

    _emit_response(ctx, response, text_renderer=_text)




@wasm.command("validate")
@click.argument("module_path", type=click.Path(exists=True))
@click.pass_context
def wasm_validate(ctx: click.Context, module_path: str) -> None:
    """Validate a WASM binary header and format structure."""
    from hath0r_cli.bots.wasm_runtime_bot import WasmRuntimeBot

    bot = WasmRuntimeBot()
    res = bot.validate_module(module_path)

    response = _build_response(
        ctx,
        command="wasm.validate",
        state="ok" if res.get("valid") else "error",
        data=res,
    )

    def _text() -> None:
        if res.get("valid"):
            console.print(f"[bold green]✓ Valid WebAssembly Module:[/bold green] {module_path}")
            console.print(f"  • Size: {res.get('size_bytes')} bytes")
            console.print(f"  • WASM Version: {res.get('wasm_version')}")
        else:
            console.print(f"[bold red]✗ Invalid WASM Module:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@wasm.command("status")
@click.pass_context
def wasm_status(ctx: click.Context) -> None:
    """Display host WASM engine availability and capability security status."""
    from hath0r_cli.bots.wasm_runtime_bot import WasmRuntimeBot

    bot = WasmRuntimeBot()
    status = bot.get_runtime_status()

    response = _build_response(ctx, command="wasm.status", state="ok", data=status)

    def _text() -> None:
        console.print("[bold]Hath0r WASM Micro-Runtime Status:[/bold]")
        console.print(f"  • Active Engine: [cyan]{status['engine']}[/cyan]")
        console.print(f"  • Wasmtime Available: {'✓ Yes' if status['wasmtime_installed'] else '✗ No'}")
        console.print(f"  • Wasmer Available: {'✓ Yes' if status['wasmer_installed'] else '✗ No'}")
        console.print(f"  • Security Policy: [bold green]{status['capability_enforcement']}[/bold green]")
        console.print(f"  • Default Memory Limit: {status['default_memory_limit_mb']} MB")

    _emit_response(ctx, response, text_renderer=_text)


wasm_group = wasm
