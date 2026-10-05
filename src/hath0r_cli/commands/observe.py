"""
HATH0R CLI Observability & Arize Phoenix Command Group.

Provides operator commands to inspect distributed agent tracing, evaluate
LLM-as-a-judge scores, and check Phoenix health status.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import click
from rich.console import Console

from ..bots.phoenix_observer_bot import phoenix_observer_bot
from ..telemetry import load_otel_config

console = Console()


@click.group("observe", help="Inspect agent observability, Phoenix traces, and LLM evaluations.")
def observe_cmd() -> None:
    """Agent observability and Phoenix telemetry command suite."""
    pass


@observe_cmd.command("status", help="Check Phoenix collector endpoint and OTel telemetry status.")
@click.option("--endpoint", default=None, help="Custom Phoenix OTLP/HTTP endpoint to test.")
@click.option("--json", "as_json", is_flag=True, help="Output status in JSON format.")
def observe_status(endpoint: Optional[str], as_json: bool) -> None:
    """Check connectivity to Arize Phoenix and local OpenTelemetry configuration."""
    bot = phoenix_observer_bot
    if endpoint:
        bot.custom_endpoint = endpoint

    res = bot.check_health()
    cfg = load_otel_config()

    status_data: Dict[str, Any] = {
        "service": cfg.service_name,
        "environment": cfg.deployment_environment,
        "otel_enabled": cfg.enabled,
        "otlp_endpoint": cfg.otlp_endpoint or "http://1NPHOENIX:4318",
        "target_url": res["target_url"],
        "phoenix_reachable": res["healthy"],
        "http_code": res["http_status"],
        "error": res["error"],
    }

    if as_json:
        click.echo(json.dumps(status_data, indent=2))
        return

    console.print(f"[bold cyan]HATH0R Observability Status for [{cfg.service_name}]:[/bold cyan]")
    console.print(f"  • Environment: {cfg.deployment_environment}")
    console.print(f"  • OTLP Target: {status_data['otlp_endpoint']}")
    console.print(f"  • Phoenix UI URL: {res['target_url']}")

    if status_data["phoenix_reachable"]:
        console.print("  [bold green]✓ Arize Phoenix is reachable and active (HTTP 200).[/bold green]")
    else:
        console.print(
            f"  [yellow]! Arize Phoenix at {res['target_url']} is unreachable (Error: {status_data.get('error', 'Unknown')})[/yellow]"
        )


@observe_cmd.command("evals", help="Inspect automated LLM-as-a-judge evaluation benchmarks.")
@click.option("--dataset", default="golden-legislative", help="Dataset name to inspect.")
@click.option("--json", "as_json", is_flag=True, help="Output evaluation schema in JSON.")
def observe_evals(dataset: str, as_json: bool) -> None:
    """Inspect registered evaluation criteria for bot pipelines."""
    eval_info: dict[str, Any] = {
        "dataset": dataset,
        "evaluators": [
            {
                "name": "StatutoryFaithfulness",
                "kind": "LLM-as-a-judge",
                "threshold": 0.45,
                "target": "Bill Summarization Factory",
            },
            {
                "name": "NeutralityTone",
                "kind": "Rule & LLM Judge",
                "threshold": 0.70,
                "target": "Plain-Language Bill Summarizer Bot",
            },
            {
                "name": "CitizenReadability",
                "kind": "Flesch-Kincaid & Sentence Structure",
                "threshold": 0.80,
                "target": "Legislative Summary Ingestion",
            },
        ],
    }

    if as_json:
        click.echo(json.dumps(eval_info, indent=2))
    else:
        console.print(f"[bold cyan]HATH0R Registered Evaluations ({dataset}):[/bold cyan]")
        for ev in eval_info["evaluators"]:
            console.print(
                f"  • [green]{ev['name']}[/green] [{ev['kind']}] - Threshold: {ev['threshold']} -> {ev['target']}"
            )


@observe_cmd.command("charts", help="Display agent performance observation charts and statistical distributions.")
@click.option(
    "--metric",
    default="latency_ms",
    type=click.Choice(["latency_ms", "prompt_tokens", "total_tokens", "cost_usd"]),
    help="Target metric for distribution histogram.",
)
@click.option(
    "--format",
    "fmt",
    default="ascii",
    type=click.Choice(["ascii", "json", "html"]),
    help="Output visualization format.",
)
def observe_charts(metric: str, fmt: str) -> None:
    """Display observation charts and statistical metrics for agent performance."""
    try:
        from hath0r_engine.telemetry.observation_charts import observation_charts_engine

        metrics = observation_charts_engine.compute_performance_metrics(metric=metric)
        if fmt == "json":
            click.echo(json.dumps(metrics, indent=2))
        elif fmt == "html":
            html_doc = observation_charts_engine.render_generative_ui_dashboard(metrics)
            click.echo(html_doc)
        else:
            ascii_doc = observation_charts_engine.render_ascii_charts(metrics)
            click.echo(ascii_doc)
    except Exception as err:
        console.print(f"[yellow]! Engine telemetry chart error ({err}). Rendering CLI status summary.[/yellow]")
