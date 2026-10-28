# Changelog

All notable changes to **HATH0R CLI** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.10.0] - 2026-10-28

### Added
- **Automatic Task Evaluation Architecture (`CR-TASK-EVAL-001` / `hath0r evals`)**: Implemented 4-tier hybrid task evaluation pipeline in `TaskEvaluatorBot` (`src/hath0r_cli/bots/task_evaluator_bot.py`) evaluating every task prior to completion (#510):
  - **Tier 1 (Deterministic Rubrics)**: Preflight checks, test suite, SemVer validation, AgentGraph OWL validation, and MemoryGraph SHA-256 CAS integrity.
  - **Tier 2 (Trajectory & FinOps Efficiency)**: Micro-session read/write balance, `TokenTreeBudgetGuard` budget verification, and Taguchi Quality Loss / SNR metrics.
  - **Tier 3 (Adversarial & Diff Critics)**: `AntagonisticReviewBot` zero-swallowed-exception verification, `CR-CLI-TECH-DEBT-001` issue hand-off, and `ChangeValidationBot`.
  - **Tier 4 (Goal Alignment & Consensus)**: Active issue/focus alignment and `MultiAgentConsensusEngine` scoring.
- Added CLI subcommands `hath0r evals run`, `hath0r evals status`, `hath0r evals verify`, and `hath0r evals report`, plus `EndOfTaskBot` / `TaskAnnouncerBot` pre-announcement gate integration, `end-of-task-factory.yaml` step binding, Governance Documentation Hexad, and unit test suite `tests/unit/test_task_evaluator_bot.py`.

## [1.9.0] - 2026-10-28

### Added
- **Hath0r Cruise Control Split-Window Browser Display (`#513`)**:
  - Automatic split-window browser display (`--split-window` / `--split-side right|left`) whenever a task or agent needs a decision (`hath0r cruise wait`, `hath0r cruise ask`, `hath0r cruise approve-in --queue-only`, `hath0r cruise approve-out --queue-only`, `hath0r cruise radar`, and `CruiseControlBot.open_split_window_for_decision`).
  - Added `ensure_cruise_control_server`, `build_macos_split_window_applescript`, `launch_cruise_control_split_window`, and `POST /api/decisions/split-window` in `src/hath0r_cli/server/decision_radar_server.py`.
  - Added `?focus=<decision_id>` URL deep-linking and header `◫ Split Window` control in the Cruise Control Web Radar UI.

## [1.8.1] - 2026-10-28

### Changed
- **Hath0r Cruise Control (`hath0r cruise` / `hath0r cruise-control` / `hath0r decision`)**: Renamed the Agent Decision Control Layer & Unblocking Engine from "Minority Report" to **Cruise Control** across CLI commands, Web/TUI radar headers, contracts schema, and Governance Documentation Hexad (#508).
- Added `CruiseControlBot` (`src/hath0r_cli/bots/decision_radar_bot.py`) and `HathorCruiseControlServer` (`src/hath0r_cli/server/decision_radar_server.py`) SDK exports alongside `hath0r cruise` and `hath0r cruise-control` CLI aliases.

## [1.8.0] - 2026-10-28

### Added
- **Hath0r Cruise Control / Decision Radar (`hath0r decision` / `hath0r radar`)**: Agent Decision Control Layer & Unblocking Engine (#499, #500, #501, #502, #503, #504, #505, #506):
  - `DecisionGraph` DAG dependency modeling and Transitive Unblocking Impact Score $U(d)$ reranker (`src/hath0r_cli/bots/decision_radar_bot.py`).
  - `FactSettlementEngine` replacing timer-based snoozing with declarative fact predicates (`git.pr.merged`, `ci.workflow.passed`, `agent.task.completed`, `file.exists`, `memory.fact.asserted`, `endpoint.health.ok`) and automatic event settlement (`STATUS=SETTLED_BY_EVENT`).
  - `WorkBoundaryGate` bidirectional Input ("what goes in") and Output ("what comes out") approval gates with HMAC-SHA256 signatures and audit ledger.
  - `HathorDecisionRadarServer` interactive concentric radial sunburst Web UI across 7 canonical decision wedges with SSE streaming (`src/hath0r_cli/server/decision_radar_server.py`) and Rich Terminal TUI.
  - Contract schema `contracts/hath0r-decision-spec-v1.schema.json`, declarative workflow `cfg/workflows/decision-radar-workflow.yaml`, Governance Documentation Hexad, and unit/integration test suite `tests/unit/test_decision_radar.py`.

## [1.7.3] - 2026-10-28

### Changed
- Added `CR-SONAR-PREANNOUNCE-001` to the agent instructions: confirm SonarCloud Quality Gate thresholds before announcing work Complete.

## [1.7.2] - 2026-10-28

### Added
- Tests for previously uncovered CLI commands (design, upgrade, factory, docs, playbook, memory, agentgraph, iac, repo, voice, mcp) and bots (step runner dispatch, voice daemon loop, churn git analysis, gameshow rounds, MCP probes and routing, portrait sync runs), lifting SonarCloud new-code coverage above the 80% gate.

## [1.7.1] - 2026-10-28

### Added
- CR-SEMVER-BUMP-001: every created or merged PR must create or bump the product's Semantic Version (`VERSION` is the source of truth).

## [1.7.0] - 2026-10-17

### Added
- Enterprise distribution artifacts in `release/` and release script.
