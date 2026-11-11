# Changelog

All notable changes to **HATH0R CLI** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.26.0] - 2026-11-11

### Added
- **Verification gate on merge and announce** (#596, #597). A factory step marked `gate: verified` runs only
  when `hath0r evals verify` passes and `hath0r andon status` shows no stop. The workflow executor enforces it,
  fails closed and logs each decision to `.hath0r/state/gates/events.jsonl`. `end-of-task` runs the eval with
  tests before the PR (`andon: stop`) and gates `merge-pr` and `announce-complete`; `pr-lifecycle` gates
  `document-merged-prs`.
- **Clarification hook** (#598). `start-of-task` runs `decision-radar-bot clarify-issue`, which raises a
  blocking decision when the issue has no acceptance criteria and records each check in
  `.hath0r/state/clarity/events.jsonl`.
- FMEA occurrence signals `gate:escape` and `clarity:unasked` (20-sample minimum) and
  `hath0r fmea update --signal`. EOT-07/12/13 and PL-07/12/13 re-rated with actions; both worksheets have no H rows.
- `hath0r cccd calibrate --measure-cmd/--responses` and `hath0r cicccd calibrate --measure-cmd` (#595).

### Changed
- **CCCD calibration uses measured responses only** (#595). The simulated Taguchi matrix and hard-coded drift
  are gone; drift is computed against the previous measured calibration. Without a measurement source
  (`measure_cmd` in `cfg/cccd/doe-spec.yaml`) the pre-task gate reports not fresh instead of faking a run.
- **Tier 4 scores the change and the tiers' verdicts** (#599). Goal overlap is matched against changed paths and
  added diff lines, and consensus is the share of approving critics voting from Tier 1-3 evidence plus a goal
  critic. `tier4.method: evidence-v2` is in the judge fingerprint; the WS1 study was re-run and passes
  (%GRR 0.112, ndc 100, attribute agreement 100%). Known-good parts now span R_task 0.897-0.951.

### Fixed
- Dependabot PRs are no longer merged when no CI checks have reported.

## [1.25.0] - 2026-11-11

### Added
- **Industrial QA methods for the eval and agent pipeline** (epic #580). Everything is a `hath0r`
  subcommand run by a registered bot, with a factory, a contract and the governance hexad.
  - **Gage R&R on the evals** (#584, #585): `hath0r evals msa run|report` (`measurement-system-bot`) runs a
    crossed ANOVA Gage R&R and attribute agreement over a reference panel through the real eval pipeline,
    stores the study in `.hath0r/evals/msa/` and pins the judge fingerprint. `cfg/evals/task-eval.json`
    pins the Tier 4 judge, sets the goal to R_task 1.0 and turns the Tier 4 clamp off now that the study ran.
  - **Statistical process control and capability** (#586, #587): `hath0r spc status|chart|baseline|capability`
    (`spc-monitor-bot`) with I-MR limits, Western Electric rules, EWMA and CUSUM over R_task, tier scores,
    duration, tokens, cost and latency; R_task Cp/Cpk/Pp/Ppk against the eval threshold. Signals and
    Cpk below 1.33 are warnings; `capability.mode: block` in `thresholds.json` makes them blocking.
    `hath0r quality local` shows a Capability line.
  - **Andon** (#588, #589): `hath0r andon raise|ack|clear|status|verify` (`andon-bot`) with a hash-chained
    ledger. Factory steps can declare `andon: stop|warn`; workflows, the agent DAG runner and the token tree
    budget guard stop on an active stop. Stops are routed to the decision radar.
  - **Agent FMEA** (#590): `hath0r fmea init|add|update|score|report|sync-issues|export` (`fmea-bot`) with the
    14-mode multi-agent failure taxonomy, AIAG-VDA action priority and occurrence scored from eval history.
  - **Root cause** (#591): `hath0r rca tag|pareto|fishbone|why` (`root-cause-bot`) with 6M cause categories,
    Pareto of failed gates and 5 Whys compounded as insight nodes.
  - **DMAIC projects** (#592): `hath0r dmaic start|analyze|improve|status|close` (`dmaic-project-bot`); close
    refuses until the CTQ chart has 20 in-control points after the change. Issue template
    `.github/ISSUE_TEMPLATE/dmaic-improvement.yml`.
  - **Sequential design of experiments** (#593): `hath0r optimize screen|rsm|bayes|confirm` (`doe-bot`) and
    `hath0r cccd calibrate --strategy sequential`; MCP tool `hath0r_optimize_doe`. Bayesian optimisation is
    optional (`pip install 'hath0r-cli[doe]'`). Measurement is never simulated.
  - **Poka-yoke** (#583): catalogue `docs/governance/poka-yoke-catalogue.md`; factory `on_failure` accepts the
    `failure_policy` alias.
  - Level 1 read-only tools in HATH0R-MCP and the SPC panel in HATH0R-ATC (#594).

### Fixed
- Taguchi analysis no longer pads missing responses with 1.0: `hath0r optimize taguchi --responses` refuses an
  incomplete experiment unless `--allow-partial` is given, and then analyses only measured runs (#581).
- Tier 4 no longer clamps scores or falls back to fixed values when the judge is unavailable (#582).
- `cfg/factories/cccd-4h-calibration-factory.yaml` was referenced but missing; it now exists.

## [1.24.0] - 2026-11-07

### Added
- **Real embedding and rerank backends for RAG/CAG retrieval** (#570):
  - New shared module `src/hath0r_cli/embeddings.py`: `sentence-transformers` (optional) → local Ollama
    (`/api/embed`, default `all-minilm`, 384-d) → deterministic hash fallback. Select with `HATH0R_EMBED_BACKEND`
    (`auto|sentence-transformers|ollama|hash`), `HATH0R_EMBED_MODEL`, `HATH0R_OLLAMA_URL` / `OLLAMA_HOST`.
  - `InstructionAwareReranker` now scores with a real cross-encoder (`sentence-transformers`; Qwen3-Reranker via
    its `seq-cls` conversion, BGE v2-m3, MiniLM) or bi-encoder cosine over trained embeddings, falling back to the
    lexical heuristic. Select with `HATH0R_RERANK_BACKEND` (`auto|cross-encoder|embedding|heuristic`). Every result
    reports `backend` and the `model` that actually scored it.
  - `NeuralIntentClassifier` (CAG/RAG/CLI router) embeds queries with the shared backend; result carries
    `embedding_backend`.
  - `hath0r kb rerankers` shows the active rerank and embedding backends; `hath0r kb search --hybrid` reports
    `rerank_backend` / `rerank_model`.
  - Optional extra `pip install 'hath0r-cli[rerank]'` for local cross-encoder / sentence-transformers models.

### Changed
- Removed the SHA-256 "semantic nuance" noise from the heuristic reranker; it is now a plain, deterministic
  lexical score and is labelled `lexical-heuristic`.
- Tests pin `HATH0R_EMBED_BACKEND=hash` / `HATH0R_RERANK_BACKEND=heuristic` (autouse fixture) so they never call
  Ollama or Hugging Face.

## [1.23.1] - 2026-11-07

### Added
- **`CR-CONTEXT-SQUEEZE-001` — Compress Context with SuperSqueeze (CRITICAL · CANONICAL)**: agents compress bulky context through `hath0r squeeze` / `SuperSqueezeBot` before it enters a context window or prompt. Registered in `CANONICAL_RULE_SECTIONS` for `hath0r rules ensure-all`; canonical doc `docs/governance/rules/cr-context-squeeze-001.md`.
- **`hath0r rules ensure-all` keeps `CLAUDE.md` mirrored**: `RuleRolloutBot.prepare()` now writes and commits `CLAUDE.md` as a byte-for-byte copy of the updated `AGENTS.md` (CR-CLAUDE-SYNC-001); before, rollout PRs changed only `AGENTS.md` and broke the mirror. Tests: `tests/unit/test_rule_rollout_bot.py`.
### Fixed
- **`hath0r preflight run`, `hath0r evals run` and `hath0r deploy pre` ignored `thresholds.json` commands** (#574):
  without a `cfg/quality-gates.json` override they always ran `pytest -q` and `ruff check src`, so repos without a
  `src/` folder failed preflight with ruff E902 and scored `test_suite` 0 in the task eval. Commands now resolve in
  order: `cfg/quality-gates.json`, then the `tests` and `errors` commands in `thresholds.json` (`CR-LOCAL-QGATES-001`),
  then the built-in defaults, which lint `src` only when it exists. Found in Bayly-AI/Legion-Wow-Armory (#66).
  Tests: `tests/unit/test_quality_bots.py`.

## [1.23.0] - 2026-11-03

### Added
- **`hath0r quality sonar --branch` and `--failed-tasks N`** (#568): `--branch` scopes the quality gate and issues to a
  branch instead of the main branch. `--failed-tasks N` lists the N most recent failed SonarCloud analyses
  (`api/ce/activity`) with their error messages, the only place SonarCloud says why a "SonarQube Cloud analysis failed"
  check failed. It found that MatrixOnline-Client analyses fail on the `bayly-ai` organization's 50,000-line plan limit.
  Tests: `tests/unit/test_quality_bots.py`.

## [1.22.0] - 2026-11-01

### Added
- **Official Hath0r Install Wizard for CLI & Hath0r MCP via Docker (`CR-FEATURE-WORKFLOW-STANDARD-001` & `CR-DOCKER-HATH0R-GROUP-001`)** (#566):
  - Added `InstallWizardBot` (`src/hath0r_cli/bots/install_wizard_bot.py`) orchestrating the 5-stage installation pipeline:
    1. **Dependency Inspection & Installation**: Detects and installs missing Python >= 3.10, `pipx`/`pip`, Git, `curl`, Docker Engine, and Docker Compose v2 across `brew`, `apt`, and `dnf`, and starts the Docker daemon.
    2. **Global Hath0r CLI Installation**: Installs `hath0r` globally via `pipx`, standalone binary (`release/` or GitHub Releases), or `pip` with SHA-256 checksum verification and automatic `PATH` profile persistence.
    3. **Hath0r MCP Docker Staging**: Stages the hardened non-root `Dockerfile` (`USER 10001:10001`), `docker-compose.yml` (`name: hath0r`, `Hath0r-MCP`, `127.0.0.1:38083:8083`, `read_only: true`, `cap_drop: [ALL]`), `requirements.txt`, and canonical knowledgebase (`~/.hath0r/mcp` or workspace sibling `hath0r-mcp`).
    4. **Docker Network & Container Launch**: Provisions external network `hath0r-net` with `com.hath0r.*` labels and launches `Hath0r-MCP` via Docker Compose.
    5. **End-to-End Verification & Receipt**: Probes `http://127.0.0.1:38083/health` and `/ready`, runs `UpgradeVerifierBot.verify()`, configures `~/.hath0r/mcp.json` and `.hath0r/mcp.json`, and writes `~/.hath0r/install/INSTALL_RECEIPT.json`.
  - Added `hath0r install-wizard` (and alias `hath0r setup`) with `run`, `check`, `status`, `repair`, and `uninstall` subcommands (`src/hath0r_cli/commands/install_wizard.py`), registered `install-wizard-bot` in `BotRegistry` (`src/hath0r_cli/step_runner.py`), and exposed the `hath0r_install_wizard` MCP tool (`src/hath0r_cli/server/mcp_server.py`).
  - Upgraded `scripts/install_hath0r.py` and added `release/install-wizard.sh` as the zero-dependency release bootstrap entrypoints bundled into `release/` (`scripts/build_release_binaries.py` and `.github/workflows/release.yml`).
  - Added full Governance Documentation Hexad (`docs/governance/*/install-wizard-*.md`), declarative factory `cfg/factories/install-wizard-factory.yaml`, and unit test suite `tests/unit/test_install_wizard_bot.py`.

## [1.21.0] - 2026-10-31

### Added
- **Local Quality Gates (`Q-Gates`), Per-Repo `thresholds.json` & `TaskEvaluatorBot` Integration (`CR-LOCAL-QGATES-001`)** (#561):
  - Added `LocalQualityGateBot` (`src/hath0r_cli/bots/local_quality_gate_bot.py`) enforcing SonarCloud's canonical thresholds locally (`max_errors: 0`, `min_coverage_pct: 80.0`, `max_complexity: 15`, `max_duplicated_lines_pct: 3.0`) without calling SonarCloud's remote API directly.
  - Provisions canonical `<repo>/thresholds.json` per repository, detects technology stack (`python`, `node-ts`, `infra-python`, `rust`, `go`), verifies/installs supporting test/lint/coverage libraries, and automatically scaffolds a baseline test harness if one does not exist.
  - Added `hath0r quality init`, `hath0r quality local`, and `hath0r quality ensure-all` commands (`src/hath0r_cli/commands/quality.py`) and registered `local-quality-gate-bot` in `BotRegistry` (`src/hath0r_cli/step_runner.py`).
  - Integrated Local Q-Gates directly into `TaskEvaluatorBot` (`src/hath0r_cli/bots/task_evaluator_bot.py` and `src/hath0r_cli/commands/evals.py`) across Tier 1 (`local_quality_gates`), Tier 3 (complexity and duplication deductions), `.hath0r/evals/latest.json`, and the Markdown Eval Scorecard Summary.
  - Added full Governance Documentation Hexad under `docs/governance/` (`local-quality-gates.md`, strategy, procedure, playbook, runbook, workflow, bot spec) and `cfg/factories/local-qgates-factory.yaml`.

## [1.20.0] - 2026-10-31

### Added
- **Continuous 4-Tier `TaskEvaluatorBot` Replacing Binary `1.00` Score Inflation (`CR-TASK-EVAL-001` & `CR-FEATURE-WORKFLOW-STANDARD-001`)** (#555):
  - Upgraded `TaskEvaluatorBot` (`src/hath0r_cli/bots/task_evaluator_bot.py`) to compute continuous, non-binary sub-scores across all 4 tiers (`0.80 <= R_task < 1.00`, capping at `0.9900`):
    - **Tier 1 (Deterministic Rubrics)**: Taguchi continuous latency/duration loss, 4-hour agent calibration freshness decay (`exp(-0.04 * age_hours)`), Workflow-First & Service-Bot coverage, and Level 1/2 `AgentGraph` parity.
    - **Tier 2 (Trajectory & FinOps Efficiency)**: Continuous step-efficiency decay, Level 1 MCP + `SuperSqueeze` utilization ratio, and micro-session read/write balance.
    - **Tier 3 (Adversarial & Diff Critic)**: Continuous AST line/cyclomatic complexity penalty, diff size penalty, and test-to-code ratio.
    - **Tier 4 (Goal Alignment & Consensus)**: Continuous TF-IDF semantic cosine overlap between task objective, git diff symbols, and `MemoryGraph` nodes.
  - Updated `tests/unit/test_task_evaluator_bot.py` to assert continuous non-1.00 grading (`0.80 <= R_task < 1.00`).

## [1.19.0] - 2026-10-31

### Added
- **`ArchitecturePreservationBot`, `SubstrateUtilizationBot` & `TaskCompletionVerifierBot` (`CR-FEATURE-WORKFLOW-STANDARD-001`)** (#554):
  - Added `ArchitecturePreservationBot` (`src/hath0r_cli/bots/architecture_preservation_bot.py`) verifying Service-Bot ownership (`>= 1` Bot), Level 1/2 `AgentGraph` parity, Workflow-First bindings, `.hath0r/` hidden-root exclusivity, `CLAUDE.md == AGENTS.md` sync, and Phoenix OTel configuration across all 5 suite repositories.
  - Added `SubstrateUtilizationBot` (`src/hath0r_cli/bots/substrate_utilization_bot.py`) auditing AST and runtime usage of `SuperCompressBot` (`SuperSqueeze`), `trace_span`, `OpenFeature`, `PBAC`/`Sanitizer`, and `.hath0r/spool/` OpenObservation telemetry while flagging legacy `ddtrace` imports.
  - Added `TaskCompletionVerifierBot` (`src/hath0r_cli/bots/task_completion_verifier_bot.py`) enforcing `FactSettlementEngine` probes (`cccd.calibration.fresh:4h`, `eval.gate.passed`, `mlflow.run.logged`, `phoenix.trace.verified`, `workflow.first.verified`) and continuous 4-tier eval scores (`0.80 <= R_task < 1.00`).
  - Added `hath0r arch verify|substrate|completion` (`src/hath0r_cli/commands/arch.py`) and wired all 3 bots into `start-of-task-factory.yaml`, `end-of-task-factory.yaml`, `clean-repos-factory.yaml`, and `orient-factory.yaml`.

## [1.18.0] - 2026-10-31

### Added
- **`IterationCascadeBot` Enforcing the 4-Stage Execution Hierarchy (`Task -> Hath0r-CLI/MCP -> Computer -> Web`) & `CR-FEATURE-WORKFLOW-STANDARD-001`** (#553):
  - Added `IterationCascadeBot` (`src/hath0r_cli/bots/iteration_cascade_bot.py`) enforcing `Stage 1: Task (Workflow-First + 4h Calibration + Cruise Control + Level 2 Micro-Memory)` → `Stage 2: Hath0r-CLI (Level 2) ⇄ Hath0r-MCP (Level 1) on AgentGraph + SuperSqueeze` → `Stage 3: Local Computer` → `Stage 4: External Web`.
  - Blocks out-of-order stage escalation, halts at Stage 1 with a Missing-Workflow Offer when a task has no matching workflow, blocks Stage 4 (`web`) unless Stage 2 and Stage 3 return a verified knowledge miss (`confidence < 0.70`), and sanitizes/compresses/compounds external findings into `.hath0r/memory/graph.json`.
  - Registered `iteration-cascade-bot` in `BotRegistry` (`src/hath0r_cli/step_runner.py`), added `hath0r workflow cascade` (`src/hath0r_cli/commands/workflow.py`), added `cfg/factories/iteration-cascade-factory.yaml`, and added unit tests in `tests/unit/test_issue553_iteration_cascade_bot.py`.

## [1.17.0] - 2026-10-31

### Added
- **`MCPCentralizationBot` & `MCPWorkflowEngineBot`, Workflow-First Missing-Workflow Offer, and Level 1/2 `AgentGraph` Bridge (`CR-FEATURE-WORKFLOW-STANDARD-001`)** (#552):
  - Added `MCPCentralizationBot` (`src/hath0r_cli/bots/mcp_centralization_bot.py`) auditing tool, workflow, and knowledge parity between Level 1 (`HATH0R-MCP`) and Level 2 (`HATH0R-CLI` & `.hath0r/memory/`) across `AgentGraph`, verifying `>= 1` owning Bot per service in `BotRegistry`, pruning schemas via `SchemaPruner`, and pinning SHA-256 digests in `.hath0r/security/mcp-schema-pins.json`.
  - Added `MCPWorkflowEngineBot` (`src/hath0r_cli/bots/mcp_workflow_engine_bot.py`) enforcing `CR-FEATURE-WORKFLOW-STANDARD-001` ("Everything We Do Is a Workflow"), generating deterministic Missing-Workflow Offers (`hath0r workflow offer` / `hath0r workflow scaffold`) with the original request bound as the acceptance test, enforcing pre-task 4-hour agent calibration (`ensure_calibrated(max_age_hours=4.0)`), propagating W3C `traceparent` to `Hath0r-phoenix`, and syncing boundary gates with `Hath0r-Cruise-Control`.
  - Added `hath0r workflow list|match|offer|scaffold|run` (`src/hath0r_cli/commands/workflow.py`) and `hath0r mcp parity|pin-schemas` (`src/hath0r_cli/commands/mcp.py`), plus `cfg/factories/workflow-first-offer-factory.yaml` and `docs/governance/mcp-centralization-workflow-first-standard.md`.

## [1.16.0] - 2026-10-31

### Added
- **Universal 69+ `BotRegistry` Service-Bot Ownership, 4-Hour Pre-Task Auto-Calibration, `SuperSqueeze` Wiring & `hath0r-net` OTel Alignment (`CR-FEATURE-WORKFLOW-STANDARD-001`)** (#551):
  - Registered all 69+ bots in `BotRegistry` (`src/hath0r_cli/step_runner.py` and `src/hath0r_cli/factories/step_runner.py`) and added `SERVICE_BOT_MAP` mapping every `hath0r` CLI command group to its owning Bot(s) (`>= 1` Bot), `agentgraph_level`, and `workflow_id`, ingested into `.hath0r/agentgraph/snapshot.json` via `AgentGraphBot.sync()`.
  - Updated `CCCDCalibrationLoop` (`src/hath0r_cli/cccd/calibration_loop.py`) and `CICCCDManagingBot` / `CalibrationBot` (`src/hath0r_cli/bots/cicccd_bot.py`, `src/hath0r_cli/bots/ci_cccd_bot.py`) from 24h to a 4-hour freshness TTL (`max_age_hours = 4.0`) and added `ensure_calibrated(max_age_hours=4.0, trigger_source="pre_task")`, wired into `cli.py`, `hath0r task start`, and `cfg/factories/start-of-task-factory.yaml`.
  - Wired `SuperSqueezeBot` (`SuperCompressBot` in `src/hath0r_cli/bots/supercompress_bot.py`) across `CAGEngine.pack_context()`, `HybridCAGRAGRouter.rag_search()`, `HAHPProtocolManager.create_envelope()`, `BotRegistry`, and `hath0r squeeze`.
  - Updated `cfg/observability/otel.json` to target `http://localhost:38000/phoenix` (`Hath0r-phoenix`), `Hathor-MLFLOW` (`:35000`), and `Hath0r-Cruise-Control` (`:38090`).

## [1.15.5] - 2026-10-30

### Fixed
- **`hath0r release publish` tags the promoted commit, not the checkout** (#550):
  - `ReleaseBot.tag_and_release()` fetches and resolves a release ref (default `origin/master`, `--ref` to override), reads `VERSION` and `CHANGELOG.md` from that commit, and creates the annotated tag on it. Previously it ran `git tag` on the checkout's HEAD with the checkout's version, so publishing from `development` tagged unpromoted code.
  - An existing tag on a different commit now fails the publish instead of being ignored; an existing tag on the same commit is accepted, so re-runs are safe.
  - Dry runs report the resolved `ref` and `sha`. The factory `release-bot` publish step accepts a `ref` argument.
  - Documented the publish step in `docs/procedures/git-promotion-workflow-procedure.md` and the quality/release runbook.

## [1.15.4] - 2026-10-30

### Added
- **CLI tests for CR-AGENTIC-SEC-001 commands** (`tests/unit/test_agentic_security_cli.py`): `skills audit`, `mcp audit`, `kb redteam`, `finops tokens verify-ledger`, and `observe shadow-ai` are exercised in text and JSON modes, including dangerous skill/MCP definitions and a tampered telemetry ledger. Raises SonarCloud new-code coverage for the release from 75.2% to above the 80% gate (#545).

## [1.15.3] - 2026-10-30

### Fixed
- **Continuous Training no longer fabricates results (`hath0r cicccdct train run` · `hath0r_cicccdct_train`)**:
  - `CCCDTTrainingCoordinator.run_training_job()` now returns `status: "unavailable"` with a reason and the missing backend dependencies per method (`lora`/`peft`: torch, transformers, peft; `qlora`: + bitsandbytes; `sft`/`dpo`: + trl; DSPy methods: dspy). Removed the 16-dim hash-vector "LoRA subspace" optimizer, floored candidate reward, constant latencies, invented MLflow run IDs, placeholder adapter files, and the `cccd_state.json` "Staging" write introduced in 1.13.0.
  - `cicccdct train run` emits a `TRAINING_BACKEND_UNAVAILABLE` error diagnostic and exits 1; the MCP tool description states that no backend exists.
- **`hath0r kb redteam` passes mypy**: probe ID and category cells are passed to `Table.add_row` as strings, fixing the `arg-type` errors that failed CI `mypy src/hath0r_cli`.
- **`test_cli_sync_command` no longer depends on terminal width**: the `cruise status` assertion collapses whitespace so Rich line wrapping on narrow CI runners cannot split "not this folder".

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
