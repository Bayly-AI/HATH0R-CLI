# AGENTS.md — HATH0R-CLI (Control Tower & Operator CLI)

> **Canonical Control Tower and Operator CLI** for the **Hath0r OpenSource Suite** (`hath0r-opensource`).
> Roles: **Governance Control Tower** · **Operator CLI (`hath0r`)** · **Shared Bot & Workflow Substrate** · **AgentGraph & Memory Hub**.

| Field | Value |
|---|---|
| Product | **HATH0R-CLI** |
| Product ID | `hath0r-cli` |
| Role | Control Tower & Operator CLI (`is_control_tower: true`) |
| GitHub | **[Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI)** |
| Local Path | `/Users/raybayly/Development/OpenSource/hathor-cli` |
| Group | `hath0r-opensource` / **OpenSource Project** |
| Docker Group | **`hath0r`** (`CR-DOCKER-HATH0R-GROUP-001`) |
| Docker Network | **`hath0r-net`** (CANONICAL) |
| Shared Edge / State | `hath0r-nginx` (ATC) / `hath0r-redis` (port 6379) / `Hathor-MLFLOW` |
| Standalone MCP | `hath0r-mcp` (`../hath0r-mcp`, port `38083` / `8083`, `https://mcp.hath0r-cli.com`) |
| Members Root | `/Users/raybayly/Development/OpenSource` |
| Hidden Root | **`.hath0r/` only** (`cr-hath0r-root-001`) |
| Canonical KB Hub | `/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase` |

---

## CR-CLI-ENTRY-001: Start with the CLI (CRITICAL — Org-Wide · CANONICAL)
1. **Start with the CLI (CRITICAL ENTRY GATE)**: When receiving ANY request or starting any task, agents **MUST ALWAYS START WITH THE OPERATOR CLI (`hath0r`)** rather than inventing ad-hoc scripts. Check `hath0r --help` and `hath0r <group> --help` first.
2. **Missing Capability Offer**: If the required connection, MCP, workflow, bot, or factory does not exist in `hath0r`, offer to register the missing capability, using the original request as the acceptance test.
3. **Docs before code**: Require procedure/playbook/runbook before scaffolding implementation.

---

## CR-CLI-ENTRY-001: Start with the CLI (CRITICAL — Org-Wide · CANONICAL)

1. **Start with the CLI (CRITICAL ENTRY GATE)**: When receiving ANY request or starting any task, agents **MUST ALWAYS START WITH THE OPERATOR CLI (`hath0r`)** rather than inventing ad-hoc scripts. Check `hath0r --help` and the matching `hath0r <group> --help` first.
2. **Missing Capability Offer**: If the required connection, MCP, workflow, bot, or factory does not exist in `hath0r`, offer to register the missing capability, using the original request as the acceptance test.
3. **Docs before code**: Require procedure/playbook/runbook before scaffolding implementation.

Canonical: [HATH0R-CLI `docs/governance/cli-first-rules.md`](https://github.com/Bayly-AI/HATH0R-CLI/blob/development/docs/governance/cli-first-rules.md).

## CR-CLI-FEATURE-STANDARD-001 (Shared Code in CLI & Artifact Hexad — CRITICAL · CANONICAL)
- **Zero Code Duplication**: Anything usable across multiple repositories MUST live in `HATH0R-CLI`.
- **Complete Feature Package**: When adding any feature that qualifies as a CLI capability, deliver the CLI commands (`src/hath0r_cli/commands/`), managing bots (`src/hath0r_cli/bots/`), workflows (`cfg/workflows/`), and the Governance Documentation Hexad (Strategy, Procedure, Playbook, Runbook, Workflow, Bot Spec).
- **Configuration-Only Member Repos**: Consumer repositories contain declarative configuration files (`cfg/`, `otel.json`, workflow JSONs/YAMLs) that bind to CLI tools.

---

## CR-CLAUDE-SYNC-001 (Mandatory `CLAUDE.md` ↔ `AGENTS.md` 1:1 Synchronization — CRITICAL · CANONICAL)
- **Exact 1:1 Mirror**: Every repository in the suite MUST maintain `CLAUDE.md` at the repository root as an exact byte-for-byte mirror of `AGENTS.md` so Claude Code, Antigravity, Cursor, and all multi-agent runtimes enforce identical non-conflicting governance rules.
- **Automated Synchronization**: `hath0r agentgraph sync`, `hath0r memory hash --sync`, and `hath0r clean-repos` automatically synchronize `CLAUDE.md` from `AGENTS.md` and track both files in `.hath0r/memory/hashes.json`.
- **Drift & Contradiction Gate**: `hath0r agentgraph validate` and `hath0r skills audit` verify `CLAUDE.md == AGENTS.md` and fail closed on any rule drift or rule conflict (such as `Version Impact: none` vs `CR-SEMVER-BUMP-001`).

---

## CR-AGENTIC-SEC-001 (Agentic Security, Supply-Chain & Governance Controls — CRITICAL · CANONICAL)
- **BITE Supply-Chain & Skill Integrity (`hath0r skills audit` / `hath0r mcp audit`)**: Audit all `.agents/skills/**/SKILL.md`, `CLAUDE.md`, `AGENTS.md`, `WARP.md`, and MCP tool schemas for prompt injection, hidden Unicode tag characters, reverse shells, and credential exfiltration, and pin SHA-256 digests in `.hath0r/security/mcp-schema-pins.json`.
- **L2 Output Sanitizer & Canary Honeytokens**: Enforce output-side taint and canary honeytoken verification (`L2OutputSanitizer`) on RAG/MCP tool results before LLM context injection.
- **Cryptographic Hash-Chained Token & Tool Ledger (`hath0r finops tokens verify-ledger`)**: Every tool/completion event is recorded in `.hath0r/state/finops/token_ledger.jsonl` with a tamper-evident SHA-256 hash chain (`prev_hash` → `entry_hash`).
- **Dynamic Purpose-Based Access Control (PBAC) & Confused-Deputy Prevention**: Enforce clearance, sensitivity classification, and stated mission purpose (`PBACPolicyEngine`) across knowledge retrieval and MCP tools.
- **Two-Stage AST + Adversarial Reachability (`hath0r security openant`) & Red-Team Probing (`hath0r kb redteam`)**: Verify exploitability of findings via `OpenAntReachabilityVerifier` and run automated multi-persona RBAC boundary probing.
- **Fail-Closed `THREATMODEL.md` Gate (`hath0r threatmodel validate`) & Slopsquatting Guard**: Maintain a valid `THREATMODEL.md` in every repository and verify dependency/rule drift (`DependencyGuardBot`) during preflight.

---

## CR-CLI-TECH-DEBT-001 (Self-Admitted Technical Debt Issue Hand-off — CRITICAL · CANONICAL)
- **Zero Hidden Tech Debt**: Whenever an agent identifies, admits to, or introduces **self-admitted technical debt** (e.g. `TODO`s, `FIXME`s, temporary workarounds, incomplete refactors, skipped test cases, or fallback stubs), the agent MUST immediately hand that technical debt off to the **Issue Bot** (`hath0r issue create` or `gh issue create`) to create structured GitHub issues.
- **Mandatory User Disclosure**: The agent MUST explicitly present the newly created issue(s) with clickable markdown links (`https://github.com/.../issues/...`) in its final response to the user, highlighting the scope and open items.
- **Enforcement & Audit**: Leaving self-admitted technical debt in conversation responses or codebase comments without creating corresponding tracking issues violates canonical governance.

---

## CR-CLI-AGENT-SUBSTRATE-002 (Agentic Substrate & KV Pre-warming Rules — CANONICAL)
- **KV Cache Pre-warming**: Multi-agent subgraphs and subagent execution trees MUST execute zero-token prompt anchor pre-warming (`KVCachePrewarmer` / `hath0r agent prewarm`) to eliminate prefill latency spikes before spawning subagents.
- **L2WS Warm-Starting & SFT/LoRA/PEFT Continuous Training**: Parameter optimization, Taguchi calibration loops, and continuous SFT/LoRA/PEFT training MUST use `L2WSPredictor` (`hath0r cccd calibrate`) and `hath0r cccd train`.
- **HAHP Handoff Protocol**: All inter-agent communication, scratchpad memory transfers, and subagent state handoffs MUST use the Hath0r Agent Handoff Protocol (`HAHPEnvelope` / `hath0r agent hahp`).
- **Agent DAG Runner**: Multi-agent parallel execution trees MUST be defined and run via `AgentDAGRunner` (`hath0r agent dag`).

---

## CR-CLI-KNOWLEDGE-CAG-002 (W3C OWL Reasoning, CAG & Hybrid Router — CANONICAL)
- **AgentGraph OWL Snapshot**: Every AgentGraph policy mutation or sync MUST export W3C Turtle RDF syntax (`.ttl`) to `.hath0r/agentgraph/snapshot.ttl` via `hath0r agentgraph export --format turtle`.
- **Description Logic Validation**: AgentGraph policy validation MUST run `hath0r agentgraph validate --owl` to verify formal semantic consistency and detect policy contradictions.
- **Context-Augmented Generation (CAG)**: Active workspace queries and rules MUST use full-context prompt caching (`CAGEngine` / `hath0r context pack --cag`) instead of chunking lossy retrieval.
- **Hybrid CAG + RAG Router**: Knowledge queries MUST be dynamically classified via `HybridCAGRAGRouter` (`hath0r kb smart-query`) to route workspace queries to CAG and document archival queries to RAG.

---

## CR-MEMORY-COMPOUND-001 (Mandatory `.hath0r/memory` Repository Presence, Micro Memory Sessions, SHA-256 File Hashing, Un-Ignored Graph Folders & Pre-Announcement MemoryGraph Compounding — CANONICAL)
- **Universal `.hath0r/memory`, `.hath0r/memory/sessions` & `.hath0r/memory/hashes.json` Folder**: Every repository across `/Users/raybayly/Development` MUST maintain `.hath0r/memory/graph.json`, `.hath0r/memory/sessions/current.json`, `.hath0r/memory/sessions/latest.json`, `.hath0r/memory/hashes.json`, `core_rules.md`, and `architecture.md` (`hath0r memory init` / `hath0r memory ensure-all`).
- **Graph Folders Never Git-Ignored**: Repository `.gitignore` files MUST NEVER ignore `.hath0r/memory/`, `.hath0r/memory/sessions/`, `.hath0r/agentgraph/`, `.hath0r/graphs/`, `.hath0r/state/cache/`, or `.hath0r/state/context/`. Any `.hath0r/*` or `.hath0r/state/*` wildcard ignore rules MUST include explicit `!` negation rules (`!.hath0r/memory/**`, `!.hath0r/agentgraph/**`, `!.hath0r/graphs/**`, `!.hath0r/state/cache/**`, `!.hath0r/state/context/**`).
- **True Micro Memory Session Read & Write**: Every session MUST read and write a compact (<2KB) micro memory session (`hath0r memory session start|read`, `hath0r memory session write`, `hath0r memory session end`) linked via `PRECEDES` edges in `.hath0r/memory/graph.json`.
- **Cryptographic SHA-256 File Hashing & CAS Conflict Prevention (`hath0r memory hash`)**: Every file in `.hath0r/memory/` and every repository `source_files` path referenced on a `MemoryNode` MUST be tracked with canonical `SHA-256` digests and monotonic `revision` counters in `.hath0r/memory/hashes.json`. Concurrent writes use optimistic Compare-And-Swap (`expected_hash` / `base_hash`) with deterministic set-union auto-merging for non-conflicting additions and atomic file replacement (`os.replace`).
- **Pre-Announcement Memory Compounding**: Every task MUST compound structured knowledge (`episode`, `decision`, `fact`, `insight`, `concept`, or `rule`) into `.hath0r/memory/graph.json` prior to announcing complete (`hath0r memory compound` + `hath0r memory verify`).
- **Hard Gate & Immediate AgentGraph Sync**: `TaskAnnouncerBot.announce_complete`, `EndOfTaskBot`, and `CleanReposWorkflowBot` enforce `MemoryManagerBot.verify_compounded()` (`read_count >= 1`, `write_count >= 1`, `compounded_nodes_count >= 1`, `hashes_verified: True`, and `graphs_not_ignored: True`) before announcing complete and synchronize `.hath0r/agentgraph/snapshot.json` and `CLAUDE.md` on every memory mutation.

---

## CR-CLI-FINOPS-VERIFIER-002 (Token Budget Circuit Breakers & Adversarial Evals — CANONICAL)
- **Token Tree Budget Guard**: Subagent execution trees MUST enforce cumulative token and cost caps (`TokenTreeBudgetGuard` / `hath0r finops budget check`). If total tree tokens exceed 50,000 or USD exceeds $0.25, the execution MUST throw a `TokenBudgetExceeded` exception and halt recursion.
- **Multi-Agent Consensus Gate**: Multi-agent responses across GAIN peer nodes MUST be evaluated via `MultiAgentConsensusEngine` (`hath0r evals consensus`). If agreement score falls below 0.70, human-in-the-loop fallback MUST be triggered.
- **Antagonistic Review Bot**: PR diffs and code modifications MUST be audited by `AntagonisticReviewBot` (`hath0r pr review --antagonistic`) for swallowed exceptions (`except Exception: pass`) and self-admitted tech debt (`TODO`s, `FIXME`s).
- **Red-Team Verification Engine**: Critical multi-agent components MUST undergo Red-Team vs Blue-Team adversarial stress testing (`MultiAgentRedTeamEngine` / `hath0r evals redteam`) requiring 100% attack vector survival.

---

## CR-CLI-MCP-ECOSYSTEM-001 (Hath0r CLI & Hath0r MCP Ecosystem Synergy — CANONICAL)
- **Paired Execution Architecture**: `HATH0R-CLI` and `HATH0R-MCP` (`hath0r-mcp`) operate as a paired execution suite. CLI tools map declarative commands directly to MCP semantic knowledge, PBAC-governed retrieval, and tool endpoints.
- **Canonical Cloud & Local Endpoints**: Operators connect to `https://mcp.hath0r-cli.com` or local `http://127.0.0.1:38083` (`hath0r-mcp` container on Docker network `hath0r-net`).

---

## CR-SEMVER-BUMP-001 (Semantic Version Bump on Every PR — CANONICAL)
- Every pull request that is created and merged must create or bump this product's Semantic Version (`MAJOR.MINOR.PATCH`, https://semver.org). The root `VERSION` file is the source of truth; keep `VERSION`, `pyproject.toml` and `CHANGELOG.md` in step with it.
- Pick the bump by impact: MAJOR for breaking changes, MINOR for backward-compatible features, PATCH for fixes, docs, chores and everything else. `Version Impact: none` is not allowed.
- New products start at `0.1.0`.
- Declare the bump in the PR body as `Version Impact: patch|minor|major` and add a matching `CHANGELOG.md` entry. Verify with `hath0r release validate` before announcing complete.
- A PR merged without a version bump is not Complete.

---

## Branch & Promotion Governance (`CR-BRANCH-GOV-001` · `CR-BAI-001`)

```text
local → feature|bugfix|chore/<issue>-slug → development → (release/x.x.x) → testing → staging → master (Production)
```

- **Issue first**: Create a GitHub issue before any work branch (`hath0r branch start <type> <issue> <slug>`).
- **Day-to-day work**: PRs target `development` only (`hath0r pr create --semver <patch|minor|major>`).
- **Human gate**: Required before promoting to `staging` and `master` (`hath0r promote to staging --gate`).
- **Entry CLI**: `hath0r`

---

## Clean Repo Standard Operating Protocol (`hath0r clean-repos`)

When requested to **"clean repo"** or **"clean repos"**, execute the 13-step lifecycle via `hath0r clean-repos` (see `.agents/skills/clean-repos/SKILL.md`):

1. **Capture all repos in the project**: Enumerate all member repositories in `/Users/raybayly/Development/OpenSource` (`cfg/suite.yaml`).
2. **Ensure all changes are committed**: Verify `git status` and commit uncommitted source changes.
3. **Cleanup development artifacts**: Remove `.DS_Store`, `__pycache__`, `.pytest_cache`, `.coverage`, and build logs.
4. **Clean up and remove stale worktrees**: Run `git worktree prune` and detach/remove orphaned worktrees.
5. **Review branches, merge changes, resolve conflicts & ensure all PRs are merged**: Review all local and remote non-canonical branches, merge any branches with unmerged changes into `development`, and merge pending approved Pull Requests (`hath0r pr merge`).
6. **Share Knowledge & Compound MemoryGraph**: Synchronize context to knowledge roots, `.hath0r/knowledgebase`, and `.hath0r/memory/graph.json` (`CR-MEMORY-COMPOUND-001`).
7. **Update Documentation, `CLAUDE.md` Sync, AgentGraph & Security Audits**: Update `README.md`, `AGENTS.md`, sync `CLAUDE.md` (`CR-CLAUDE-SYNC-001`), and run `hath0r agentgraph sync`, `hath0r agentgraph validate`, `hath0r skills audit`, and `hath0r threatmodel validate`.
8. **Evaluate Task & Commit Documentation/State Changes**: Run `hath0r evals run` (`CR-TASK-EVAL-001`), sync `.hath0r/memory/hashes.json` (`hath0r memory hash --sync`), and commit doc/knowledge/eval updates cleanly.
9. **Ensure all changes are PR'd**: Push active feature branches and open PRs against `development` (`hath0r pr create`).
10. **Monitor PRs and merge**: Monitor CI/CD checks (`gh pr checks`) and merge passing PRs (`hath0r pr merge`).
11. **Delete stale feature branches (local & remote)**: Remove all merged/stale non-canonical feature branches locally and remotely.
12. **Return to Development & Pull/Push Origin**: Switch back to `development`, `git pull --rebase origin development`, and `git push origin development`.
13. **Verify Pre-Announce Gates & Announce Complete**: Verify `hath0r memory verify`, `hath0r evals verify`, and `hath0r quality sonar`, and present a concise status summary + Eval Scorecard to the user.

---

## AgentGraph Substrate

This repository is governed by the Hath0r AgentGraph substrate. Dynamic rule retrieval, role RBAC, and policy graphs are stored under `.hath0r/agentgraph/`.
- Query status: `hath0r agentgraph status`
- Query rules: `hath0r agentgraph query "<topic>"`
- Route role: `hath0r agentgraph route --role <role>`
- Sync rules & `CLAUDE.md`: `hath0r agentgraph sync`
- Validate rules: `hath0r agentgraph validate`

---

## CR-SONAR-PREANNOUNCE-001 (SonarCloud Thresholds Before Announcing Complete — CANONICAL)
- **Pre-Announcement SonarCloud Gate**: Before announcing any work as Complete, the agent MUST analyze the code and confirm it meets this repository's SonarCloud Quality Gate thresholds (coverage on new code, duplication, reliability, security, maintainability, and security hotspots reviewed).
- **How to Verify**: Use `hath0r quality sonar` (project key from `sonar-project.properties`) together with local test and coverage runs. If the gate cannot be checked, state that plainly instead of announcing Complete.
- **Not Complete Until Green**: A failing or unverified Quality Gate means the work is not Complete.

---

## CR-TASK-EVAL-001 (Automatic Task Evaluation Before Announcing Complete — CRITICAL · CANONICAL)
- **Mandatory Pre-Announcement Task Evaluation Gate**: Every task MUST be evaluated across the 4-tier hybrid evaluation pipeline (Tier 1 Deterministic Rubrics, Tier 2 Trajectory & FinOps Efficiency, Tier 3 Adversarial & Diff Critics, Tier 4 Goal Alignment & Consensus) prior to announcing work as Complete.
- **Composite Reward Threshold**: Task completion requires `passed_gate: true` and composite reward score `R_task >= 0.80` persisted in `.hath0r/evals/latest.json` and compounded as an `eval:<task_id>` node in `.hath0r/memory/graph.json`.
- **How to Verify**: Run `hath0r evals run` and `hath0r evals verify` before announcing Complete (`EndOfTaskBot`, `TaskAnnouncerBot.announce_complete`, and `CleanReposWorkflowBot` enforce this gate automatically).
- **Mandatory Eval Scorecard Summary After Every Task (CRITICAL · CANONICAL)**: Immediately after running task evaluations (`hath0r evals run`), the agent MUST always return a structured summary of the **Eval Scorecard** (`eval_id`, `task_id`, `passed_gate`, composite `R_task`, Tier 1–4 scores, Local Q-Gates status, and `.hath0r/evals/latest.json` path) in its completion response to the user.
- **Local Quality Gates (`CR-LOCAL-QGATES-001` — `thresholds.json`)**: `hath0r evals run` and `hath0r quality local` enforce 4 local quality gates (`Errors <= 0`, `Test Coverage >= 80.0%`, `Complexity <= 15`, `Repeated Code / Duplication <= 3.0%`) seeded with SonarCloud's canonical thresholds in `<repo>/thresholds.json` (`hath0r quality init` / `hath0r quality ensure-all`).
- **Not Complete Until Evaluated & Scorecard Returned**: A missing, failing, unverified, or unreported task evaluation scorecard means the work is not Complete.
