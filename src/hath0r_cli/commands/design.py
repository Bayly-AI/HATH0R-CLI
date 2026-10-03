"""Design & Paper.design MCP integration commands for Hath0r CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from hath0r_cli.bots.paper_design_bot import PaperDesignBot
from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("design")
def design() -> None:
    """Design tools and Paper.design MCP integration for website design."""


@design.command("status")
@click.option("--url", default="http://127.0.0.1:29979", help="Base URL of the Paper Desktop MCP server.")
@click.pass_context
def design_status(ctx: click.Context, url: str) -> None:
    """Check connectivity and operational readiness of Paper.design MCP."""
    bot = PaperDesignBot(base_url=url)
    report = bot.check_connection()
    data = report.to_dict()

    state = "ok" if report.connected else "warning"
    response = _build_response(ctx, command="design.status", state=state, data=data)

    def _text() -> None:
        if report.connected:
            color = "green" if report.status == "online" else "yellow"
            console.print(f"[bold {color}]✓ Paper.design MCP Status: {report.status.upper()}[/bold {color}]")
            console.print(f"  • Transport: [cyan]{report.transport}[/cyan]")
            console.print(f"  • Base URL:  {report.url}")
            if report.cli_path:
                console.print(f"  • CLI Path:  {report.cli_path}")
            console.print(f"  • Message:   {report.message}")
            if report.tools_available:
                console.print(f"  • Tools:     {', '.join(report.tools_available)}")
        else:
            console.print("[bold red]✗ Paper.design MCP is Offline[/bold red]")
            console.print(f"  • Tested URL: {report.url}")
            console.print(f"  • Message:    {report.message}")
            if report.remediation:
                console.print("\n[bold yellow]Remediation Steps:[/bold yellow]")
                for line in report.remediation.splitlines():
                    console.print(f"  {line}")

    _emit_response(ctx, response, text_renderer=_text)


@design.command("inspect")
@click.option("--mock", type=click.Path(exists=True, path_type=Path), help="Optional path to mock selection JSON file.")
@click.pass_context
def design_inspect(ctx: click.Context, mock: Optional[Path]) -> None:
    """Inspect the current active canvas selection from Paper.design."""
    bot = PaperDesignBot()
    mock_payload = None
    if mock:
        try:
            mock_payload = json.loads(mock.read_text(encoding="utf-8"))
        except Exception as exc:
            raise click.BadParameter(f"Could not parse mock JSON: {exc}")

    res = bot.get_selection(mock_payload=mock_payload)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="design.inspect", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print("[bold green]✓ Paper Canvas Selection Inspected[/bold green]")
            sel = res.get("selection", {})
            console.print(f"  • Type:   [cyan]{sel.get('type')}[/cyan]")
            console.print(f"  • Name:   [bold]{sel.get('name')}[/bold]")
            if "width" in sel and "height" in sel:
                console.print(f"  • Size:   {sel.get('width')}x{sel.get('height')}px")
            if "source" in res:
                console.print(f"  • Source: {res['source']}")
        else:
            console.print(f"[bold red]✗ Failed to inspect canvas selection:[/] {res.get('error')}")
            if res.get("remediation"):
                console.print(f"  {res.get('remediation')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@design.command("to-code")
@click.option("--input-file", "-i", type=click.Path(exists=True, path_type=Path), help="HTML or JSON mockup file to synthesize.")
@click.option("--name", "-n", default="WebHero", help="Component name (default: WebHero).")
@click.option("--framework", "-f", type=click.Choice(["react_tailwind", "html_css"]), default="react_tailwind", help="Target framework.")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Destination file to write generated code.")
@click.pass_context
def design_to_code(
    ctx: click.Context,
    input_file: Optional[Path],
    name: str,
    framework: str,
    output: Optional[Path],
) -> None:
    """Synthesize production-grade React + Tailwind code from Paper design canvas or mockup."""
    raw_design: str | dict = ""
    if input_file:
        content = input_file.read_text(encoding="utf-8")
        try:
            raw_design = json.loads(content)
        except json.JSONDecodeError:
            raw_design = content
    else:
        # Default placeholder hero layout
        raw_design = f"<h1>{name}</h1><p>Modern web layout synthesized from Paper.design</p>"

    bot = PaperDesignBot()
    res = bot.design_to_code(raw_design=raw_design, component_name=name, framework=framework)

    if output and res.get("success"):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(res["code"], encoding="utf-8")
        res["written_to"] = str(output)

    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="design.to-code", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Synthesized Component:[/] [cyan]{res['component_name']}[/cyan] ({res['framework']})")
            if "written_to" in res:
                console.print(f"  • Saved to: [bold]{res['written_to']}[/bold]")
            else:
                console.print("\n[dim]Preview Code:[/dim]")
                console.print(res["code"])
        else:
            console.print(f"[bold red]✗ Code synthesis failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@design.command("to-canvas")
@click.option("--input-file", "-i", required=True, type=click.Path(exists=True, path_type=Path), help="HTML or React component file to stage for Paper.")
@click.option("--name", "-n", default="Web Design Canvas", help="Artboard name in Paper.")
@click.option("--width", "-w", type=int, default=1440, help="Canvas width in pixels.")
@click.option("--height", "-h", type=int, default=900, help="Canvas height in pixels.")
@click.pass_context
def design_to_canvas(
    ctx: click.Context,
    input_file: Path,
    name: str,
    width: int,
    height: int,
) -> None:
    """Format and stage web layout into Paper canvas artboard."""
    code = input_file.read_text(encoding="utf-8")
    bot = PaperDesignBot()
    res = bot.code_to_design(html_or_jsx=code, artboard_name=name, width=width, height=height)

    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="design.to-canvas", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print("[bold green]✓ Staged Canvas Payload for Paper.design[/bold green]")
            console.print(f"  • Artboard: [cyan]{name}[/cyan] ({width}x{height}px)")
            console.print(f"  • Tool:     [magenta]{res['payload']['tool']}[/magenta]")
            console.print(f"  • Connected: {'yes' if res['connected'] else 'no (staged for dispatch)'}")
        else:
            console.print(f"[bold red]✗ Staging failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@design.command("tokens")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def design_tokens(ctx: click.Context, input_file: Path) -> None:
    """Extract design tokens (colors, typography, radii) from CSS/HTML/SVG."""
    content = input_file.read_text(encoding="utf-8")
    bot = PaperDesignBot()
    res = bot.extract_tokens(raw_design_or_css=content)

    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="design.tokens", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            console.print(f"[bold green]✓ Extracted {res['count']} Design Tokens[/bold green]")
            table = Table(title="Extracted Palette & Tokens")
            table.add_column("Token", style="cyan")
            table.add_column("Value", style="magenta")
            for k, v in res["tokens"]["colors"].items():
                table.add_row(f"--color-{k}", str(v))
            console.print(table)
            console.print("\n[dim]CSS Variables:[/dim]\n" + res["css_variables"])
        else:
            console.print(f"[bold red]✗ Token extraction failed:[/] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@design.command("audit")
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def design_audit(ctx: click.Context, input_file: Path) -> None:
    """Audit layout for accessibility landmarks, image alt attributes, and web standards."""
    content = input_file.read_text(encoding="utf-8")
    bot = PaperDesignBot()
    res = bot.audit_layout(html_or_code=content)

    state = "ok" if res.get("status") == "pass" else "warning"
    response = _build_response(ctx, command="design.audit", state=state, data=res)

    def _text() -> None:
        score = res.get("accessibility_score", 0)
        color = "green" if score >= 80 else ("yellow" if score >= 50 else "red")
        status_label = str(res.get("status") or "").upper()
        console.print(f"[bold {color}]Web Layout Audit Score: {score}/100 ({status_label})[/bold {color}]")
        console.print(f"  • Landmarks Detected: {', '.join(res.get('landmarks_detected', [])) or 'None'}")
        findings = res.get("findings", [])
        if findings:
            console.print("\n[bold yellow]Findings & Recommendations:[/bold yellow]")
            for f in findings:
                sev_color = "red" if f["severity"] == "error" else "yellow"
                console.print(f"  [{sev_color}]• [{f['severity'].upper()}][/] {f['message']}")
        else:
            console.print("  [green]✓ No accessibility or semantic violations detected.[/green]")

    _emit_response(ctx, response, text_renderer=_text)
