"""#599: Tier 4 scores the change and the tiers' verdicts, so it can tell good work apart."""

from __future__ import annotations

import subprocess
from pathlib import Path

from hath0r_cli.bots.task_evaluator_bot import TaskEvaluatorBot


def _repo(root: Path, added: str) -> TaskEvaluatorBot:
    def git(*args: str) -> None:
        subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args], cwd=root, check=True, capture_output=True)

    git("init", "-q", "-b", "development")
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "base")
    (root / "calc.py").write_text("def add(a, b):\n    return a + b\n" + added, encoding="utf-8")
    return TaskEvaluatorBot(cwd=root)


PASS = {"passed": True}
FAIL = {"passed": False}


def test_goal_is_matched_against_the_change_not_memory(tmp_path):
    bot = _repo(tmp_path, "\ndef subtract(a, b):\n    return a - b\n")
    hit = bot._evaluate_tier4_goal_alignment(task_id="subtract-calc", issue_number=1, critics={"deterministic": PASS})
    miss = bot._evaluate_tier4_goal_alignment(task_id="multiply-matrix-calc", issue_number=1, critics={"deterministic": PASS})
    assert hit["goal_overlap_score"] == 1.0 and "subtract" in hit["goal_keywords_matched"]
    assert miss["goal_overlap_score"] < hit["goal_overlap_score"]
    assert miss["score"] < hit["score"]


def test_consensus_is_the_share_of_approving_critics(tmp_path):
    bot = _repo(tmp_path, "\ndef subtract(a, b):\n    return a - b\n")
    all_pass = bot._evaluate_tier4_goal_alignment(task_id="subtract", issue_number=None, critics={"deterministic": PASS, "trajectory": PASS, "adversarial": PASS})
    one_fail = bot._evaluate_tier4_goal_alignment(task_id="subtract", issue_number=None, critics={"deterministic": FAIL, "trajectory": PASS, "adversarial": PASS})
    assert all_pass["consensus_score"] == 1.0
    assert one_fail["consensus_score"] == 0.75
    assert one_fail["critic_votes"]["deterministic_critic"] == "fail"
    assert one_fail["score"] < all_pass["score"]


def test_unanimous_failure_is_not_scored_as_agreement(tmp_path):
    bot = _repo(tmp_path, "\nx = 1\n")
    res = bot._evaluate_tier4_goal_alignment(task_id="subtract", issue_number=None, critics={"deterministic": FAIL, "trajectory": FAIL, "adversarial": FAIL})
    assert res["consensus_score"] == 0.0 and res["raw_consensus"] == 1.0
