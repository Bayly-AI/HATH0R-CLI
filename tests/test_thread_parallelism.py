"""Unit tests for ThreadLevelParallelismBot (TLP Thread-Level Parallelism)."""

from __future__ import annotations

import pytest

from hath0r_cli.bots.task_level_planner_bot import TaskLevelPlannerBot
from hath0r_cli.bots.thread_parallelism_bot import (
    ThreadContext,
    ThreadLevelParallelismBot,
)


@pytest.fixture
def tlp_bot() -> ThreadLevelParallelismBot:
    return ThreadLevelParallelismBot()


@pytest.fixture
def planner() -> TaskLevelPlannerBot:
    return TaskLevelPlannerBot()


def test_thread_context_isolation(tlp_bot: ThreadLevelParallelismBot) -> None:
    ctx1 = ThreadContext(thread_id="th-1")
    ctx2 = ThreadContext(thread_id="th-2")

    ctx1.record_usage(tokens=500, cost=0.001)
    ctx1.scratchpad["key"] = "val1"

    ctx2.record_usage(tokens=1000, cost=0.002)
    ctx2.scratchpad["key"] = "val2"

    assert ctx1.tokens_used == 500
    assert ctx2.tokens_used == 1000
    assert ctx1.scratchpad["key"] == "val1"
    assert ctx2.scratchpad["key"] == "val2"


def test_run_parallel_dag_success(
    tlp_bot: ThreadLevelParallelismBot, planner: TaskLevelPlannerBot
) -> None:
    dag = planner.create_plan(goal="Deploy release package")
    result = tlp_bot.run_parallel_dag(dag=dag, max_workers=2)

    assert result["success"] is True
    assert result["completed_nodes"] == result["total_nodes"]
    assert result["finops"]["total_tokens"] > 0
    assert len(result["records"]) == result["total_nodes"]
    for record in result["records"]:
        assert record["status"] == "completed"
        assert record["thread_id"].startswith("tlp-th-")


def test_run_parallel_dag_with_custom_executor(
    tlp_bot: ThreadLevelParallelismBot, planner: TaskLevelPlannerBot
) -> None:
    dag = planner.create_plan(goal="Clean member repositories")

    called_nodes = []

    def custom_fn(node, ctx):
        called_nodes.append(node.id)
        ctx.record_usage(100, 0.0002)
        return {"custom": True, "id": node.id}

    result = tlp_bot.run_parallel_dag(dag=dag, executor=custom_fn, max_workers=4)

    assert result["success"] is True
    assert set(called_nodes) == set(dag.nodes.keys())
    assert result["finops"]["total_tokens"] == len(dag.nodes) * 100
