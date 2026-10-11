"""Unit tests for TaskLevelPlannerBot (TLP Task-Level Planning)."""

from __future__ import annotations

import pytest

from hath0r_cli.bots.task_level_planner_bot import (
    TaskExecutionDAG,
    TaskLevelPlannerBot,
    TaskNode,
    TaskStatus,
)


@pytest.fixture
def planner() -> TaskLevelPlannerBot:
    return TaskLevelPlannerBot()


def test_create_plan_general(planner: TaskLevelPlannerBot) -> None:
    dag = planner.create_plan(goal="Implement OAuth2 Authentication Provider")
    assert dag.dag_id.startswith("dag-")
    assert len(dag.nodes) >= 4
    assert "analyze_requirements" in dag.nodes
    assert "scaffold_implementation" in dag.nodes
    assert "author_tests" in dag.nodes
    assert "validate_and_verify" in dag.nodes
    assert "document_changes" in dag.nodes


def test_create_plan_clean_repos(planner: TaskLevelPlannerBot) -> None:
    dag = planner.create_plan(goal="Clean member repositories across suite")
    assert "scan_repos" in dag.nodes
    assert "clean_artifacts" in dag.nodes
    assert "audit_branches" in dag.nodes
    assert "sync_knowledge" in dag.nodes
    assert "verify_health" in dag.nodes


def test_topological_sort_and_tiers(planner: TaskLevelPlannerBot) -> None:
    dag = planner.create_plan(goal="Clean member repositories across suite")
    tiers = planner.topological_sort(dag)
    assert len(tiers) >= 3
    # First tier must be scan_repos
    assert tiers[0] == ["scan_repos"]
    # Second tier must have both clean_artifacts and audit_branches
    assert sorted(tiers[1]) == ["audit_branches", "clean_artifacts"]


def test_cycle_detection(planner: TaskLevelPlannerBot) -> None:
    dag = TaskExecutionDAG(dag_id="cyclic-dag", goal="Cycle Test")
    node_a = TaskNode(id="A", title="Node A", description="", depends_on=["B"])
    node_b = TaskNode(id="B", title="Node B", description="", depends_on=["A"])
    dag.add_node(node_a)
    dag.add_node(node_b)

    has_cycle, unresolved = planner.detect_cycles(dag)
    assert has_cycle is True
    assert set(unresolved) == {"A", "B"}

    with pytest.raises(ValueError, match="Cannot sort cyclic DAG"):
        planner.topological_sort(dag)


def test_dynamic_replanning(planner: TaskLevelPlannerBot) -> None:
    dag = planner.create_plan(goal="Refactor backend service")
    assert "scaffold_implementation" in dag.nodes

    # Trigger failure on scaffold_implementation
    repaired_dag = planner.replan_on_failure(
        dag=dag,
        failed_node_id="scaffold_implementation",
        error_message="SyntaxError on line 42",
    )
    assert dag.nodes["scaffold_implementation"].status == TaskStatus.FAILED
    assert "remediate_scaffold_implementation" in repaired_dag.nodes
    remediation_node = repaired_dag.nodes["remediate_scaffold_implementation"]
    assert remediation_node.depends_on == ["scaffold_implementation"]

    # Dependent validate_and_verify should now depend on remediation node
    val_node = repaired_dag.nodes["validate_and_verify"]
    assert "remediate_scaffold_implementation" in val_node.depends_on


def test_export_mermaid(planner: TaskLevelPlannerBot) -> None:
    dag = planner.create_plan(goal="Refactor API")
    mermaid = planner.export_mermaid(dag)
    assert mermaid.startswith("flowchart TD")
    assert "analyze_requirements" in mermaid
    assert "-->" in mermaid
