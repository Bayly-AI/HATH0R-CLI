"""Vision Transformers (ViT) & Multimodal Pipeline commands for Hath0r CLI."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("vision")
def vision() -> None:
    """Vision Transformers (ViT) & Multimodal Pipeline tools."""


@vision.command("inspect")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.option("--prompt", default=None, help="Custom inspection prompt or question.")
@click.pass_context
def vision_inspect(ctx: click.Context, image_path: Path, prompt: str | None) -> None:
    """Inspect an image or screenshot using Vision Transformers."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.inspect_image(image_path=image_path, prompt=prompt)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.inspect", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Vision Inspection Completed[/bold green] ({res.get('provider')}/{res.get('model')})")
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
@click.pass_context
def vision_parse_doc(ctx: click.Context, image_path: Path, prompt: str | None) -> None:
    """Parse visual documents, architecture diagrams, charts, and structured layouts."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.parse_document(image_path=image_path, prompt=prompt)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.parse_doc", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Document Layout Parsed[/bold green] ({res.get('provider')})")
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
@click.pass_context
def vision_ground(ctx: click.Context, image_path: Path, target: str) -> None:
    """Ground a UI element description to coordinate bounding boxes."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.ground_element(image_path=image_path, target=target)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.ground", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            grounded = res.get("grounded_target", {})
            coords = grounded.get("center_coordinates", {})
            bbox = grounded.get("bounding_box", [])
            console.print(f"[bold green]✓ Element Grounded:[/] '{target}'")
            console.print(f"  [bold]Center Coordinates:[/] ({coords.get('x')}, {coords.get('y')}) px")
            console.print(f"  [dim]Normalized Bounding Box:[/] {bbox}")
        else:
            console.print(f"[bold red]✗ Grounding Failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@vision.command("embed")
@click.argument("image_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def vision_embed(ctx: click.Context, image_path: Path) -> None:
    """Extract multimodal cross-modal vector embedding for an image."""
    from hath0r_cli.bots.vision_bot import VisionBot

    bot = VisionBot(cwd=Path.cwd())
    res = bot.embed_visual(image_path=image_path)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="vision.embed", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            emb = res.get("embedding", [])
            console.print(f"[bold green]✓ Multimodal Embedding Generated[/bold green] ({len(emb)} dimensions, model: {res.get('model')})")
            console.print(f"  [dim]Vector snippet:[/] [{', '.join(str(x) for x in emb[:5])}, ...]")
        else:
            console.print(f"[bold red]✗ Embedding Failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@vision.command("doctor")
@click.pass_context
def vision_doctor(ctx: click.Context) -> None:
    """Diagnose Vision Transformer backends, Ollama connectivity, and API credentials."""
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
