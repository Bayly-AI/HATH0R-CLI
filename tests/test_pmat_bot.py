"""Unit tests for PmatBot."""

from pathlib import Path
from hath0r_cli.bots.pmat_bot import PmatBot, pmat_bot


def test_pmat_bot_doctor():
    bot = PmatBot()
    doc = bot.doctor()
    assert doc["status"] == "OK"
    assert doc["bot_name"] == "PmatBot"
    assert "supported_intents" in doc


def test_pmat_bot_get_stats():
    bot = PmatBot()
    stats = bot.get_stats(window_days=30)
    assert stats["schema_version"] == "hath0r.pmat.stats/1"
    assert "summary" in stats
    assert "provability" in stats
    assert "complexity" in stats


def test_pmat_bot_analyze_churn():
    bot = PmatBot()
    report = bot.analyze_churn()
    assert "churn" in report
    assert "hotspots" in report


def test_pmat_bot_check_provability():
    bot = PmatBot()
    prov = bot.check_provability()
    assert "provability" in prov
    assert "provability_rankings" in prov


def test_pmat_bot_calculate_complexity():
    bot = PmatBot()
    comp = bot.calculate_complexity()
    assert "complexity" in comp
    assert "complexity_rankings" in comp


def test_pmat_bot_conversational_intents():
    bot = PmatBot()
    r1 = bot.handle_conversational_intent("analyze code churn")
    assert "churn" in r1

    r2 = bot.handle_conversational_intent("check provability score")
    assert "provability" in r2

    r3 = bot.handle_conversational_intent("calculate complexity score")
    assert "complexity" in r3
