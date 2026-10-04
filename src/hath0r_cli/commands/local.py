"""Local reasoning and coding model command group for Hath0r CLI."""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group()
def local() -> None:
    """Manage local offline LLM reasoning (DeepSeek-R1) and coding (Qwen2.5-Coder) engines."""
    pass


@local.command("status")
@click.pass_context
def local_status(ctx: click.Context) -> None:
    """Inspect local hardware acceleration and installed Ollama models."""
    from hath0r_cli.bots.local_model import LocalModelBot

    bot = LocalModelBot()
    status = bot.detect_hardware()

    response = _build_response(
        ctx,
        command="local.status",
        state="ok",
        data={
            "title": "HATH0R Local Hardware & LLM Runtimes",
            "operating_system": f"Operating System: {status.os_name} ({status.architecture})",
            "os_name": status.os_name,
            "architecture": status.architecture,
            "has_metal": status.has_metal,
            "has_cuda": status.has_cuda,
            "ollama_running": status.ollama_running,
            "installed_models": status.installed_models,
            "mlx_available": status.mlx_available,
        },
    )

    def _text() -> None:
        console.print("[bold cyan]HATH0R Local Hardware & LLM Runtimes[/bold cyan]")
        console.print(f"  • Operating System: {status.os_name} ({status.architecture})")
        console.print(f"  • Metal (Apple Silicon): {'✓ Enabled' if status.has_metal else '✗ Disabled'}")
        console.print(f"  • CUDA (NVIDIA): {'✓ Enabled' if status.has_cuda else '✗ Disabled'}")
        console.print(f"  • MLX Acceleration: {'✓ Available' if status.mlx_available else '✗ Not Available'}")
        console.print(
            f"  • Ollama Server: {'✓ Online' if status.ollama_running else '✗ Offline'} ({status.ollama_url})"
        )
        if status.installed_models:
            console.print(f"  • Installed Models: {', '.join(status.installed_models)}")

    _emit_response(ctx, response, text_renderer=_text)


@local.command("run")
@click.argument("prompt")
@click.option("--model", "-m", "model_name", default="llama3.2", help="Model name.")
@click.pass_context
def local_run(ctx: click.Context, prompt: str, model_name: str) -> None:
    """Run local inference using Ollama or simulated fallback."""
    from hath0r_cli.bots.local_model import LocalModelBot

    bot = LocalModelBot()
    res = bot.generate(prompt=prompt, model=model_name)
    res_data = dict(res)
    res_data["Model:"] = model_name
    res_data["Response:"] = res.get("response", "")

    response = _build_response(
        ctx,
        command="local.run",
        state="ok" if res.get("status") in ("success", "simulated") else "error",
        data=res_data,
    )

    def _text() -> None:
        console.print(f"Model: {model_name}")
        console.print(f"Response:\n{res.get('response', '')}")

    _emit_response(ctx, response, text_renderer=_text)


@local.command("reason")
@click.argument("prompt")
@click.option(
    "--model",
    "-m",
    "model_name",
    type=click.Choice(["deepseek-r1:7b", "deepseek-r1:1.5b", "deepseek-r1:14b"]),
    default="deepseek-r1:7b",
    help="Target reasoning model identifier.",
)
@click.option("--show-cot", is_flag=True, default=False, help="Display internal Chain-of-Thought thinking trace.")
@click.option("--offline", is_flag=True, default=False, help="Force offline deterministic simulation.")
@click.pass_context
def local_reason(
    ctx: click.Context,
    prompt: str,
    model_name: str,
    show_cot: bool,
    offline: bool,
) -> None:
    """Execute deep reasoning task using DeepSeek-R1 with CoT extraction."""
    from hath0r_cli.bots.local_model_bot import LocalModelBot

    bot = LocalModelBot()
    res = bot.reason(prompt=prompt, model=model_name, force_offline=offline)

    response = _build_response(
        ctx,
        command="local.reason",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        console.print(
            f"[bold green]✓ Reasoning Complete ({res.get('engine')}, {res.get('latency_ms')}ms):[/bold green]"
        )
        if show_cot and res.get("thinking_trace"):
            console.print(
                Panel(
                    res.get("thinking_trace", ""),
                    title="[bold yellow]Chain-of-Thought (<think>)[/bold yellow]",
                    border_style="yellow",
                )
            )
        console.print(
            Panel(
                res.get("response", ""),
                title=f"[bold cyan]Answer ({model_name})[/bold cyan]",
                border_style="cyan",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)


@local.command("code")
@click.argument("prompt")
@click.option(
    "--model",
    "-m",
    "model_name",
    type=click.Choice(["qwen2.5-coder:7b", "qwen2.5-coder:1.5b", "qwen2.5-coder:14b"]),
    default="qwen2.5-coder:7b",
    help="Target code generation model identifier.",
)
@click.option("--language", "-l", default="python", help="Target programming language.")
@click.option("--offline", is_flag=True, default=False, help="Force offline deterministic simulation.")
@click.pass_context
def local_code(
    ctx: click.Context,
    prompt: str,
    model_name: str,
    language: str,
    offline: bool,
) -> None:
    """Generate production-grade code using Qwen2.5-Coder."""
    from hath0r_cli.bots.local_model_bot import LocalModelBot

    bot = LocalModelBot()
    res = bot.generate_code(prompt=prompt, model=model_name, language=language, force_offline=offline)

    response = _build_response(
        ctx,
        command="local.code",
        state="ok" if res.get("success") else "error",
        data=res,
    )

    def _text() -> None:
        console.print(
            f"[bold green]✓ Code Generation Complete ({res.get('engine')}, {res.get('latency_ms')}ms):[/bold green]"
        )
        console.print(res.get("code", ""))

    _emit_response(ctx, response, text_renderer=_text)


@local.command("models")
@click.pass_context
def local_models(ctx: click.Context) -> None:
    """List supported local reasoning and coding model architectures."""
    from hath0r_cli.bots.local_model_bot import LocalModelBot

    bot = LocalModelBot()
    models = bot.list_models()

    response = _build_response(
        ctx,
        command="local.models",
        state="ok",
        data={"models": models, "count": len(models)},
    )

    def _text() -> None:
        table = Table(title="Supported Local LLM Architectures")
        table.add_column("Model ID", style="cyan")
        table.add_column("Family", style="magenta")
        table.add_column("CoT (<think>)", style="yellow")
        table.add_column("Description", style="white")

        for m in models:
            table.add_row(
                m["model_id"],
                m["family"],
                "✓ Enabled" if m["cot_enabled"] else "✗ Standard",
                m["description"],
            )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


local_group = local
