"""Hath0r Gameshow Continuous Calibration (CAG/RAG) Managing Bot.

Orchestrates multi-round agent evaluation tournaments:
1. Evaluates candidate questions against target agent endpoints or tools.
2. Judges answers against verified ground truth and essential key facts.
3. Dynamically trains agent memory via CAG continuous calibration between rounds.
4. Drives iterative rounds to convergence and outputs benchmark reports.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from hath0r_engine.calibration.cag_registry import CAGCalibrationRegistry
from hath0r_engine.training.gameshow_judge import GameshowJudge
from hath0r_engine.training.gameshow_models import (
    CardAttempt,
    EvaluationCard,
    TournamentDeckState,
    TournamentRoundStats,
)

logger = logging.getLogger("hath0r_cli.bots.gameshow_bot")


class HathorGameshowBot:
    """Autonomous managing bot executing benchmark evaluation tournaments."""

    def __init__(
        self,
        deck_path: Optional[str] = None,
        cache_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        similarity_threshold: float = 0.85,
    ) -> None:
        self.output_dir = output_dir or os.path.join(os.getcwd(), ".hath0r", "gameshow")
        self.deck_file = deck_path or os.path.join(self.output_dir, "tournament_deck.json")
        self.cache_file = cache_path or os.path.join(self.output_dir, "cag_calibration_cache.json")
        self.judge = GameshowJudge()
        self.calibration = CAGCalibrationRegistry(
            persistence_path=self.cache_file,
            similarity_threshold=similarity_threshold,
        )
        self.deck_state: Optional[TournamentDeckState] = None

    def initialize_deck(self, source_path: Optional[str] = None) -> TournamentDeckState:
        """Load tournament deck state from file or initialize empty deck."""
        target_path = source_path or self.deck_file
        if os.path.exists(target_path):
            logger.info("Loading existing tournament deck from %s", target_path)
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.deck_state = TournamentDeckState.model_validate(data)
        else:
            logger.info("Initializing new deck at %s", target_path)
            self.deck_state = TournamentDeckState(
                epoch=1,
                total_cards=0,
                cards={},
            )
        return self.deck_state

    def save_deck_state(self, target_path: Optional[str] = None) -> None:
        """Persist deck state to disk."""
        if not self.deck_state:
            return
        path = target_path or self.deck_file
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.deck_state.model_dump_json(indent=2))

    def evaluate_response(
        self,
        card: EvaluationCard,
        agent_response: str,
    ) -> Tuple[bool, float, str]:
        """Judge an agent response against ground-truth card."""
        return self.judge.evaluate(card, agent_response)

    async def run_round(
        self,
        round_num: int,
        agent_invoker: Callable[[str], Any],
        cards_to_eval: List[EvaluationCard],
        concurrency: int = 5,
    ) -> TournamentRoundStats:
        """Execute a single evaluation round across a batch of cards."""
        start_time = datetime.utcnow().isoformat()
        semaphore = asyncio.Semaphore(concurrency)
        correct_count = 0
        incorrect_count = 0
        incorrect_ids: List[str] = []
        domain_stats: Dict[str, Dict[str, Any]] = {}

        async def _eval_one(card: EvaluationCard) -> CardAttempt:
            nonlocal correct_count, incorrect_count
            async with semaphore:
                t0 = time.time()
                # Check CAG cache first
                cag_hit = self.calibration.lookup_calibrated_fact(card.question)
                if cag_hit:
                    agent_text = cag_hit["expected_answer"]
                    model_used = "cag_calibration_cache"
                    tools = ["cag_cache_lookup"]
                else:
                    try:
                        res = agent_invoker(card.question)
                        if asyncio.iscoroutine(res):
                            res = await res
                        if isinstance(res, dict):
                            agent_text = res.get("response", str(res))
                            model_used = res.get("model", "target_agent")
                            tools = res.get("tools", [])
                        else:
                            agent_text = str(res)
                            model_used = "target_agent"
                            tools = []
                    except Exception as exc:
                        logger.error("Agent execution error on card %s: %s", card.card_id, exc)
                        agent_text = f"Error: {exc}"
                        model_used = "error"
                        tools = []

                latency_ms = int((time.time() - t0) * 1000)
                is_correct, score, reason = self.judge.evaluate(card, agent_text)

                attempt = CardAttempt(
                    round_num=round_num,
                    question=card.question,
                    agent_response=agent_text,
                    model_used=model_used,
                    tools_executed=tools,
                    is_correct=is_correct,
                    score=score,
                    reason=reason,
                    latency_ms=latency_ms,
                )
                card.attempts.append(attempt)

                if is_correct:
                    card.status = "correct"
                    correct_count += 1
                else:
                    card.status = "incorrect"
                    incorrect_count += 1
                    incorrect_ids.append(card.card_id)

                dom = card.domain
                if dom not in domain_stats:
                    domain_stats[dom] = {"total": 0, "correct": 0, "incorrect": 0}
                domain_stats[dom]["total"] += 1
                if is_correct:
                    domain_stats[dom]["correct"] += 1
                else:
                    domain_stats[dom]["incorrect"] += 1

                return attempt

        await asyncio.gather(*[_eval_one(c) for c in cards_to_eval])

        total_evaluated = len(cards_to_eval)
        acc_pct = (correct_count / total_evaluated * 100.0) if total_evaluated > 0 else 0.0

        for d_info in domain_stats.values():
            d_total = d_info["total"]
            d_info["accuracy_pct"] = (d_info["correct"] / d_total * 100.0) if d_total > 0 else 0.0

        round_stat = TournamentRoundStats(
            round_num=round_num,
            started_at=start_time,
            completed_at=datetime.utcnow().isoformat(),
            total_cards=len(self.deck_state.cards) if self.deck_state else total_evaluated,
            cards_evaluated=total_evaluated,
            correct_cards=correct_count,
            incorrect_cards=incorrect_count,
            accuracy_pct=round(acc_pct, 2),
            domain_breakdown=domain_stats,
            calibrated_before_round=self.calibration.count,
            incorrect_card_ids=incorrect_ids,
        )

        if self.deck_state:
            self.deck_state.rounds.append(round_stat)
            self.deck_state.current_round = round_num

        return round_stat

    def calibrate_missed_cards(self, incorrect_card_ids: List[str]) -> int:
        """Calibrate missed cards into active CAG memory."""
        if not self.deck_state:
            return 0
        missed = [self.deck_state.cards[cid] for cid in incorrect_card_ids if cid in self.deck_state.cards]
        calibrated_count = self.calibration.calibrate_cards(missed)
        for c in missed:
            c.calibrated = True
        return calibrated_count

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """Synthesize markdown benchmark convergence report."""
        if not self.deck_state or not self.deck_state.rounds:
            report_text = f"# Hath0r Gameshow Benchmark Report\n\nDeck loaded ({len(self.deck_state.cards) if self.deck_state else 0} cards), no tournament rounds executed yet."
            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report_text)
            return report_text

        lines = [
            f"# Hath0r Gameshow Continuous Calibration Benchmark Report — Epoch {self.deck_state.epoch}",
            "",
            f"- **Generated:** {datetime.utcnow().isoformat()}Z",
            f"- **Total Cards in Deck:** {len(self.deck_state.cards):,}",
            f"- **Rounds Completed:** {len(self.deck_state.rounds)}",
            f"- **Active CAG Ground Truth Memories:** {self.calibration.count:,}",
            "",
            "## Tournament Progression by Round",
            "",
            "| Round | Cards Evaluated | Correct | Incorrect | Accuracy % | Active CAG Memories |",
            "|---|---|---|---|---|---|",
        ]

        for r in self.deck_state.rounds:
            lines.append(
                f"| Round {r.round_num} | {r.cards_evaluated:,} | {r.correct_cards:,} | {r.incorrect_cards:,} | **{r.accuracy_pct:.2f}%** | {r.calibrated_before_round:,} |"
            )

        report_text = "\n".join(lines)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            logger.info("Saved tournament report to %s", output_path)

        return report_text


gameshow_managing_bot = HathorGameshowBot()
