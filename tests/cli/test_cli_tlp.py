"""CLI integration tests for hath0r tlp commands (plan, run, verify)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_tlp_plan_text():
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "text", "tlp", "plan", "--goal", "Refactor authentication flow"])
    assert res.exit_code == 0
    assert "Task Execution DAG: Refactor authentication flow" in res.output
    assert "Tier 1" in res.output


def test_cli_tlp_plan_json(tmp_path: Path):
    runner = CliRunner()
    out_file = tmp_path / "dag.json"
    res = runner.invoke(
        main,
        ["--output", "json", "tlp", "plan", "--goal", "Deploy service", "--output-file", str(out_file)],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "tlp.plan"
    assert data["state"] == "ok"
    assert "dag" in data["data"]
    assert out_file.exists()


def test_cli_tlp_run_parallel():
    runner = CliRunner()
    res = runner.invoke(
        main,
        ["--output", "json", "tlp", "run", "--goal", "Test and deploy", "--parallel", "--max-workers", "2"],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "tlp.run"
    assert data["state"] == "ok"
    assert data["data"]["success"] is True
    assert data["data"]["completed_nodes"] == data["data"]["total_nodes"]


def test_cli_tlp_verify_valid():
    runner = CliRunner()
    res = runner.invoke(
        main,
        [
            "--output",
            "json",
            "tlp",
            "verify",
            "--trajectory",
            "local,development,testing,staging,master",
            "--policy",
            "cr-bai-001",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "tlp.verify"
    assert data["state"] == "ok"
    assert data["data"]["valid"] is True


def test_cli_tlp_verify_invalid():
    runner = CliRunner()
    res = runner.invoke(
        main,
        [
            "--output",
            "json",
            "tlp",
            "verify",
            "--trajectory",
            "local,staging",
            "--policy",
            "cr-bai-001",
        ],
    )
    assert res.exit_code == 0
    data = json.loads(res.output)
    assert data["command"] == "tlp.verify"
    assert data["state"] == "degraded"
    assert data["data"]["valid"] is False
