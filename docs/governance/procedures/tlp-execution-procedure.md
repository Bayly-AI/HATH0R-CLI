# Procedure: TLP Execution Procedure

> Artifact: **Procedure** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `tlp-execution-procedure`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#426  
> Date: 2026-10-11

## 1. Overview

This standard operating procedure defines the required steps for decomposing, concurrently executing, and formally verifying tasks using the Hath0r CLI TLP subsystem.

---

## 2. Step-by-Step Procedure

### Step 1: Goal Synthesis & DAG Planning
Run `hath0r tlp plan` to synthesize a Directed Acyclic Graph:
```bash
hath0r tlp plan --goal "<macro-objective>" --format text
```
- To serialize the plan to disk for durable pipeline execution:
```bash
hath0r tlp plan --goal "<macro-objective>" --output-file /path/to/dag.json
```

### Step 2: Policy & Invariant Pre-Verification
Verify the generated plan trajectory conforms to organizational temporal logic constraints:
```bash
hath0r tlp verify --plan /path/to/dag.json --policy all
```
Ensure all policies report `✓ Compliant`. If any policy reports `✗ Violates Policy`, do not execute the plan.

### Step 3: Concurrent Thread-Level Execution
Dispatch the task graph across isolated thread contexts:
```bash
hath0r tlp run --plan /path/to/dag.json --parallel --max-workers 4 --timeout 60
```
- Verify each independent execution tier succeeds.
- If a step fails, verify that dynamic replanning generated a remediation node.

### Step 4: Post-Execution Audit & Telemetry
Inspect total token consumption and FinOps cost reported in the execution summary.
