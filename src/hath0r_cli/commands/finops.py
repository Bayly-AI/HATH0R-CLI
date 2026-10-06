"""FinOps & Tokenizer Tax commands for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

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
@click.option(
    "--precision",
    type=click.Choice(["fp16", "fp32"], case_sensitive=False),
    default="fp16",
    help="Precision format (default fp16).",
)
@click.option(
    "--cost-per-million", type=float, default=5.0, help="API inference cost per 1M tokens in USD (default $5.00)."
)
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
            table.add_row(
                s["script"], str(s["character_count"]), f"{s['percentage']}%", f"{s['expansion_factor']:.2f}x"
            )

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
        console.print(
            f"  • Idle VRAM Overhead:                 [bold red]{vram['vocab_vram_gb']} GB[/bold red] ({vram['precision']})"
        )

        # Continuous Patch Budget
        vit = res["vit_patch_budget"]
        console.print("\n[bold]Continuous Visual Patch Budget (Pixel-Native ViT):[/bold]")
        console.print(f"  • Patch Resolution:  {vit['patch_size']} ({vit['rendered_page_size']})")
        console.print(
            f"  • Page Patch Budget: [cyan]{vit['total_continuous_patches']} visual patches[/cyan] (Language-Neutral)"
        )

        # FinOps Economics
        fo = res["finops_impact"]
        console.print(f"\n[bold]Economic Impact (@ ${cost_per_million:.2f}/1M tokens):[/bold]")
        console.print(f"  • Subword Token Cost:        ${fo['actual_cost_usd']:.4f}")
        console.print(f"  • Pixel-Native Normalized:   ${fo['baseline_cost_usd']:.4f}")
        console.print(f"  • Potential Cost Reduction:  [bold green]{fo['potential_cost_savings_pct']}%[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@finops.group("tokens")
def finops_tokens() -> None:
    """Agent prompt token telemetry, FinOps cost ledger, and distribution histograms."""


@finops_tokens.command("record")
@click.option("--prompt", "-p", required=True, help="Prompt text sent to agent.")
@click.option("--user", "-u", default="default_user", help="User or caller identifier.")
@click.option("--model", "-m", default="claude-3-5-sonnet", help="Model identifier.")
@click.option(
    "--tier",
    "-t",
    type=click.Choice(["light", "standard", "reasoning"], case_sensitive=False),
    default="standard",
    help="Complexity tier.",
)
@click.option("--completion", "-c", default="", help="Completion response text.")
@click.option("--session", "-s", default="", help="Session identifier.")
@click.pass_context
def finops_tokens_record(
    ctx: click.Context,
    prompt: str,
    user: str,
    model: str,
    tier: str,
    completion: str,
    session: str,
) -> None:
    """Record agent prompt token telemetry into the FinOps ledger."""
    from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot

    bot = TokenTelemetryCLIBot(cwd=Path.cwd())
    rec = bot.record(
        prompt=prompt,
        user_id=user,
        model=model,
        tier=tier,
        completion=completion,
        session_id=session,
    )

    response = _build_response(ctx, command="finops.tokens.record", state="ok", data=rec)

    def _text() -> None:
        console.print(f"[bold green]✓ Token Telemetry Recorded:[/] [cyan]{rec['id']}[/cyan]")
        console.print(f"  • User:               [yellow]{rec['user_id']}[/yellow]")
        console.print(f"  • Prompt Length:      {rec['prompt_length_chars']:,} chars")
        console.print(f"  • Prompt Tokens:      [magenta]{rec['prompt_tokens']:,}[/magenta]")
        console.print(f"  • Total Tokens:       [magenta]{rec['total_tokens']:,}[/magenta]")
        console.print(f"  • Model & Tier:       {rec['model']} ({rec['tier']})")
        console.print(f"  • Calculated Cost:    [bold green]${rec['cost_usd']:.6f}[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@finops_tokens.command("list")
@click.option("--user", "-u", default=None, help="Filter by user identifier.")
@click.option("--model", "-m", default=None, help="Filter by model.")
@click.option("--agent", "-a", default=None, help="Filter by agent identifier.")
@click.option("--session", "-s", default=None, help="Filter by session ID.")
@click.option("--tier", "-t", default=None, help="Filter by tier.")
@click.option("--limit", "-n", default=20, type=int, help="Maximum number of records to return.")
@click.pass_context
def finops_tokens_list(
    ctx: click.Context,
    user: Optional[str],
    model: Optional[str],
    agent: Optional[str],
    session: Optional[str],
    tier: Optional[str],
    limit: int,
) -> None:
    """List agent token telemetry records."""
    from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot

    bot = TokenTelemetryCLIBot(cwd=Path.cwd())
    records = bot.list_records(
        user_id=user,
        model=model,
        agent_id=agent,
        session_id=session,
        tier=tier,
        limit=limit,
    )

    response = _build_response(
        ctx,
        command="finops.tokens.list",
        state="ok",
        data={"count": len(records), "records": records},
    )

    def _text() -> None:
        if not records:
            console.print("[yellow]No token telemetry records found.[/yellow]")
            return

        table = Table(title=f"Token Telemetry Records (Showing {len(records)})")
        table.add_column("Timestamp", style="dim")
        table.add_column("User", style="bold yellow")
        table.add_column("Model", style="cyan")
        table.add_column("Chars", justify="right")
        table.add_column("Prompt Tok", justify="right", style="magenta")
        table.add_column("Total Tok", justify="right", style="bold magenta")
        table.add_column("Cost USD", justify="right", style="green")

        for r in records:
            ts = r.get("timestamp", "")[:19].replace("T", " ")
            table.add_row(
                ts,
                r.get("user_id", ""),
                r.get("model", ""),
                str(r.get("prompt_length_chars", 0)),
                str(r.get("prompt_tokens", 0)),
                str(r.get("total_tokens", 0)),
                f"${r.get('cost_usd', 0.0):.6f}",
            )

        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@finops_tokens.command("histogram")
@click.option(
    "--metric",
    "-m",
    type=click.Choice(["prompt_tokens", "prompt_length_chars", "total_tokens", "cost_usd", "latency_ms"]),
    default="prompt_tokens",
    help="Metric to bin.",
)
@click.option("--user", "-u", default=None, help="Filter by user identifier.")
@click.option("--model", "-M", default=None, help="Filter by model.")
@click.option("--agent", "-a", default=None, help="Filter by agent identifier.")
@click.option("--session", "-s", default=None, help="Filter by session ID.")
@click.option("--tier", "-t", default=None, help="Filter by tier.")
@click.option("--bins", "-b", default=10, type=int, help="Number of histogram bins.")
@click.pass_context
def finops_tokens_histogram(
    ctx: click.Context,
    metric: str,
    user: Optional[str],
    model: Optional[str],
    agent: Optional[str],
    session: Optional[str],
    tier: Optional[str],
    bins: int,
) -> None:
    """Build and display a statistical distribution histogram of token telemetry."""
    from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot

    bot = TokenTelemetryCLIBot(cwd=Path.cwd())
    data = bot.histogram(
        metric=metric,
        user_id=user,
        model=model,
        agent_id=agent,
        session_id=session,
        tier=tier,
        bins_count=bins,
    )

    response = _build_response(ctx, command="finops.tokens.histogram", state="ok", data=data)

    def _text() -> None:
        tot = data.get("total_records", 0)
        if tot == 0:
            console.print("[yellow]No records found to construct histogram.[/yellow]")
            return

        st = data.get("stats", {})
        console.print(f"[bold green]✓ FinOps Token Distribution Histogram[/bold green] (Metric: [cyan]{metric}[/cyan])")
        console.print(f"  • Total Interactions: [bold]{tot:,}[/bold]")
        console.print(f"  • Total Tokens:       [bold magenta]{data.get('total_tokens', 0):,}[/bold magenta]")
        console.print(f"  • Total Spend:        [bold green]${data.get('total_cost_usd', 0.0):.4f}[/bold green]")
        console.print(
            f"  • Distribution:       Mean: [cyan]{st.get('mean', 0):.2f}[/cyan] | "
            f"Median: [cyan]{st.get('median', 0):.2f}[/cyan] | "
            f"P95: [yellow]{st.get('p95', 0):.2f}[/yellow] | "
            f"P99: [red]{st.get('p99', 0):.2f}[/red]"
        )

        table = Table(title=f"Histogram Bins ({metric})")
        table.add_column("Range", style="bold")
        table.add_column("Count", justify="right")
        table.add_column("%", justify="right")
        table.add_column("Cumulative %", justify="right", style="dim")
        table.add_column("Distribution", style="cyan")

        for b in data.get("bins", []):
            rng = f"[{b['bin_start']:.1f} - {b['bin_end']:.1f}]"
            table.add_row(
                rng,
                str(b["count"]),
                f"{b['percentage']:.1f}%",
                f"{b['cumulative_percentage']:.1f}%",
                b["ascii_bar"],
            )

        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@finops_tokens.command("check")
@click.option("--user", "-u", default="raybayly", help="User profile identifier (default: raybayly).")
@click.option("--days", "-d", default=90, type=int, help="Trailing period in days (default: 90).")
@click.option(
    "--artifact-dir", type=click.Path(path_type=Path), default=None, help="Directory to save HTML dashboard artifact."
)
@click.pass_context
def finops_tokens_check(
    ctx: click.Context,
    user: str,
    days: int,
    artifact_dir: Optional[Path],
) -> None:
    """Execute complete token check workflow returning 90-day FinOps usage, histogram, and HTML artifact."""
    from hath0r_cli.bots.token_check_bot import TokenCheckWorkflowBot

    bot = TokenCheckWorkflowBot(cwd=Path.cwd())
    data = bot.run_token_check(user_id=user, days=days, artifact_dir=artifact_dir)

    response = _build_response(ctx, command="finops.tokens.check", state="ok", data=data)

    def _text() -> None:
        console.print(data.get("markdown_report", ""))

    _emit_response(ctx, response, text_renderer=_text)


@finops.group("budget")
def finops_budget() -> None:
    """Subagent token and USD tree budget circuit breaker commands."""
    pass


@finops_budget.command("check")
@click.option("--tree-id", default="default_tree", help="Subagent tree identifier.")
@click.pass_context
def finops_budget_check(ctx: click.Context, tree_id: str) -> None:
    """Inspect token and cost budget consumption for subagent execution trees."""
    from hath0r_cli.bots.token_tree_budget import token_tree_budget_guard
    res = token_tree_budget_guard.check_budget(tree_id)

    response = _build_response(ctx, command="finops.budget.check", state="ok", data=res)

    def _text() -> None:
        console.print(f"\n[bold cyan]FinOps Subagent Tree Budget Status ({tree_id})[/bold cyan]")
        console.print(f"Status: [bold green]{res['status']}[/bold green]")
        console.print(f"Tokens Used: [bold white]{res['total_tokens']}[/bold white] / {res['max_tokens_budget']} cap")
        console.print(f"USD Used: [bold white]${res['estimated_usd']:.4f}[/bold white] / ${res['max_usd_budget']:.2f} cap")
        console.print(f"Remaining Tokens: [bold green]{res['remaining_tokens']}[/bold green]")
        console.print(f"Remaining USD: [bold green]${res['remaining_usd']:.4f}[/bold green]\n")

    _emit_response(ctx, response, text_renderer=_text)
