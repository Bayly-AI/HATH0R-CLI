"""Thread-Level Parallelism (TLP) Concurrent Execution Engine."""

from __future__ import annotations

import concurrent.futures
import datetime
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .task_level_planner_bot import TaskExecutionDAG, TaskNode, TaskStatus, task_level_planner


@dataclass
class ThreadContext:
    """Isolated execution context and scratchpad for an individual thread."""

    thread_id: str
    scratchpad: Dict[str, Any] = field(default_factory=dict)
    token_budget: int = 25000
    tokens_used: int = 0
    cost_usd: float = 0.0
    call_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def record_usage(self, tokens: int, cost: float = 0.0) -> None:
        self.tokens_used += tokens
        self.cost_usd += cost

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThreadExecutionRecord:
    """Telemetry report for a single thread execution run."""

    thread_id: str
    node_id: str
    status: str
    latency_ms: float
    tokens_used: int
    cost_usd: float
    output: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ThreadLevelParallelismBot:
    """Orchestrates concurrent execution of Task DAGs with context isolation and join barriers."""

    COST_PER_1K_TOKENS = 0.002

    def __init__(self) -> None:
        pass

    def default_executor(self, node: TaskNode, ctx: ThreadContext) -> Any:
        """Default synthetic executor simulating tool invocation and AST analysis."""
        # Simulated workload with predictable token metrics
        tokens = node.estimated_tokens
        cost = (tokens / 1000.0) * self.COST_PER_1K_TOKENS
        ctx.record_usage(tokens=tokens, cost=cost)

        ctx.call_history.append(
            {
                "tool": node.required_tools[0] if node.required_tools else "generic_task",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "node_id": node.id,
            }
        )
        return {
            "status": "completed",
            "message": f"Successfully executed task '{node.title}' in isolated thread '{ctx.thread_id}'",
            "tools_called": node.required_tools,
        }

    def execute_node_thread(
        self,
        node: TaskNode,
        executor: Callable[[TaskNode, ThreadContext], Any],
        timeout: int,
    ) -> ThreadExecutionRecord:
        """Execute a single task node inside an isolated worker thread."""
        thread_id = f"tlp-th-{uuid.uuid4().hex[:8]}"
        ctx = ThreadContext(thread_id=thread_id, token_budget=node.estimated_tokens * 2)
        node.assigned_thread_id = thread_id
        node.status = TaskStatus.RUNNING

        start = time.perf_counter()
        try:
            output = executor(node, ctx)
            latency = (time.perf_counter() - start) * 1000.0
            node.status = TaskStatus.COMPLETED
            node.output = output

            return ThreadExecutionRecord(
                thread_id=thread_id,
                node_id=node.id,
                status="completed",
                latency_ms=round(latency, 2),
                tokens_used=ctx.tokens_used,
                cost_usd=round(ctx.cost_usd, 6),
                output=output,
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            node.status = TaskStatus.FAILED
            node.error = str(exc)

            return ThreadExecutionRecord(
                thread_id=thread_id,
                node_id=node.id,
                status="failed",
                latency_ms=round(latency, 2),
                tokens_used=ctx.tokens_used,
                cost_usd=round(ctx.cost_usd, 6),
                error=str(exc),
            )

    def run_parallel_dag(
        self,
        dag: TaskExecutionDAG,
        max_workers: int = 4,
        timeout_per_step: int = 60,
        executor: Optional[Callable[[TaskNode, ThreadContext], Any]] = None,
        auto_replan: bool = True,
    ) -> Dict[str, Any]:
        """Execute a Task DAG across concurrent threads using topological barrier tiers."""
        task_fn = executor or self.default_executor
        tiers = task_level_planner.topological_sort(dag)

        overall_start = time.perf_counter()
        execution_records: List[ThreadExecutionRecord] = []
        total_tokens = 0
        total_cost = 0.0

        for tier_idx, tier_node_ids in enumerate(tiers):
            tier_nodes = [dag.nodes[nid] for nid in tier_node_ids if dag.nodes[nid].status == TaskStatus.PENDING]
            if not tier_nodes:
                continue

            # Fan-out: execute all independent nodes in this tier concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tier_nodes), max_workers)) as pool:
                futures = {
                    pool.submit(self.execute_node_thread, node, task_fn, timeout_per_step): node
                    for node in tier_nodes
                }

                # Fan-in barrier: wait for tier completion
                tier_failed = False
                for future in concurrent.futures.as_completed(futures):
                    record = future.result()
                    execution_records.append(record)
                    total_tokens += record.tokens_used
                    total_cost += record.cost_usd

                    if record.status == "failed":
                        tier_failed = True
                        if auto_replan:
                            task_level_planner.replan_on_failure(
                                dag=dag,
                                failed_node_id=record.node_id,
                                error_message=record.error or "Unknown failure",
                            )

                if tier_failed and not auto_replan:
                    # Halt downstream tiers
                    for subsequent_tier in tiers[tier_idx + 1:]:
                        for nid in subsequent_tier:
                            dag.nodes[nid].status = TaskStatus.SKIPPED
                    break

        total_latency = (time.perf_counter() - overall_start) * 1000.0

        completed_count = sum(1 for n in dag.nodes.values() if n.status == TaskStatus.COMPLETED)
        failed_count = sum(1 for n in dag.nodes.values() if n.status == TaskStatus.FAILED)

        return {
            "dag_id": dag.dag_id,
            "goal": dag.goal,
            "success": failed_count == 0,
            "completed_nodes": completed_count,
            "failed_nodes": failed_count,
            "total_nodes": len(dag.nodes),
            "total_latency_ms": round(total_latency, 2),
            "finops": {
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 6),
            },
            "records": [r.to_dict() for r in execution_records],
        }


# Global singleton
thread_parallelism = ThreadLevelParallelismBot()
