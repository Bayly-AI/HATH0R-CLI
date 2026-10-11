"""Unit tests for Hath0r CLI Observe Command Group."""

import json

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_observe_help():
    runner = CliRunner()
    result = runner.invoke(main, ["observe", "--help"])
    assert result.exit_code == 0
    assert "status" in result.output
    assert "evals" in result.output


def test_observe_evals_json():
    runner = CliRunner()
    result = runner.invoke(main, ["observe", "evals", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "dataset" in data
    assert len(data["evaluators"]) >= 3


def test_observe_status_json():
    runner = CliRunner()
    result = runner.invoke(main, ["observe", "status", "--json", "--endpoint", "http://127.0.0.1:6006"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "otel_enabled" in data
    assert "target_url" in data


def test_observe_charts():
    runner = CliRunner()
    result = runner.invoke(main, ["observe", "charts"])
    assert result.exit_code == 0
    assert (
        "OBSERVATION CHARTS" in result.output
        or "FinOps Histogram" in result.output
        or "Rendering CLI" in result.output
        or "telemetry chart error" in result.output
    )


def test_observe_anomalies_json():
    runner = CliRunner()
    result = runner.invoke(main, ["observe", "anomalies", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_spans_analyzed"] >= 10
    assert data["anomalies_detected"] >= 1
    assert "baseline_threshold" in data
    assert any(rec["root_cause"] in ("PROMPT_TAX_EXPLOSION", "FINOPS_BUDGET_SPIKE", "LATENCY_STALL") for rec in data["anomalous_records"])

