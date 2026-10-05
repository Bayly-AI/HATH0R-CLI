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

