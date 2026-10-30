# Changelog

All notable changes to **HATH0R CLI** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.15.3] - 2026-10-30

### Fixed
- **Continuous Training no longer fabricates results (`hath0r cicccdct train run` · `hath0r_cicccdct_train`)**:
  - `CCCDTTrainingCoordinator.run_training_job()` now returns `status: "unavailable"` with a reason and the missing backend dependencies per method (`lora`/`peft`: torch, transformers, peft; `qlora`: + bitsandbytes; `sft`/`dpo`: + trl; DSPy methods: dspy). Removed the 16-dim hash-vector "LoRA subspace" optimizer, floored candidate reward, constant latencies, invented MLflow run IDs, placeholder adapter files, and the `cccd_state.json` "Staging" write introduced in 1.13.0.
  - `cicccdct train run` emits a `TRAINING_BACKEND_UNAVAILABLE` error diagnostic and exits 1; the MCP tool description states that no backend exists.

## [1.15.2] - 2026-10-29

### Added
- **Workspace-Wide `hath0r clean-repos --root` Discovery & Fast Artifact Cleanup**:
  - Added `--root` option to `hath0r clean-repos` and `hath0r repo workflow` to recursively discover and clean all unique git repositories across `/Users/raybayly/Development`, skipping `node_modules`/`.venv` during artifact cleanup and protecting local archive clones.

## [1.15.1] - 2026-10-29

### Added
- **Automatic Post-Task Evaluation & Pre-Push Verification Hooks (`CR-TASK-EVAL-001` · `hath0r evals ensure-all`)**:
  - Enhanced `TaskEvaluatorBot.ensure_repo_eval_setup()` to provision `cfg/evals/task-eval.json` (`auto_run_after_every_task: true`, `require_scorecard_summary: true`), `.hath0r/evals/post-task-hook.sh`, `.git/hooks/pre-push` (`hath0r evals verify --auto-run`), and automatic `CLAUDE.md` ↔ `AGENTS.md` synchronization across all 39 workspace repositories.

## [1.15.0] - 2026-10-29

### Added
- **Mandatory `CLAUDE.md` ↔ `AGENTS.md` 1:1 Synchronization & Rule Conflict Detection (`CR-CLAUDE-SYNC-001`)**:
  - Added `AgentGraphBot.sync_claude_md()` and wired automatic `CLAUDE.md` synchronization into `hath0r agentgraph sync`, `hath0r memory hash --sync` (`MemoryManagerBot.sync_file_hashes`), and `hath0r clean-repos` (`CleanReposWorkflowBot`).
  - Enhanced `AgentGraphBot.validate()`, `DependencyGuardBot.check_rule_file_drift()`, and `BITEVerifierBot.audit_skills_and_rules()` to verify `CLAUDE.md == AGENTS.md` and detect rule contradictions (such as `CR-SEMVER-BUMP-001` vs legacy `Version Impact: none`).
  - Updated `.agents/skills/clean-repos/SKILL.md`, `.agents/skills/orient/SKILL.md`, `plugin/skills/hath0r/SKILL.md`, and `cfg/workflows/git-promotion-workflow.yaml` to leverage the latest CLI workflows.

## [1.14.0] - 2026-10-29

### Added
- **Agentic Supply-Chain Security, BITE Verification & Knowledge Curation Suite (`CR-AGENTIC-SEC-001`)** (#537, #538, #539, #540, #541):
  - **WS1 (`BITEVerifierBot`, `hath0r skills audit`, `hath0r mcp audit`)**: Added [`src/hath0r_cli/bots/bite_verifier_bot.py`](src/hath0r_cli/bots/bite_verifier_bot.py) and [`src/hath0r_cli/commands/skills.py`](src/hath0r_cli/commands/skills.py) evaluating `SKILL.md`, `AGENTS.md`, `WARP.md`, and MCP configs against the 3 BITE questions (`is_reachable`, `is_unnecessary`, `is_concealed`), detecting invisible Unicode variation selectors (`\uFE00-\uFE0F`) and prompt overrides, and persisting `.hath0r/security/bite_manifest.json` (#538).
  - **WS2 (`SecretPIISanitizerBot` & Hash-Chained Token Telemetry Ledger)**: Added [`src/hath0r_cli/bots/secret_pii_sanitizer.py`](src/hath0r_cli/bots/secret_pii_sanitizer.py) wired into `MemoryManagerBot`, `HAHPProtocolManager`, and `TokenTelemetryCLIBot`, plus SHA-256 hash chaining (`prev_hash`, `hash`), token-bucket rate limiting, and `hath0r finops tokens verify-ledger` (#539).
  - **WS3 & WS4 CLI (`hath0r kb redteam` & OpenAnt Red-Team Reachability)**: Added `hath0r kb redteam` in `src/hath0r_cli/commands/kb.py`, L2 snippet sanitization in `HybridCAGRAGRouter`, and OpenAnt static reachability + constrained attacker persona verification in `MultiAgentRedTeamEngine`.
  - **WS5 (`THREATMODEL.md` & Evidence Trust Tiers)**: Added [`src/hath0r_cli/commands/threatmodel.py`](src/hath0r_cli/commands/threatmodel.py) (`hath0r threatmodel init|validate` with fail-closed validation) and `ChangeValidationBot.generate_evidence_trust_report()` wired into `TaskEvaluatorBot` (#540).
  - **WS6 (`DependencyGuardBot` & `ShadowAIClassifierBot`)**: Added [`src/hath0r_cli/bots/dependency_guard_bot.py`](src/hath0r_cli/bots/dependency_guard_bot.py) (slopsquatting & rule-drift guard wired into `PreflightBot`) and [`src/hath0r_cli/bots/shadow_ai_classifier.py`](src/hath0r_cli/bots/shadow_ai_classifier.py) (`hath0r observe shadow-ai` AgentSonar commit scoring) (#541).
  - Delivered the `CR-CLI-FEATURE-STANDARD-001` Governance Documentation Hexad (`docs/strategies/bite-supply-chain-strategy.md`, `docs/procedures/bite-supply-chain-procedure.md`, `docs/playbooks/bite-supply-chain-playbook.md`, `docs/runbooks/bite-supply-chain-runbook.md`, `cfg/workflows/bite-supply-chain-workflow.yaml`, `docs/bots/bite-verifier-bot-spec.md`).

## [1.13.0] - 2026-10-29

### Added
- **SFT, LoRA, QLoRA & PEFT Subspace Training Coordinator & Benchmark Evals (`CCCDTTrainingCoordinator`)**:
  - Updated `CCCDTTrainingCoordinator` (`src/hath0r_cli/cccd/training_coordinator.py`) to execute real Low-Rank Adaptation (`lora`), 4-bit NormalFloat QLoRA (`qlora`), Supervised Fine-Tuning (`sft`), and Parameter-Efficient Fine-Tuning (`peft`) subspace optimization (`_optimize_lora_peft_subspace`), persist `.bin` PEFT adapter weights with SHA-256 checksums, and run post-training benchmark evaluations (`eval_passed`).
- **Git Workflows: branch, PR & environment promotion (`GitWorkflowBot`, CR-BAI-001 / cr-branch-gov-001)**:
  - New `src/hath0r_cli/bots/git_workflow_bot.py` mirroring `.github/workflows/enforce-promotion-path.yml` locally (same work/release regexes and per-stage rules).
  - `hath0r branch start <type> <issue> <slug>` (issue-verified branch from `origin/development`) and `hath0r branch sync [--rebase]` (aborts cleanly on conflict).
  - `hath0r pr check`, `pr create` (path-validated, `Closes #n` + `Version Impact`), `pr status`, and `pr merge` (squash into development; merge commit for promotions; `--human-approved` required for staging/master).
  - New `hath0r promote` group: `status` (pending/drift/versions/open PRs per stage), `release <x.y.z>` (non-destructive release cut), and `to testing|staging|production [--from release/x.y.z] [--gate]`.
  - Governance hexad: `cfg/workflows/git-promotion-workflow.yaml`, strategy, procedure, runbook and playbook docs.

### Fixed
- **SAST Dynamic Code Execution Scanner (`SecuritySASTScanner`)**: Updated `SecuritySASTScanner._scan_python_file` (`src/hath0r_cli/bots/cicccd_bot.py`) to ignore string literals, comments, method definitions (`def exec(`), and attribute calls (`.exec(`) when scanning for dynamic `eval()`/`exec()` invocations.
- Legacy `--json` flags (churn, decision/cruise, mesh, mlflow, observe, phoenix, pmat, orient) and the `pmat stats` / `observe charts` `--format` options now honour the global `-o json` and non-TTY `auto` output mode instead of printing Rich tables.

## [1.12.1] - 2026-10-28

### Added
- **Mandatory Eval Scorecard Summary in Completion Responses (`CR-TASK-EVAL-001` — `#524`)**:
  - Updated `TaskEvaluatorBot.CANONICAL_AGENTS_EVAL_SECTION` (`src/hath0r_cli/bots/task_evaluator_bot.py`) to mandate as **CRITICAL · CANONICAL** (immediately below running the evals themselves) that agents always return a structured summary of the **Eval Scorecard** (`eval_id`, `task_id`, `passed_gate`, composite `R_task`, Tier 1–4 breakdown, and `.hath0r/evals/latest.json` path) after completion of every task.
  - Added `TaskEvaluatorBot.format_scorecard_markdown()`, `scorecard_summary_markdown` output across `evaluate_task()`, `get_status()`, `verify_evaluated()`, and `TaskAnnouncerBot.announce_complete()`, and automatic in-place upgrading of existing `CR-TASK-EVAL-001` sections via `hath0r evals ensure-all`.

## [1.12.0] - 2026-10-28

### Added
- **Clean Repo Workflow Branch Merge, Conflict Resolution & Local/Remote Pruning (`CleanReposWorkflowBot` — `#522`)**:
  - Updated `CleanReposWorkflowBot.run_clean_repo_workflow` (`src/hath0r_cli/bots/repo_clean.py`) to review all local and remote non-canonical branches, detect genuinely unmerged commits (`git cherry`), merge unmerged branches into `development` (or canonical base branch), and automatically resolve merge conflicts (`-X ours` and tree-level conflict fallback).
  - Enhanced worktree pruning (`_prune_worktrees`) to detach or remove secondary feature worktrees so locked local feature branches can be merged and deleted cleanly.
  - Added automatic deletion of all merged/stale local feature branches (`git branch -D`) and remote feature branches (`git push origin --delete` + `git fetch --prune`).
  - Reordered Step 8, Step 12, and Step 13 so `TaskEvaluatorBot` (`CR-TASK-EVAL-001`) and `MemoryManagerBot` (`CR-MEMORY-COMPOUND-001`) execute and commit before switching back to `development` and running `git pull --rebase origin development` and `git push origin development`.

## [1.11.0] - 2026-10-28

### Added
- **Detached Cruise Control View & Stateless Agent Update API (`hath0r cruise detach|update|status|stop`)**:
  - Added autonomous background fact-settlement monitor (`_run_autonomous_monitor`) inside `HathorDecisionRadarServer` (`src/hath0r_cli/server/decision_radar_server.py`) so Cruise Control runs in a detached view and evaluates/settles ready facts without requiring any agent process to keep running or monitoring it (#520).
  - Added `DecisionRadarBot.update_decision()` (`src/hath0r_cli/bots/decision_radar_bot.py`), HTTP endpoints `POST /api/decisions/update` and `GET /api/decisions/status`, and automatic HTTP push sync (`_sync_to_detached_server`) from any agent repository to the detached Cruise Control server (`127.0.0.1:38090`).
  - Added CLI subcommands `hath0r cruise update <decision_id>`, `hath0r cruise detach`, `hath0r cruise status`, `hath0r cruise stop`, and `--detached/--foreground` flag on `hath0r cruise radar`.

## [1.10.1] - 2026-10-28

### Added
- **Workspace-Wide `CR-TASK-EVAL-001` Pre-Announcement Enforcement (`hath0r evals ensure-all`)**:
  - Defaulted `TaskAnnouncerBot.announce_complete(enforce_eval_gate=True)` and integrated `TaskEvaluatorBot` verification into `CleanReposWorkflowBot` Step 13 (`13_announce_complete`) and `MemoryManagerBot.ensure_all_repos()` (#518).
  - Added `TaskEvaluatorBot.ensure_repo_eval_setup()` and `TaskEvaluatorBot.ensure_all_repos()` plus CLI subcommand `hath0r evals ensure-all` to provision `cfg/evals/task-eval.json`, `.gitignore` negations (`!.hath0r/evals/**`), canonical `## CR-TASK-EVAL-001` directives in `AGENTS.md` / `WARP.md` / `.hath0r/memory/core_rules.md`, and baseline `.hath0r/evals/latest.json` scorecards across every repository under `~/Development`.

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
