# Workflow: TLP Tri-Paradigm Orchestration Workflow

> Artifact: **Workflow** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `tlp-orchestration-workflow`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#426  
> Date: 2026-10-11

## 1. Workflow Architecture

The TLP Orchestration Workflow executes the canonical 4-stage lifecycle:
1. **Decomposition**: `TaskLevelPlannerBot.create_plan()` generates a multi-tier DAG.
2. **Formal Verification**: `TemporalLogicPlannerBot.verify_trace()` validates policy invariants against automata.
3. **Parallel Dispatch**: `ThreadLevelParallelismBot.run_parallel_dag()` dispatches tier-by-tier concurrently.
4. **Telemetry & Consolidation**: Summarizes runtime latency, tokens consumed, and state changes.

---

## 2. Declarative Schema

The workflow binds to `cfg/workflows/tlp-dag-workflow.yaml`:
```yaml
schema_version: "hath0r.tlp.workflow/1"
workflow_id: "tlp-canonical-orchestration"
description: "Canonical Task-Level, Thread-Level, and Temporal Logic Planning Execution Pipeline"
stages:
  - id: plan_synthesis
    bot: TaskLevelPlannerBot
    action: create_plan
  - id: temporal_verification
    bot: TemporalLogicPlannerBot
    action: verify_trace
  - id: parallel_execution
    bot: ThreadLevelParallelismBot
    action: run_parallel_dag
```
