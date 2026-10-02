"""FinOps & Tokenizer Tax commands for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click
from rich.table import Table

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    console,
)


@click.group("finops")
def finops() -> None:
    """FinOps, cost observability, tokenizer tax audit, and resource optimization."""


@finops.command("tokenizer-tax")
@click.argument("target", type=str)
@click.option("--vocab-size", type=int, default=256_000, help="Model vocabulary size (default 256,000).")
@click.option("--hidden-dim", type=int, default=4096, help="Model hidden dimension d_model (default 4096).")
@click.option("--precision", type=click.Choice(["fp16", "fp32"], case_sensitive=False), default="fp16", help="Precision format (default fp16).")
@click.option("--cost-per-million", type=float, default=5.0, help="API inference cost per 1M tokens in USD (default $5.00).")
@click.option("--patch-size", type=int, default=16, help="Continuous visual patch size P (default 16).")
@click.pass_context
def finops_tokenizer_tax(
    ctx: click.Context,
    target: str,
    vocab_size: int,
    hidden_dim: int,
    precision: str,
    cost_per_million: float,
    patch_size: int,
) -> None:
    """Audit subword tokenizer tax, token expansion inflation, VRAM overhead, and ViT patch budgets."""
    from hath0r_cli.bots.tokenizer_tax_bot import TokenizerTaxBot

    precision_bytes = 2 if precision.lower() == "fp16" else 4
    bot = TokenizerTaxBot(cwd=Path.cwd())
    res = bot.audit(
        text_or_path=target,
        vocab_size=vocab_size,
        hidden_dim=hidden_dim,
        precision_bytes=precision_bytes,
        cost_per_million_tokens=cost_per_million,
        patch_size=patch_size,
    )

    if not res.get("success"):
        console.print(f"[bold red]✗ Audit Failed:[/] {res.get('error')}")
        ctx.exit(1)

    response = _build_response(ctx, command="finops.tokenizer_tax", state="ok", data=res)

    def _text() -> None:
        console.print(f"[bold green]✓ FinOps Tokenizer Tax Audit Completed[/bold green] (Source: {res['source']})")

        # Script Breakdown Table
        table = Table(title="Unicode Script Distribution & Expansion Factor")
        table.add_column("Script Family", style="bold")
        table.add_column("Characters", justify="right")
        table.add_column("Percentage", justify="right")
        table.add_column("Token Inflation Factor", justify="right", style="cyan")

        for s in res["script_breakdown"]:
            table.add_row(s["script"], str(s["character_count"]), f"{s['percentage']}%", f"{s['expansion_factor']:.2f}x")

        console.print(table)

        # Token Metrics
        tm = res["token_metrics"]
        console.print(f"\n[bold]Overall Token Inflation:[/] [bold magenta]{tm['inflation_ratio']}x[/bold magenta]")
        console.print(f"  • Baseline English/Latin Tokens: {tm['baseline_tokens_latin_equiv']:,}")
        console.print(f"  • Subword Tokenizer Tokens:      {tm['actual_subword_tokens']:,}")
        console.print(f"  • Incurred Token Tax Penalty:    [red]+{tm['tax_penalty_tokens']:,} tokens[/red]")

        # Vocab VRAM Overhead
        vram = res["vocab_vram_overhead"]
        console.print("\n[bold]Vocabulary Memory Overhead (Serving VRAM):[/bold]")
        console.print(f"  • Embedding & Output Head Parameters: [yellow]{vram['vocab_parameters']:,}[/yellow]")
        console.print(f"  • Idle VRAM Overhead:                 [bold red]{vram['vocab_vram_gb']} GB[/bold red] ({vram['precision']})")

        # Continuous Patch Budget
        vit = res["vit_patch_budget"]
        console.print("\n[bold]Continuous Visual Patch Budget (Pixel-Native ViT):[/bold]")
        console.print(f"  • Patch Resolution:  {vit['patch_size']} ({vit['rendered_page_size']})")
        console.print(f"  • Page Patch Budget: [cyan]{vit['total_continuous_patches']} visual patches[/cyan] (Language-Neutral)")

        # FinOps Economics
        fo = res["finops_impact"]
        console.print(f"\n[bold]Economic Impact (@ ${cost_per_million:.2f}/1M tokens):[/bold]")
        console.print(f"  • Subword Token Cost:        ${fo['actual_cost_usd']:.4f}")
        console.print(f"  • Pixel-Native Normalized:   ${fo['baseline_cost_usd']:.4f}")
        console.print(f"  • Potential Cost Reduction:  [bold green]{fo['potential_cost_savings_pct']}%[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)
