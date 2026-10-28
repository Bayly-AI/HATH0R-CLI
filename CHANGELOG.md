# Changelog

All notable changes to **HATH0R CLI** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.0] - 2026-10-28

### Added
- **Hath0r Decision Radar (`hath0r decision` / `hath0r radar`)**: Minority Report Agent Decision Control Layer & Unblocking Engine (#499, #500, #501, #502, #503, #504, #505, #506):
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
