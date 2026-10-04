"""
HATH0R CLI Observability & Arize Phoenix Command Group.

Provides operator commands to inspect distributed agent tracing, evaluate
LLM-as-a-judge scores, and check Phoenix health status.
"""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
import click
from rich.console import Console
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
    cfg = load_otel_config()
    target_endpoint = endpoint or cfg.otlp_endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:6006")

    # If port 4318, check root or /v1/traces, or standard Phoenix UI on 6006
    health_url = target_endpoint.replace(":4318", ":6006").rstrip("/")
    if not health_url.startswith("http"):
        health_url = f"http://{health_url}"

    status_data: Dict[str, Any] = {
        "service": cfg.service_name,
        "environment": cfg.deployment_environment,
        "otel_enabled": cfg.enabled,
        "otlp_endpoint": cfg.otlp_endpoint or "http://1NPHOENIX:4318",
        "target_url": health_url,
        "phoenix_reachable": False,
        "http_code": None,
    }

    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "hath0r-cli/observe"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            status_data["http_code"] = resp.status
            status_data["phoenix_reachable"] = (resp.status == 200)
    except Exception as exc:
        status_data["error"] = str(exc)

    if as_json:
        click.echo(json.dumps(status_data, indent=2))
        return

    console.print(f"[bold cyan]HATH0R Observability Status for [{cfg.service_name}]:[/bold cyan]")
    console.print(f"  • Environment: {cfg.deployment_environment}")
    console.print(f"  • OTLP Target: {status_data['otlp_endpoint']}")
    console.print(f"  • Phoenix UI URL: {health_url}")

    if status_data["phoenix_reachable"]:
        console.print("  [bold green]✓ Arize Phoenix is reachable and active.[/bold green]")
    else:
        console.print(f"  [yellow]! Arize Phoenix at {health_url} is unreachable (Error: {status_data.get('error', 'Unknown')})[/yellow]")


@observe_cmd.command("evals", help="Inspect automated LLM-as-a-judge evaluation benchmarks.")
@click.option("--dataset", default="golden-legislative", help="Dataset name to inspect.")
@click.option("--json", "as_json", is_flag=True, help="Output evaluation schema in JSON.")
def observe_evals(dataset: str, as_json: bool) -> None:
    """Inspect registered evaluation criteria for bot pipelines."""
    eval_info = {
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
            console.print(f"  • [green]{ev['name']}[/green] [{ev['kind']}] - Threshold: {ev['threshold']} -> {ev['target']}")
