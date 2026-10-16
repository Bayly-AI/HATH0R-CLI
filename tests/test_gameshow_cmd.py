"""Tests for HATH0R Gameshow CLI commands and bot."""

import os
import tempfile

from click.testing import CliRunner
from hath0r_engine.training.gameshow_models import EvaluationCard, TournamentDeckState

from hath0r_cli.cli import main


def test_gameshow_cli_status():
    """Verify hath0r gameshow status command."""
    runner = CliRunner()
    result = runner.invoke(main, ["gameshow", "status"])
    assert result.exit_code == 0
    assert "Active Calibrated Memories" in result.output or "calibrated_memories_count" in result.output


def test_gameshow_cli_calibrate_and_report():
    """Verify hath0r gameshow calibrate and report workflow with a sample deck."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        deck_path = os.path.join(tmp_dir, "test_deck.json")
        cache_path = os.path.join(tmp_dir, "test_cache.json")
        report_path = os.path.join(tmp_dir, "test_report.md")

        card = EvaluationCard(
            card_id="TEST-001",
            epoch=1,
            domain="system",
            question="What is the POSIX standard for portable operating systems?",
            expected_answer="POSIX stands for Portable Operating System Interface.",
            key_facts=["POSIX", "Portable Operating System"],
        )
        deck = TournamentDeckState(
            epoch=1,
            total_cards=1,
            cards={"TEST-001": card},
        )
        with open(deck_path, "w", encoding="utf-8") as f:
            f.write(deck.model_dump_json(indent=2))

        # Calibrate
        cal_res = runner.invoke(main, [
            "gameshow", "calibrate",
            "--deck", deck_path,
            "--output", cache_path,
        ])
        assert cal_res.exit_code == 0
        assert os.path.exists(cache_path)

        # Status with specific cache
        status_res = runner.invoke(main, [
            "gameshow", "status",
            "--cache", cache_path,
            "--deck", deck_path,
        ])
        assert status_res.exit_code == 0
        assert "calibrated_memories_count" in status_res.output or "Active Calibrated Memories" in status_res.output

        # Report
        rep_res = runner.invoke(main, [
            "gameshow", "report",
            "--deck", deck_path,
            "--output", report_path,
        ])
        assert rep_res.exit_code == 0
        assert os.path.exists(report_path)


def test_evals_gameshow_subcommand_alias():
    """Verify hath0r evals gameshow status works as an alias."""
    runner = CliRunner()
    result = runner.invoke(main, ["evals", "gameshow", "status"])
    assert result.exit_code == 0
    assert "calibrated_memories_count" in result.output or "Active Calibrated Memories" in result.output
