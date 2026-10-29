# Bot Specification: TaskEvaluatorBot

> Canonical Bot Specification · Hath0r Agentic Framework  
> Updated: 2026-10-28 · Epic: #510 · Rule: `CR-TASK-EVAL-001`

---

## 1. Role & Identity

- **Bot Name**: `task-evaluator-bot`
- **Class Name**: `TaskEvaluatorBot`
- **Subsystem**: `HATH0R-CLI` (`src/hath0r_cli/bots/task_evaluator_bot.py`)
- **CLI Command**: `hath0r evals run` / `hath0r evals status` / `hath0r evals verify` / `hath0r evals report`
- **Declarative Config**: `cfg/evals/task-eval.json`
- **Primary Function**: Executes the 4-tier hybrid task evaluation pipeline (Deterministic Engineering Rubrics, Trajectory & FinOps Efficiency, Adversarial Diff Critics, and Goal Alignment) prior to task completion, computes multi-objective reward $R_{\text{task}}$ and Taguchi Quality Loss, persists `.hath0r/evals/latest.json`, compounds `eval:<task_id>` into `.hath0r/memory/graph.json`, and logs telemetry to Arize Phoenix and MLflow.

---

## 2. Supported Actions (`BotRegistry`)

1. `run-eval` / `evaluate`: Execute the 4-tier evaluation pipeline and persist `.hath0r/evals/latest.json`.
2. `verify-eval` / `verify`: Verify that a valid, passing evaluation scorecard exists for the current task/session prior to `announce_complete`.
3. `status`: Return the latest evaluation scorecard from `.hath0r/evals/latest.json`.
4. `report`: Aggregate evaluation scorecards across workspace repositories.

---

## 3. State Persistence & MemoryGraph Integration

- **Latest Scorecard**: `.hath0r/evals/latest.json` (tracked in `.hath0r/memory/hashes.json` via SHA-256 and never git-ignored via `!.hath0r/evals/**`).
- **History Store**: `.hath0r/evals/history/eval-<task_id>.json`.
- **MemoryGraph Node**: `eval:<task_id>` (`type="eval"`) linked with `EVALUATES` edges to `session:<session_id>` and `episode:<task_id>`.
