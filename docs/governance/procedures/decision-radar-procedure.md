# Procedure: Integrating & Operating the Hath0r Decision Radar

> Canonical Procedure · ID: `PROC-DECISION-RADAR-001`  
> Epic: #499 · Tasks: #500–#506

---

## 1. Purpose

Defines the step-by-step procedure for autonomous agents and human operators to queue decisions, bind declarative wait facts, enforce input/output work boundaries, and resolve items via the Minority Report Decision Radar.

---

## 2. Step-by-Step Procedure

### Step 1: Register Task Dependency Edges (Optional DAG Enrichment)
When multiple downstream tasks depend on upstream milestones, register edges so the transitive unblocking score $U(d)$ reflects the full cascade:
```bash
hath0r decision dep --from "schema-v2" --to "api-resolvers" --weight 1.5 --criticality 2.0
```

### Step 2: Enforce the Input Boundary Gate ("What Goes In")
Before starting a high-token multi-agent run, request or approve an Input Gate:
```bash
hath0r decision approve-in "@a11152" --intent "Migrate Parts-API schema" --budget 50000 --tools "read_file,edit_file,run_command"
```

### Step 3: Agent Requests a Decision or Waits on a Fact
From any agent terminal needing human guidance:
```bash
hath0r decision wait \
  --question "Confirm Parts-API build order: Widget search before index" \
  --category "set_product_rule" \
  --agent "@a3740" \
  --unblocks "@a6440,@a9094,search-indexer" \
  --fact "git.pr.merged:Bayly-AI/HATH0R-CLI#499" \
  --timeout 5.0
```

### Step 4: Operator Inspects & Resolves via Radar UI or CLI
1. Launch the Minority Report Radial Web Radar:
   ```bash
   hath0r decision radar --port 8085
   ```
   Or inspect in the terminal via Rich TUI:
   ```bash
   hath0r decision tui
   ```
2. Answer highest-$U(d)$ decision first:
   ```bash
   hath0r decision answer <decision-id> --response "Confirm build order: Widget search first"
   ```
3. Or snooze on a declarative fact (never a timer):
   ```bash
   hath0r decision snooze <decision-id> --fact "ci.workflow.passed:sonar-gate"
   ```

### Step 5: Auto-Settle Fact-Bound Decisions
Trigger or run the Fact Settlement Engine to resolve questions whose awaited events have occurred:
```bash
hath0r decision settle
```

### Step 6: Enforce the Output Boundary Gate ("What Comes Out")
Before merging or accepting agent deliverables:
```bash
hath0r decision approve-out "drv-c9cdf6d8" --summary "Widget proof & contract tests" --unblocks "release-train-1.8"
```
