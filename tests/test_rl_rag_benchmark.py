"""Unit tests for RL-RAG Reward Evaluator and Benchmark Harness."""

from __future__ import annotations

from hath0r_cli.cccd.rl_rag_eval import RLRAGBenchmarkHarness, RLRAGRewardEvaluator


def test_rl_rag_reward_evaluator() -> None:
    evaluator = RLRAGRewardEvaluator()
    res = evaluator.calculate_reward(accuracy=1.0, tokens_used=500, latency_ms=50.0, constraint_violated=False)

    assert "total_reward" in res
    assert res["total_reward"] > 0.5
    assert res["components"]["r_accuracy"] == 1.0


def test_rl_rag_benchmark_harness() -> None:
    harness = RLRAGBenchmarkHarness()
    sample_dataset = [
        {"input": "query 1"},
        {"input": "query 2"},
    ]

    benchmark_res = harness.run_benchmark(sample_dataset)

    assert benchmark_res["success"] is True
    assert benchmark_res["total_samples"] == 2
    assert benchmark_res["rl_guided"]["mean_reward"] > benchmark_res["static_baseline"]["mean_reward"]
    assert benchmark_res["delta"]["token_savings_pct"] > 40.0
