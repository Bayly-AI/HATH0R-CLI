"""CLI integration tests for hath0r elt command group."""

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_cli_elt_help():
    """Verify hath0r elt --help returns zero exit code."""
    runner = CliRunner()
    result = runner.invoke(main, ["elt", "--help"])
    assert result.exit_code == 0
    assert "Embedded ELT" in result.output
    assert "extract" in result.output
    assert "transform" in result.output
    assert "status" in result.output


def test_cli_elt_status_text_and_json():
    """Verify hath0r elt status in both text and JSON modes."""
    runner = CliRunner()

    # Text mode
    res_text = runner.invoke(main, ["--output", "text", "elt", "status"])
    assert res_text.exit_code == 0
    assert "Embedded ELT Staging Store" in res_text.output

    # JSON mode
    res_json = runner.invoke(main, ["--output", "json", "elt", "status"])
    assert res_json.exit_code == 0
    data = json.loads(res_json.output)
    assert data["state"] == "ok"
    assert "store_stats" in data["data"]


def test_cli_elt_load_and_transform(tmp_path: Path):
    """Verify hath0r elt load and transform CLI commands."""
    runner = CliRunner()

    # Load raw content in text mode
    res_load = runner.invoke(main, [
        "--output", "text",
        "elt", "load",
        "--source", "test://raw-note",
        "--type", "raw",
        "--raw", "Hello ELT world",
    ])
    assert res_load.exit_code == 0
    assert "Loaded Raw Record" in res_load.output

    # Transform projections in text mode
    res_trans = runner.invoke(main, [
        "--output", "text",
        "elt", "transform",
        "--projection", "fts5",
    ])
    assert res_trans.exit_code == 0
    assert "fts5" in res_trans.output

    # Transform in json mode
    res_trans_json = runner.invoke(main, [
        "--output", "json",
        "elt", "transform",
        "--projection", "all",
    ])
    assert res_trans_json.exit_code == 0
    trans_data = json.loads(res_trans_json.output)
    assert trans_data["state"] == "ok"
    assert "fts5" in trans_data["data"]


def test_cli_elt_prune():
    """Verify hath0r elt prune CLI command."""
    runner = CliRunner()
    res = runner.invoke(main, ["--output", "text", "elt", "prune", "--retention", "365"])
    assert res.exit_code == 0
    assert "Pruning Complete" in res.output
