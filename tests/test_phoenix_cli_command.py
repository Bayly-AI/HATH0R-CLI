"""Tests for hath0r phoenix command suite."""

import json

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_phoenix_help():
    runner = CliRunner()
    res = runner.invoke(main, ["phoenix", "--help"])
    assert res.exit_code == 0
    assert "status" in res.output
    assert "evals" in res.output
    assert "up" in res.output
    assert "down" in res.output


def test_phoenix_status_json():
    runner = CliRunner()
    res = runner.invoke(main, ["phoenix", "status", "--json", "--endpoint", "http://127.0.0.1:6006"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "target_url" in data
    assert "healthy" in data


def test_phoenix_evals_json():
    runner = CliRunner()
    res = runner.invoke(main, ["phoenix", "evals", "--json"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "evaluators" in data
    assert len(data["evaluators"]) >= 4


def test_phoenix_projects_json():
    runner = CliRunner()
    res = runner.invoke(main, ["phoenix", "projects", "--json", "--group", "1-nation"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert isinstance(data, list)


def test_phoenix_costs_json():
    runner = CliRunner()
    res = runner.invoke(main, ["phoenix", "costs", "--json", "--group", "1-nation"])
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert "total_spans" in data
    assert "total_cost_usd" in data

