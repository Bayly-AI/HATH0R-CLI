"""Vision Transformers (ViT) & Multimodal Pipeline commands for Hath0r CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("vision")
def vision() -> None:
    """Vision Transformers (ViT), PyTorch Acceleration & Multimodal tools."""


@vision.command("inspect")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--prompt", default=None, help="Custom inspection prompt or question.")
@click.option("--device", type=click.Choice(["auto", "mps", "cuda", "cpu"], case_sensitive=False), default=None, help="Compute device for neural acceleration.")
@click.pass_context
def vision_inspect(ctx: click.Context, image_path: Path, prompt: str | None, device: str | None) -> None:
    """Inspect an image or screenshot using Vision Transformers."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.inspect_image(image_path=image_path, prompt=prompt, device=device)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.inspect", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            dev_str = f" [{res.get('device')}]" if res.get("device") else ""
            console.print(f"[bold green]✓ Vision Inspection Completed[/bold green] ({res.get('provider')}/{res.get('model')}{dev_str})")
            meta = res.get("image_metadata", {})
            console.print(f"  [dim]File:[/] {res.get('image_path')} ({meta.get('width')}x{meta.get('height')} {meta.get('format')})")
            console.print(f"  [bold]Summary:[/] {res.get('description')}")
            objs = res.get("detected_objects", [])
            if objs:
                console.print(f"  [dim]Detected {len(objs)} objects/regions.[/]")
        else:
            console.print(f"[bold red]✗ Vision Inspection Failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@vision.command("parse-doc")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--prompt", default=None, help="Extraction directives or target sections.")
@click.option("--device", type=click.Choice(["auto", "mps", "cuda", "cpu"], case_sensitive=False), default=None, help="Compute device for neural acceleration.")
@click.pass_context
def vision_parse_doc(ctx: click.Context, image_path: Path, prompt: str | None, device: str | None) -> None:
    """Parse visual documents, architecture diagrams, charts, and structured layouts."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.parse_document(image_path=image_path, prompt=prompt, device=device)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.parse_doc", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            dev_str = f" [{res.get('device')}]" if res.get("device") else ""
            console.print(f"[bold green]✓ Document Layout Parsed[/bold green] ({res.get('provider')}{dev_str})")
            doc = res.get("document_structure", {})
            console.print(f"  [bold]Type:[/] {doc.get('doc_type')}")
            for sec in doc.get("sections", []):
                console.print(f"    • {sec}")
            console.print(f"\n{res.get('extracted_text')}")
        else:
            console.print(f"[bold red]✗ Document Parsing Failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@vision.command("ground")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--target", "-t", required=True, help="Description of UI element or region to locate.")
@click.option("--device", type=click.Choice(["auto", "mps", "cuda", "cpu"], case_sensitive=False), default=None, help="Compute device for neural acceleration.")
@click.pass_context
def vision_ground(ctx: click.Context, image_path: Path, target: str, device: str | None) -> None:
    """Ground a UI element description to coordinate bounding boxes."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.ground_element(image_path=image_path, target=target, device=device)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.ground", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            grounded = res.get("grounded_target", {})
            coords = grounded.get("center_coordinates", {})
            bbox = grounded.get("bounding_box", [])
            dev_str = f" [{grounded.get('device')}]" if grounded.get("device") else ""
            console.print(f"[bold green]✓ Element Grounded:[/] '{target}'{dev_str}")
            console.print(f"  [bold]Center Coordinates:[/] ({coords.get('x')}, {coords.get('y')}) px")
            console.print(f"  [dim]Normalized Bounding Box:[/] {bbox}")
        else:
            console.print(f"[bold red]✗ Grounding Failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@vision.command("embed")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--device", type=click.Choice(["auto", "mps", "cuda", "cpu"], case_sensitive=False), default=None, help="Compute device for neural acceleration.")
@click.option("--precision", type=click.Choice(["fp32", "fp16", "int8"], case_sensitive=False), default="fp32", help="Tensor computation precision mode.")
@click.pass_context
def vision_embed(ctx: click.Context, image_path: Path, device: str | None, precision: str) -> None:
    """Extract multimodal cross-modal vector embedding for an image."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.embed_visual(image_path=image_path, device=device)
    state = "ok" if res.get("success") else "error"
    res["precision"] = precision
    response = _build_response(ctx, command="vision.embed", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            emb = res.get("embedding", [])
            dev_str = f" [{res.get('device')}/{precision}]" if res.get("device") else f" [{precision}]"
            console.print(f"[bold green]✓ Multimodal Embedding Generated[/bold green] ({len(emb)} dimensions, model: {res.get('model')}{dev_str})")
            console.print(f"  [dim]Vector snippet:[/] [{', '.join(str(x) for x in emb[:5])}, ...]")
        else:
            console.print(f"[bold red]✗ Embedding Failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@vision.command("rerank")
@click.option("--query", "-q", required=True, help="Query string for semantic reranking.")
@click.option("--candidate", "-c", "candidates", multiple=True, required=True, help="Candidate passages/entities to rank (specify multiple times).")
@click.option("--device", type=click.Choice(["auto", "mps", "cuda", "cpu"], case_sensitive=False), default=None, help="Compute device for neural acceleration.")
@click.option("--precision", type=click.Choice(["fp32", "fp16", "int8"], case_sensitive=False), default="fp32", help="Tensor computation precision mode.")
@click.pass_context
def vision_rerank(ctx: click.Context, query: str, candidates: Tuple[str, ...], device: str | None, precision: str) -> None:
    """Score and rank candidate passages against a query using neural cross-encoders."""
    from hath0r_cli.bots.pytorch_runtime import PyTorchRuntime

    runtime = PyTorchRuntime(device_preference=device or "auto", precision=precision)
    ranked = runtime.rerank_candidates(query=query, candidates=list(candidates), device=device, precision=precision)
    res = {
        "success": True,
        "operation": "rerank",
        "query": query,
        "device": runtime.active_device,
        "precision": precision,
        "ranked_candidates": ranked,
    }
    response = _build_response(ctx, command="vision.rerank", state="ok", data=res)

    def _text() -> None:
        console.print(f"[bold green]✓ Neural Reranking Completed[/bold green] [{runtime.active_device}/{precision}]")
        console.print(f"  [bold]Query:[/] {query}")
        table = Table(title="Reranked Candidates")
        table.add_column("Rank", justify="center")
        table.add_column("Score", justify="right")
        table.add_column("Candidate Text")
        for i, item in enumerate(ranked, start=1):
            table.add_row(str(i), f"{item['score']:.4f}", item["candidate"])
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@vision.command("doctor")
@click.pass_context
def vision_doctor(ctx: click.Context) -> None:
    """Diagnose Vision Transformer backends, PyTorch acceleration, and API credentials."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.check_capabilities()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.doctor", state=state, data=res)

    def _text() -> None:
        table = Table(title="HATH0R Vision Diagnostics")
        table.add_column("Component", style="bold")
        table.add_column("Status")
        table.add_column("Details")

        cfg_status = "ok" if res.get("config_present") else "default"
        table.add_row("Vision Config", f"[{'green' if cfg_status=='ok' else 'yellow'}]{cfg_status}[/]", str(res.get("config_path")))

        torch_diag = res.get("pytorch", {})
        if torch_diag.get("available"):
            t_status = f"[green]active ({torch_diag.get('device')})[/green]"
            t_details = f"v{torch_diag.get('version')} · {torch_diag.get('device_name')}"
            if torch_diag.get("memory_allocated_mb", 0) > 0:
                t_details += f" ({torch_diag.get('memory_allocated_mb')}MB VRAM)"
        else:
            t_status = "[dim]not installed[/dim]"
            t_details = "Optional native acceleration runtime"
        table.add_row("PyTorch Substrate", t_status, t_details)

        ollama = res.get("local_ollama", {})
        o_status = "online" if ollama.get("online") else "offline"
        table.add_row("Local Ollama ViT", f"[{'green' if o_status=='online' else 'dim'}]{o_status}[/]", f"{ollama.get('host')} (models: {len(ollama.get('available_models', []))})")

        creds = res.get("remote_credentials_configured", {})
        cred_str = ", ".join([f"{k}:{'✓' if v else '✗'}" for k, v in creds.items()])
        table.add_row("Remote Providers", "configured", cred_str)
        table.add_row("Embedding Model", "ready", str(res.get("embedding_model")))

        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
