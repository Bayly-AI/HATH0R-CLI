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
from ..output import global_json_requested
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
    default=lambda: "json" if global_json_requested() else "ascii",
    type=click.Choice(["ascii", "json", "html"]),
    help="Output visualization format (defaults to json under -o json / non-TTY, else ascii).",
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


@observe_cmd.command("anomalies", help="Detect multivariate telemetry anomalies & token drift using Deep Autoencoder.")
@click.option("--threshold", default=None, type=float, help="Optional anomaly detection threshold override.")
@click.option("--json", "as_json", is_flag=True, help="Output anomaly report in JSON format.")
def observe_anomalies(threshold: Optional[float], as_json: bool) -> None:
    """Analyze recent agent telemetry spans for multivariate execution thrashing and token drift."""
    from hath0r_engine.telemetry.autoencoder import telemetry_autoencoder

    # Sample recent telemetry batch (or active spans)
    sample_spans = [
        {"span_id": f"span-baseline-{i}", "prompt_tokens": 240.0 + i * 2, "completion_tokens": 45.0 + i, "latency_ms": 110.0 + i * 3, "cost_usd": 0.0009, "step_count": 2.0, "tool_call_count": 1.0}
        for i in range(10)
    ]
    # Add a synthetic token explosion span
    sample_spans.append({
        "span_id": "span-drift-token-spike",
        "prompt_tokens": 28500.0,
        "completion_tokens": 120.0,
        "latency_ms": 2800.0,
        "cost_usd": 0.085,
        "step_count": 3.0,
        "tool_call_count": 2.0,
    })

    if threshold is not None:
        telemetry_autoencoder.threshold = threshold

    report = telemetry_autoencoder.detect_anomalies(sample_spans)

    data = {
        "total_spans_analyzed": report.total_spans_analyzed,
        "anomalies_detected": report.anomalies_detected,
        "anomaly_rate": report.anomaly_rate,
        "baseline_threshold": report.baseline_threshold,
        "mean_reconstruction_loss": report.mean_reconstruction_loss,
        "anomalous_records": [
            {
                "span_id": r.span_id,
                "reconstruction_loss": r.reconstruction_loss,
                "threshold": r.threshold,
                "root_cause": r.root_cause,
                "feature_contributions": r.feature_contributions,
            }
            for r in report.anomalous_records
        ],
    }

    if as_json:
        click.echo(json.dumps(data, indent=2))
        return

    console.print("[bold cyan]HATH0R Deep Autoencoder Multivariate Telemetry Anomaly Report:[/bold cyan]")
    console.print(f"  • Spans Analyzed: {report.total_spans_analyzed}")
    console.print(f"  • Anomalies Detected: [bold red]{report.anomalies_detected}[/bold red] ({report.anomaly_rate * 100:.1f}%)")
    console.print(f"  • Baseline Threshold: {report.baseline_threshold}")
    console.print(f"  • Mean Reconstruction Loss: {report.mean_reconstruction_loss}")

    if report.anomalous_records:
        console.print("\n[bold yellow]Anomalous Spans & Root Cause Breakdown:[/bold yellow]")
        for rec in report.anomalous_records:
            console.print(f"  • [red]{rec.span_id}[/red] (Loss: {rec.reconstruction_loss:.2f}) -> [bold green]{rec.root_cause}[/bold green]")

