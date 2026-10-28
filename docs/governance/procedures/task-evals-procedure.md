# Procedure: Automatic Task Evaluation (`CR-TASK-EVAL-001`)

> Canonical Governance Procedure · ID: `PROC-TASK-EVAL-001`  
> Epic: #510 · Rule Compliance: `CR-TASK-EVAL-001`, `CR-CLI-FEATURE-STANDARD-001`, `CR-MEMORY-COMPOUND-001`

---

## 1. Purpose

Defines the mandatory standard operating procedure for executing, verifying, and compounding 4-tier task evaluations prior to completing any task across the Hath0r OpenSource Suite.

---

## 2. Standard Operating Procedure

### Step 1: Start Task & Initialize Trajectory Tracking
```bash
hath0r task start --issue <number> --slug <short-slug> --prefix feature
```
- Initializes `.hath0r/memory/sessions/current.json` to track micro-session reads, writes, and trajectory entries.

### Step 2: Execute Work & Compound Task Knowledge
```bash
hath0r memory session read --note "Reading context before compounding"
hath0r memory compound --id "episode:issue-<number>" --type episode --label "..." --content "..."
```

### Step 3: Run Automatic 4-Tier Task Evaluation
```bash
hath0r evals run --task-id "issue-<number>"
```
- Evaluates Tier 1 (Deterministic Rubrics), Tier 2 (Trajectory & FinOps), Tier 3 (Adversarial Diff Critics), and Tier 4 (Goal Alignment).
- Writes `.hath0r/evals/latest.json`, compounds `eval:issue-<number>` into `.hath0r/memory/graph.json`, updates `.hath0r/memory/hashes.json`, and syncs metrics to `Hath0r-phoenix` and `Hathor-MLFLOW`.

### Step 4: Verify Pre-Completion Gate
```bash
hath0r evals verify
```
- Confirms `passed_gate == true`, `r_task >= 0.80`, and zero hard-gate violations.

### Step 5: Finish Task & Announce Complete
```bash
hath0r task finish --bot
```
- `EndOfTaskBot` and `TaskAnnouncerBot.announce_complete()` automatically enforce both `MemoryManagerBot.verify_compounded()` and `TaskEvaluatorBot.verify_evaluated()`.
