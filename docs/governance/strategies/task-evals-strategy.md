# Strategy: Hath0r Automatic Task Evaluations (`CR-TASK-EVAL-001`)

> Canonical Governance Strategy · ID: `STRAT-TASK-EVAL-001`  
> Epic: #510 · Rule Compliance: `CR-TASK-EVAL-001`, `CR-CLI-FEATURE-STANDARD-001`, `CR-MEMORY-COMPOUND-001`, `CR-CLI-FINOPS-VERIFIER-002`

---

## 1. Architectural Rationale

Traditional agent evaluation only inspects the final text or whether a test suite compiles. In autonomous multi-agent coding systems, output-only evaluation fails to detect trajectory regressions, redundant tool loops, swallowed exceptions, self-admitted technical debt (`TODO`/`FIXME`), uncompounded memory graphs, or FinOps budget overruns.

The **Hath0r Automatic Task Evaluation Architecture (`CR-TASK-EVAL-001`)** enforces a **4-Tier Hybrid Task Evaluation Pipeline** via `TaskEvaluatorBot` prior to every task completion (`hath0r task finish`, `EndOfTaskBot`, and `TaskAnnouncerBot.announce_complete`).

---

## 2. The 4-Tier Hybrid Evaluation Model

Every task is evaluated across four orthogonal tiers into a composite Multi-Objective Task Reward $R_{\text{task}} \in [0.0, 1.0]$:

$$R_{\text{task}} = w_{\text{det}} \cdot S_{\text{det}} + w_{\text{traj}} \cdot S_{\text{traj}} + w_{\text{adv}} \cdot S_{\text{adv}} + w_{\text{goal}} \cdot S_{\text{goal}}$$

| Tier | Weight | Engine / Bot | Evaluation Vectors | Gate Policy |
|---|---|---|---|---|
| **Tier 1: Deterministic Engineering Rubrics** | $0.40$ | `PreflightBot`, `DeployTestBot`, `MemoryManagerBot`, `AgentGraphBot` | Unit tests, lint (`ruff`), SemVer (`VERSION` + `CHANGELOG.md`), branch taxonomy, AgentGraph OWL consistency, MemoryGraph CAS & un-ignored graph paths | **Hard Gate** ($S_{\text{det}} == 1.0$ required for hard checks) |
| **Tier 2: Trajectory & FinOps Efficiency** | $0.20$ | `TokenTreeBudgetGuard`, `MemoryManagerBot` (Micro-Session) | Micro-session read/write balance, step bloat / retry ratio, token cap ($\le 50,000$), USD cap ($\le \$0.25$), Taguchi Quality Loss $L = k(y - m)^2$ | **Hard Gate** on budget circuit breaker; weighted reward on efficiency |
| **Tier 3: Adversarial & Diff Critics** | $0.25$ | `AntagonisticReviewBot`, `ChangeValidationBot` | 0 swallowed exceptions (`except Exception: pass`), `CR-CLI-TECH-DEBT-001` issue hand-off for `TODO`/`FIXME`, change classification verification | **Hard Gate** on critical flaws |
| **Tier 4: Goal Alignment & Consensus** | $0.15$ | `IssueGuardBot`, `MultiAgentConsensusEngine` | Active GitHub issue & session focus alignment with modified files, tests, and compounded memory nodes; multi-agent consensus ($\ge 0.70$) | Weighted reward ($R_{\text{task}} \ge 0.80$ overall threshold) |

---

## 3. Pre-Completion Persistence & Observability Sync

1. **Local Scorecard Store**: Persists `.hath0r/evals/latest.json` and `.hath0r/evals/history/eval-<task_id>.json`, tracked by SHA-256 in `.hath0r/memory/hashes.json` and never git-ignored (`!.hath0r/evals/**`).
2. **MemoryGraph Compounding**: Compounds an `eval:<task_id>` node into `.hath0r/memory/graph.json` linked via `EVALUATES` edges to the active micro-session and task episode.
3. **ATC Observability Sync**: Emits OpenTelemetry `EVALUATOR` spans to `Hath0r-phoenix` (`:36006`) and logs experiment runs to `Hathor-MLFLOW` (`:35000`) under `hath0r-task-evals` (with automatic local spooling when containers are offline).
