# Workflow: Automatic Task Evaluation Lifecycle (`CR-TASK-EVAL-001`)

> Canonical Governance Workflow · ID: `WF-TASK-EVAL-001`  
> Epic: #510 · Factory: `cfg/factories/end-of-task-factory.yaml`

---

## 1. State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> TaskStart: hath0r task start
    TaskStart --> ActiveSession: Micro-Session & OTel Span Initialized
    ActiveSession --> CodeAndTests: Agent Executes Task & Writes Tests
    CodeAndTests --> MemoryCompound: hath0r memory compound (CR-MEMORY-COMPOUND-001)
    MemoryCompound --> TaskEvalRun: hath0r evals run (TaskEvaluatorBot)

    state TaskEvalRun {
        [*] --> Tier1_Deterministic
        Tier1_Deterministic --> Tier2_Trajectory
        Tier2_Trajectory --> Tier3_Adversarial
        Tier3_Adversarial --> Tier4_GoalAlignment
        Tier4_GoalAlignment --> ComputeReward
    }

    ComputeReward --> GateFailed: R_task < 0.80 or Hard Gate Failed
    GateFailed --> CodeAndTests: Remediate Diagnostics

    ComputeReward --> ScorecardPersisted: R_task >= 0.80 & Hard Gates Passed
    ScorecardPersisted --> ObservabilitySynced: .hath0r/evals/latest.json + eval:<id> Node + Phoenix/MLflow
    ObservabilitySynced --> AnnounceComplete: TaskAnnouncerBot.announce_complete()
    AnnounceComplete --> [*]
```

---

## 2. Factory Step Binding (`end-of-task-factory.yaml`)

In `cfg/factories/end-of-task-factory.yaml`:
- `task-evaluator-bot` executes `run-eval` with `on_failure: abort` prior to PR merge and completion announcement.
- `task-announcer-bot` verifies both `MemoryManagerBot.verify_compounded()` and `TaskEvaluatorBot.verify_evaluated()`.
