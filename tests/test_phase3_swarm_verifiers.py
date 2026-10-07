"""Unit & Integration Tests for Phase 3: Token Tree Budget, Consensus Engine, Antagonistic Review, and Red-Team Engine."""

from __future__ import annotations

import pytest
from click.testing import CliRunner
from hath0r_cli.cli import main
from hath0r_cli.bots.token_tree_budget import TokenTreeBudgetGuard, TokenBudgetExceeded
from hath0r_cli.bots.multiagent_consensus import MultiAgentConsensusEngine
from hath0r_cli.bots.antagonistic_review import AntagonisticReviewBot
from hath0r_cli.bots.redteam_engine import MultiAgentRedTeamEngine


def test_token_tree_budget_guard():
    guard = TokenTreeBudgetGuard(max_tokens_budget=1000, max_usd_budget=0.01)

    status1 = guard.record_usage("tree-1", prompt_tokens=100, completion_tokens=50)
    assert status1["total_tokens"] == 150

    chk = guard.check_budget("tree-1")
    assert chk["remaining_tokens"] == 850

    with pytest.raises(TokenBudgetExceeded):
        guard.record_usage("tree-1", prompt_tokens=1000, completion_tokens=500)


def test_multiagent_consensus_engine():
    engine = MultiAgentConsensusEngine(consensus_threshold=0.70)
    responses = [
        {"agent_id": "a1", "output": "pass"},
        {"agent_id": "a2", "output": "pass"},
        {"agent_id": "a3", "output": "fail"},
    ]
    res = engine.evaluate_consensus(responses)
    assert res["consensus_score"] == 0.67
    assert res["passed_gate"] is False
    assert res["fallback_human_in_loop_required"] is True

    responses_pass = [
        {"agent_id": "a1", "output": "pass"},
        {"agent_id": "a2", "output": "pass"},
        {"agent_id": "a3", "output": "pass"},
    ]
    res2 = engine.evaluate_consensus(responses_pass)
    assert res2["consensus_score"] == 1.0
    assert res2["passed_gate"] is True


def test_antagonistic_review_bot(tmp_path):
    bot = AntagonisticReviewBot(root_path=tmp_path)

    # Test diff with swallowed exception & TODO tech debt
    diff_sample = """
+ def broken_function():
+     # TODO: refactor temporary workaround
+     try:
+         do_something()
+     except Exception:
+         pass
"""
    res = bot.review_diff(diff_content=diff_sample)
    assert res["passed_gate"] is False
    assert res["adversarial_flaws_count"] >= 1
    assert res["tech_debts_count"] >= 1


def test_antagonistic_review_bot_ignores_regex_definitions(tmp_path):
    bot = AntagonisticReviewBot(root_path=tmp_path)
    diff_sample = """
+ tech_match = re.search(r"\\b(TODO|FIXME|HACK|XXX|STUB)\\b:?\\s*(\\S.*)?", line)
"""
    res = bot.review_diff(diff_content=diff_sample)
    assert res["passed_gate"] is True
    assert res["tech_debts_count"] == 0


def test_multiagent_redteam_engine(tmp_path):
    engine = MultiAgentRedTeamEngine(workspace_root=tmp_path)
    res = engine.run_redteam_verification("test_module")
    assert res["status"] == "passed"
    assert res["survival_gate"] == "PASSED_100_PERCENT"
    assert (tmp_path / "tests" / "adversarial" / "test_redteam_test_module.py").exists()


def test_phase3_cli_commands():
    runner = CliRunner()

    res_budget = runner.invoke(main, ["--output", "json", "finops", "budget", "check"])
    assert res_budget.exit_code == 0

    res_consensus = runner.invoke(main, ["--output", "json", "evals", "consensus"])
    assert res_consensus.exit_code == 0

    res_redteam = runner.invoke(main, ["--output", "json", "evals", "redteam"])
    assert res_redteam.exit_code == 0

    res_pr_review = runner.invoke(main, ["--output", "json", "pr", "review", "--antagonistic"])
    assert res_pr_review.exit_code == 0
