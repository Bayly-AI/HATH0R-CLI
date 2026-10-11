"""Task-Level Planning (TLP) DAG Engine and Decomposer."""

from __future__ import annotations

import datetime
import uuid
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TaskStatus(str, Enum):
    """Execution status of a task node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    """Individual node within a Task Execution DAG."""

    id: str
    title: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    estimated_tokens: int = 1500
    status: TaskStatus = TaskStatus.PENDING
    output: Optional[Any] = None
    error: Optional[str] = None
    assigned_thread_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskNode:
        payload = dict(data)
        if "status" in payload:
            payload["status"] = TaskStatus(payload["status"])
        return cls(**payload)


@dataclass
class TaskExecutionDAG:
    """Directed Acyclic Graph of structured tasks."""

    dag_id: str
    goal: str
    nodes: Dict[str, TaskNode] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: TaskNode) -> None:
        self.nodes[node.id] = node

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dag_id": self.dag_id,
            "goal": self.goal,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TaskExecutionDAG:
        nodes = {k: TaskNode.from_dict(v) for k, v in data.get("nodes", {}).items()}
        return cls(
            dag_id=data["dag_id"],
            goal=data["goal"],
            nodes=nodes,
            created_at=data.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            metadata=data.get("metadata", {}),
        )


class TaskLevelPlannerBot:
    """Bot responsible for Goal Decomposition, DAG Synthesis, and Dynamic Replanning."""

    def __init__(self) -> None:
        pass

    def create_plan(
        self, goal: str, context: Optional[Dict[str, Any]] = None
    ) -> TaskExecutionDAG:
        """Decompose a macro-goal into a structured TaskExecutionDAG with dependency tiers."""
        dag_id = f"dag-{uuid.uuid4().hex[:8]}"
        dag = TaskExecutionDAG(dag_id=dag_id, goal=goal, metadata=context or {})

        goal_lower = goal.lower()

        # Heuristic archetype decomposition
        if "clean" in goal_lower and "repo" in goal_lower:
            dag.add_node(
                TaskNode(
                    id="scan_repos",
                    title="Scan Member Repositories",
                    description="Discover all sibling repositories and inspect git statuses.",
                    depends_on=[],
                    required_tools=["view_file", "run_command"],
                    estimated_tokens=800,
                )
            )
            dag.add_node(
                TaskNode(
                    id="clean_artifacts",
                    title="Clean Development Artifacts",
                    description="Purge temporary pytest caches, OS metadata, and python bytecode.",
                    depends_on=["scan_repos"],
                    required_tools=["run_command"],
                    estimated_tokens=500,
                )
            )
            dag.add_node(
                TaskNode(
                    id="audit_branches",
                    title="Audit and Prune Stale Branches",
                    description="Scan merged pull requests and delete merged feature branches.",
                    depends_on=["scan_repos"],
                    required_tools=["run_command"],
                    estimated_tokens=1000,
                )
            )
            dag.add_node(
                TaskNode(
                    id="sync_knowledge",
                    title="Synchronize AgentGraph & KB",
                    description="Sync AgentGraph topology and verify documentation indexes.",
                    depends_on=["clean_artifacts", "audit_branches"],
                    required_tools=["run_command", "view_file"],
                    estimated_tokens=1200,
                )
            )
            dag.add_node(
                TaskNode(
                    id="verify_health",
                    title="Verify Suite Health",
                    description="Execute doctor health audit and confirm clean trees.",
                    depends_on=["sync_knowledge"],
                    required_tools=["run_command"],
                    estimated_tokens=800,
                )
            )
        elif "deploy" in goal_lower or "release" in goal_lower:
            dag.add_node(
                TaskNode(
                    id="preflight_check",
                    title="Run Preflight Validation",
                    description="Execute contracts and quality gate validation.",
                    depends_on=[],
                    required_tools=["run_command"],
                    estimated_tokens=1000,
                )
            )
            dag.add_node(
                TaskNode(
                    id="run_tests",
                    title="Run Test Suites",
                    description="Execute unit and integration tests across target packages.",
                    depends_on=["preflight_check"],
                    required_tools=["run_command"],
                    estimated_tokens=2500,
                )
            )
            dag.add_node(
                TaskNode(
                    id="verify_temporal_policy",
                    title="Verify Temporal Promotion Policy",
                    description="Verify CR-BAI-001 promotion invariants and calibration limits.",
                    depends_on=["preflight_check"],
                    required_tools=["view_file"],
                    estimated_tokens=1200,
                )
            )
            dag.add_node(
                TaskNode(
                    id="build_artifacts",
                    title="Build Release Artifacts",
                    description="Package release binaries, Docker images, and manifests.",
                    depends_on=["run_tests", "verify_temporal_policy"],
                    required_tools=["run_command"],
                    estimated_tokens=3000,
                )
            )
            dag.add_node(
                TaskNode(
                    id="deploy_environment",
                    title="Deploy to Target Environment",
                    description="Promote artifacts to next canonical environment.",
                    depends_on=["build_artifacts"],
                    required_tools=["run_command"],
                    estimated_tokens=1500,
                )
            )
        else:
            # General Macro-Task Decomposition
            dag.add_node(
                TaskNode(
                    id="analyze_requirements",
                    title="Analyze Task Requirements",
                    description=f"Inspect workspace and contracts for: '{goal}'",
                    depends_on=[],
                    required_tools=["view_file", "search_code"],
                    estimated_tokens=1200,
                )
            )
            dag.add_node(
                TaskNode(
                    id="scaffold_implementation",
                    title="Implement Core Solution",
                    description="Write production code, models, and interfaces.",
                    depends_on=["analyze_requirements"],
                    required_tools=["replace_file_content", "write_to_file"],
                    estimated_tokens=3500,
                )
            )
            dag.add_node(
                TaskNode(
                    id="author_tests",
                    title="Author Comprehensive Tests",
                    description="Create unit and integration tests verifying acceptance criteria.",
                    depends_on=["analyze_requirements"],
                    required_tools=["write_to_file"],
                    estimated_tokens=2000,
                )
            )
            dag.add_node(
                TaskNode(
                    id="validate_and_verify",
                    title="Run Quality Gates and Verification",
                    description="Execute pytest, linters, and schema contract validators.",
                    depends_on=["scaffold_implementation", "author_tests"],
                    required_tools=["run_command"],
                    estimated_tokens=1500,
                )
            )
            dag.add_node(
                TaskNode(
                    id="document_changes",
                    title="Update Documentation & Runbooks",
                    description="Document new capabilities, runbooks, and API specs.",
                    depends_on=["validate_and_verify"],
                    required_tools=["replace_file_content", "write_to_file"],
                    estimated_tokens=1800,
                )
            )

        return dag

    def detect_cycles(self, dag: TaskExecutionDAG) -> Tuple[bool, List[str]]:
        """Detect circular dependencies using Kahn's algorithm."""
        in_degree = {nid: 0 for nid in dag.nodes}
        adj = defaultdict(list)

        for nid, node in dag.nodes.items():
            for dep in node.depends_on:
                if dep in in_degree:
                    adj[dep].append(nid)
                    in_degree[nid] += 1

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(dag.nodes):
            unresolved = [nid for nid, deg in in_degree.items() if deg > 0]
            return True, unresolved
        return False, []

    def topological_sort(self, dag: TaskExecutionDAG) -> List[List[str]]:
        """Group DAG nodes into concurrent execution tiers."""
        has_cycle, unresolved = self.detect_cycles(dag)
        if has_cycle:
            raise ValueError(f"Cannot sort cyclic DAG; unresolved nodes: {unresolved}")

        in_degree = {nid: 0 for nid in dag.nodes}
        adj = defaultdict(list)

        for nid, node in dag.nodes.items():
            for dep in node.depends_on:
                adj[dep].append(nid)
                in_degree[nid] += 1

        tiers: List[List[str]] = []
        current_tier = [nid for nid, deg in in_degree.items() if deg == 0]

        while current_tier:
            tiers.append(sorted(current_tier))
            next_tier = []
            for nid in current_tier:
                for neighbor in adj[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_tier.append(neighbor)
            current_tier = next_tier

        return tiers

    def replan_on_failure(
        self, dag: TaskExecutionDAG, failed_node_id: str, error_message: str
    ) -> TaskExecutionDAG:
        """Dynamic Replanning: Handle subtask failure by injecting remediation node and rewiring dependencies."""
        if failed_node_id not in dag.nodes:
            raise KeyError(f"Task node '{failed_node_id}' not found in DAG.")

        failed_node = dag.nodes[failed_node_id]
        failed_node.status = TaskStatus.FAILED
        failed_node.error = error_message

        # Identify downstream dependents that need remediation
        downstream = [
            nid for nid, node in dag.nodes.items() if failed_node_id in node.depends_on
        ]

        # Inject remediation node
        remediation_id = f"remediate_{failed_node_id}"
        remediation_node = TaskNode(
            id=remediation_id,
            title=f"Remediate: {failed_node.title}",
            description=f"Automated remediation following failure in '{failed_node.title}': {error_message}",
            depends_on=[failed_node_id],
            required_tools=["replace_file_content", "run_command"],
            estimated_tokens=2000,
            status=TaskStatus.PENDING,
        )
        dag.add_node(remediation_node)

        # Rewire downstream nodes to depend on remediation node instead of failed node
        for child_id in downstream:
            child = dag.nodes[child_id]
            child.depends_on = [
                remediation_id if d == failed_node_id else d for d in child.depends_on
            ]
            child.status = TaskStatus.PENDING

        return dag

    def export_mermaid(self, dag: TaskExecutionDAG) -> str:
        """Generate a Mermaid diagram representing the DAG."""
        lines = ["flowchart TD"]
        status_styles = {
            TaskStatus.PENDING: "fill:#2b2d42,stroke:#8d99ae,stroke-width:1px,color:#edf2f4",
            TaskStatus.RUNNING: "fill:#023e8a,stroke:#0077b6,stroke-width:2px,color:#caf0f8",
            TaskStatus.COMPLETED: "fill:#2d6a4f,stroke:#52b788,stroke-width:2px,color:#d8f3dc",
            TaskStatus.FAILED: "fill:#780000,stroke:#c1121f,stroke-width:2px,color:#fdf0d5",
            TaskStatus.SKIPPED: "fill:#343a40,stroke:#6c757d,stroke-width:1px,color:#adb5bd",
        }

        for nid, node in sorted(dag.nodes.items()):
            label = f"{node.title}\\n({node.status.value})"
            lines.append(f'    {nid}["{label}"]')

        for nid, node in sorted(dag.nodes.items()):
            for dep in sorted(node.depends_on):
                lines.append(f"    {dep} --> {nid}")

        lines.append("")
        for nid, node in sorted(dag.nodes.items()):
            style = status_styles.get(node.status, "")
            if style:
                lines.append(f"    style {nid} {style}")

        return "\n".join(lines)


# Global singleton
task_level_planner = TaskLevelPlannerBot()
