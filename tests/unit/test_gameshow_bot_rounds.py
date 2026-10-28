"""Tournament rounds, calibration and reporting for HathorGameshowBot."""

from __future__ import annotations

import asyncio

from hath0r_engine.training.gameshow_models import EvaluationCard

from hath0r_cli.bots.gameshow_bot import HathorGameshowBot


def _card(cid: str, domain: str, question: str, answer: str, facts: list[str]) -> EvaluationCard:
    return EvaluationCard(
        card_id=cid, epoch=1, domain=domain, question=question, expected_answer=answer, key_facts=facts
    )


def _bot(tmp_path) -> HathorGameshowBot:
    return HathorGameshowBot(
        deck_path=str(tmp_path / "deck.json"),
        cache_path=str(tmp_path / "cache.json"),
        output_dir=str(tmp_path),
    )


def test_rounds_calibrate_and_converge(tmp_path):
    bot = _bot(tmp_path)
    assert "no tournament rounds" in bot.generate_report(str(tmp_path / "empty.md"))
    bot.save_deck_state()  # no deck yet: a no-op
    assert bot.calibrate_missed_cards(["x"]) == 0

    deck = bot.initialize_deck()
    cards = [
        _card(
            "A", "system", "What does POSIX stand for?", "Portable Operating System Interface", ["Portable", "POSIX"]
        ),
        _card("B", "math", "What is two plus two?", "Four", ["four"]),
        _card("C", "math", "Capital of France?", "Paris", ["Paris"]),
    ]
    deck.cards = {c.card_id: c for c in cards}
    deck.total_cards = len(cards)

    async def async_agent(question):
        return {"response": "POSIX is the Portable Operating System Interface", "model": "m", "tools": ["kb"]}

    def agent(question):
        if "two" in question:
            return "I do not know"
        if "France" in question:
            raise RuntimeError("agent offline")
        return asyncio.sleep(0, result={"response": "POSIX: Portable Operating System Interface"})

    r1 = asyncio.run(bot.run_round(1, agent, cards, concurrency=2))
    assert r1.cards_evaluated == 3 and r1.incorrect_cards >= 2
    assert set(r1.domain_breakdown) == {"system", "math"}
    assert bot.calibrate_missed_cards(r1.incorrect_card_ids) >= 0

    r2 = asyncio.run(bot.run_round(2, async_agent, cards))
    assert r2.round_num == 2 and deck.current_round == 2
    assert bot.evaluate_response(cards[0], "Portable Operating System Interface (POSIX)")[0] in (True, False)

    report_path = tmp_path / "out" / "report.md"
    report = bot.generate_report(str(report_path))
    assert "| Round 1 |" in report and report_path.read_text(encoding="utf-8") == report

    bot.save_deck_state()
    reloaded = _bot(tmp_path).initialize_deck()
    assert set(reloaded.cards) == {"A", "B", "C"} and len(reloaded.rounds) == 2


def test_empty_round(tmp_path):
    bot = _bot(tmp_path)
    stats = asyncio.run(bot.run_round(1, lambda q: "x", []))
    assert stats.cards_evaluated == 0 and stats.accuracy_pct == 0.0
