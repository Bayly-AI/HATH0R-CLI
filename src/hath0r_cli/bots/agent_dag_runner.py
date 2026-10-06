"""Multi-Agent Directed Acyclic Graph (DAG) Execution & Dependency Runner."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Tuple

from .hahp_protocol import HAHPEnvelope, hahp_manager
from .kv_prewarmer import kv_prewarmer


class AgentDAGRunner:
    """Multi-Agent DAG Runner supporting topological sorting, fan-out, fan-in barrier nodes, and HAHP handoffs."""

    def __init__(self) -> None:
        self._execution_history: List[Dict[str, Any]] = []

    def validate_dag(self, spec: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate DAG specification schema and ensure no cyclic dependencies."""
        if "nodes" not in spec:
            return False, "DAG spec missing 'nodes' key."

        nodes = spec["nodes"]
        in_degree = {node["id"]: 0 for node in nodes}
        adj = defaultdict(list)

        for node in nodes:
            node_id = node["id"]
            deps = node.get("depends_on", [])
            for dep in deps:
                if dep not in in_degree:
                    return False, f"Node '{node_id}' depends on non-existent node '{dep}'."
                adj[dep].append(node_id)
                in_degree[node_id] += 1

        # Kahn's algorithm for cycle detection
        queue = deque([n for n, deg in in_degree.items() if deg == 0])
        visited_count = 0
        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(nodes):
            return False, "Cyclic dependency detected in agent DAG."

        return True, "Valid DAG."

    def execute_dag(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multi-agent DAG workflow spec."""
        is_valid, err_msg = self.validate_dag(spec)
        if not is_valid:
            return {"status": "error", "message": err_msg}

        start_time = time.perf_counter()
        dag_name = spec.get("name", "unnamed_agent_dag")
        nodes = {node["id"]: node for node in spec["nodes"]}

        # Build adjacency and dependency maps
        in_degree = {n_id: len(n.get("depends_on", [])) for n_id, n in nodes.items()}
        dependents = defaultdict(list)
        for n_id, n in nodes.items():
            for dep in n.get("depends_on", []):
                dependents[dep].append(n_id)

        # Pre-warm shared context if specified
        shared_sys_prompt = spec.get("shared_system_prompt", "Hath0r Canonical Agent")
        prewarm_res = kv_prewarmer.prewarm_context(shared_sys_prompt, system_prompt="hath0r_dag_prewarm")

        node_outputs: Dict[str, Any] = {}
        node_envelopes: Dict[str, HAHPEnvelope] = {}
        execution_order: List[str] = []

        ready_queue = deque([n_id for n_id, deg in in_degree.items() if deg == 0])

        while ready_queue:
            # Parallel batch execution level
            current_batch = list(ready_queue)
            ready_queue.clear()

            for node_id in current_batch:
                node = nodes[node_id]
                execution_order.append(node_id)

                # Gather inputs from dependencies
                dep_outputs = {dep: node_outputs[dep] for dep in node.get("depends_on", []) if dep in node_outputs}

                # Check if node is a barrier (fan-in)
                is_barrier = node.get("type") == "barrier" or len(node.get("depends_on", [])) > 1

                # Execute HAHP handoff envelope creation
                envelope = hahp_manager.create_envelope(
                    sender_agent=f"dag-parent-{node_id}",
                    recipient_agent=node.get("agent_role", f"agent-{node_id}"),
                    scratchpad_delta=f"DAG Node {node_id} execution in batch",
                    state_variables={"dep_outputs": dep_outputs, "is_barrier": is_barrier},
                )
                node_envelopes[node_id] = envelope

                # Simulated node output execution
                node_outputs[node_id] = {
                    "node_id": node_id,
                    "agent_role": node.get("agent_role", "default"),
                    "status": "completed",
                    "envelope_id": envelope.handoff_id,
                    "is_barrier": is_barrier,
                    "result": f"Executed node {node_id} with role {node.get('agent_role')}",
                }

                # Update dependent node degrees
                for child in dependents[node_id]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        ready_queue.append(child)

        total_elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        summary = {
            "status": "success",
            "dag_name": dag_name,
            "total_nodes": len(nodes),
            "execution_order": execution_order,
            "elapsed_ms": total_elapsed_ms,
            "prewarm_summary": prewarm_res,
            "node_outputs": node_outputs,
        }
        self._execution_history.append(summary)
        return summary


agent_dag_runner = AgentDAGRunner()
