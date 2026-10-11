# Playbook: TLP Troubleshooting & Anomaly Diagnostics

> Artifact: **Playbook** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `tlp-troubleshooting-playbook`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#426  
> Date: 2026-10-11

## 1. Purpose

This playbook provides actionable recovery steps for common failures encountered during Task DAG synthesis, thread execution, and temporal automata verification.

---

## 2. Common Scenarios & Resolutions

### Scenario A: Cyclic Dependency in Task DAG
- **Symptom**: `ValueError: Cannot sort cyclic DAG; unresolved nodes: ['A', 'B']`
- **Cause**: Node A depends on Node B, and Node B depends on Node A.
- **Resolution**:
  1. Inspect the exported Mermaid graph: `hath0r tlp plan --goal "..." --format mermaid`.
  2. Locate circular arrow loops.
  3. Decompose the shared dependency into an intermediate prerequisite node.

### Scenario B: Temporal DFA Violation (`S_TRAP`)
- **Symptom**: `Transitioned into rejecting trap state 'S_TRAP' on symbol 'staging'`
- **Cause**: The execution attempted to skip a mandatory intermediate environment (violating `CR-BAI-001` or `CR-HATH0R-INIT-001`).
- **Resolution**:
  1. Inspect the full state trace reported by `hath0r tlp verify`.
  2. Insert missing predecessor tasks (`testing`, `check_playbook`, `check_runbook`).
  3. Re-run verification until DFA reaches accepting state.

### Scenario C: Thread Execution Timeout
- **Symptom**: Step marked `FAILED` with timeout exceeded.
- **Cause**: Tool invocation exceeded default 60s timeout budget.
- **Resolution**:
  1. Increase timeout flag: `hath0r tlp run --timeout 120`.
  2. Split long-running tasks into smaller, fine-grained tasks in the Task DAG.
