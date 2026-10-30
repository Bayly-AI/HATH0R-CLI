# Synced from HATH0R-CLI/cfg/group (control tower)
# Canonical git path: Bayly-AI/HATH0R-CLI → cfg/group/
# Re-run: ./scripts/sync-group-hub.sh

# AGENTS.md — OpenSource Project (group `hath0r-opensource`)

> Group control rules for every product under `/Users/raybayly/Development/OpenSource`  
> Updated: 2026-10-29

## Identity (CRITICAL)

| Field | Value |
|-------|-------|
| Group | `hath0r-opensource` |
| Project | **OpenSource Project** |
| Group root | `/Users/raybayly/Development/OpenSource` |
| **Control tower (Governance & CLI)** | **`HATH0R-CLI`** |
| Control tower path | `/Users/raybayly/Development/OpenSource/hathor-cli` |
| Control tower GitHub | `Bayly-AI/HATH0R-CLI` |
| **Control tower (Infra & Observe)** | **`HATH0R-ATC`** (`/Users/raybayly/Development/OpenSource/hath0r-atc`, `Bayly-AI/HATH0R-ATC`) |
| Operator CLI | `hath0r` |
| Canonical KB hub | `/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase` |
| Group policy | `/Users/raybayly/Development/OpenSource/WARP.md` |
| Framework hidden root | `.hath0r/` only |

## Membership rule (CRITICAL)

**All git repositories directly under the OpenSource folder are canonically part of the OpenSource Project** (siblings of the control tower), unless explicitly excluded in the control-tower product catalog.

### Current canonical members

| Product | Local path | GitHub | Role |
|---------|------------|--------|------|
| **HATH0R-CLI** | `.../OpenSource/hathor-cli` | `Bayly-AI/HATH0R-CLI` | **Control tower** + operator CLI (`hath0r`) |
| **HATH0R-ATC** | `.../OpenSource/hath0r-atc` | `Bayly-AI/HATH0R-ATC` | **Infra control tower** + Docker group `hath0r` |
| **HATH0R Framework** | `.../OpenSource/hath0r-framework` | `Bayly-AI/HATH0R-Agentic-Framework` | Framework + canonical `docs/` |
| **HATH0R-MCP** | `.../OpenSource/hath0r-mcp` | `Bayly-AI/HATH0R-MCP` | Standalone FastMCP server (`hath0r-mcp`) |
| **HATHOR POC** | `.../OpenSource/hath0r-poc` | `Bayly-AI/HATH0R-Agentic-POC` | Integration test bed |

Member repos keep their own `AGENTS.md` (and exact 1:1 mirror `CLAUDE.md`) and **defer** to this file and to the control tower for group identity, KB hub, and suite orientation.

## Control tower (CRITICAL — cr-kb-tower-001)

1. Resolve suite/control-tower questions to **HATH0R-CLI** (`cfg/control-tower.yaml`, `cfg/suite.yaml`, `cfg/products.yaml`).
2. Resolve durable local knowledge to the **group hub** KB (not member stubs).
3. Use operator CLI **`hath0r`** for path/doctor/KB orientation when installed.
4. Framework `hath0r-framework/docs/` remains the **canonical documentation corpus** (content), while HATH0R-CLI remains the **governance/control** tower.

## CR-CLI-ENTRY-001: CLI-First & Missing Capability Offer (CRITICAL — cr-cli-first-001)

1. **CLI-First**: For any request involving a connection, MCP, workflow, factory, Docker workflow, KB path, or suite orientation, invoke **`hath0r`** (or the documented operator CLI entrypoint) rather than inventing ad-hoc scripts.
2. **Missing Capability Offer**: If the required connection, MCP, workflow, or factory does not exist, do not silently improvise or hack workarounds. Offer to switch the task to:
   - Creating the missing connection / MCP / workflow / factory, and
   - Using the user's original request as the automated acceptance test of that new capability.
3. **Session Start Checklist**: Review and follow `docs/governance/checklists/agent-session-start.md` before executing work.
4. **Procedure & Runbook Requirement**: Require procedure/strategy/playbook/runbook before scaffolding or writing implementation code.

## CR-CLAUDE-SYNC-001 (Mandatory `CLAUDE.md` ↔ `AGENTS.md` 1:1 Synchronization — CRITICAL · CANONICAL)

- Every repository in the OpenSource Project (and the group root) MUST maintain `CLAUDE.md` as an exact byte-for-byte mirror of `AGENTS.md`.
- Synchronize automatically via `hath0r agentgraph sync` and `hath0r memory hash --sync`, and validate via `hath0r agentgraph validate` and `hath0r skills audit`.

## CR-AGENTIC-SEC-001 (Agentic Security, Supply-Chain & Governance Controls — CRITICAL · CANONICAL)

- **BITE Supply-Chain & Skill Integrity (`hath0r skills audit` / `hath0r mcp audit`)**: Audit all `.agents/skills/**/SKILL.md`, `CLAUDE.md`, `AGENTS.md`, `WARP.md`, and MCP tool schemas for prompt injection, hidden Unicode tag characters, reverse shells, and credential exfiltration, and pin SHA-256 digests in `.hath0r/security/mcp-schema-pins.json`.
- **L2 Output Sanitizer & Canary Honeytokens**: Enforce output-side taint and canary honeytoken verification (`L2OutputSanitizer`) on RAG/MCP tool results before LLM context injection.
- **Cryptographic Hash-Chained Token & Tool Ledger (`hath0r finops tokens verify-ledger`)**: Record and verify tamper-evident SHA-256 hash chains in `.hath0r/state/finops/token_ledger.jsonl`.
- **Dynamic Purpose-Based Access Control (PBAC)**: Enforce clearance, sensitivity classification, and stated mission purpose (`PBACPolicyEngine`) across knowledge retrieval and MCP tools.
- **Two-Stage AST + Adversarial Reachability (`hath0r security openant`) & Red-Team Probing (`hath0r kb redteam`)**: Verify exploitability of findings via `OpenAntReachabilityVerifier` and run automated multi-persona RBAC boundary probing.
- **Fail-Closed `THREATMODEL.md` Gate (`hath0r threatmodel validate`) & Slopsquatting Guard**: Maintain a valid `THREATMODEL.md` in every repository and verify dependency/rule drift (`DependencyGuardBot`) during preflight.

## CR-MEMORY-COMPOUND-001 (Mandatory `.hath0r/memory` Repository Presence, Micro Memory Sessions & Pre-Announcement MemoryGraph Compounding — CANONICAL)

- Maintain `.hath0r/memory/graph.json`, `.hath0r/memory/sessions/current.json`, `.hath0r/memory/sessions/latest.json`, `.hath0r/memory/hashes.json`, `core_rules.md`, and `architecture.md` across every repository (`hath0r memory init` / `hath0r memory ensure-all`).
- Read and write micro memory sessions (`hath0r memory session start|read|write|end`), compound structured knowledge (`hath0r memory compound`), sync SHA-256 file hashes (`hath0r memory hash --sync`), and verify (`hath0r memory verify`) before announcing complete.

## Hidden root (CRITICAL — cr-hath0r-root-001)

- **Use only** `.hath0r/` for framework-created / modified / saved project metadata.
- **Do not** create or write `.ai/`, `.customerSystem/`, or `.infraOS/`.

## Open issues tracking (group-wide)

Track **all open issues** across the canonical OpenSource GitHub repos with this verified search query (GitHub Search / Issues API):

```text
is:issue state:open repo:Bayly-AI/HATH0R-Agentic-Framework repo:Bayly-AI/HATH0R-Agentic-POC repo:Bayly-AI/HATH0R-CLI repo:Bayly-AI/HATH0R-MCP repo:Bayly-AI/HATH0R-ATC
```

## Branch & PR governance (CRITICAL — cr-branch-gov-001)

Applies to every OpenSource Project member repo:

1. **Issue first** — no GitHub issue → no work branch (`hath0r branch start <type> <issue> <slug>`).
2. Branch from **`development` only** using a work prefix:
   `feature|bugfix|hotfix|enhancement|research|fix|chore/<issue-number>-short-slug`
3. **Work PRs target `development` only** (`hath0r pr create --semver <patch|minor|major>` — never testing/staging/master).
4. Owner approval / CODEOWNERS required (`@somesayray` has admin merge authority on `development`; human gate enforced before `staging` and `master`).
5. **Release trains** use `release/x.x.x` cut from `development` (`hath0r promote release <x.y.z>`) for promotion beyond development.
6. Promote only along: `development → testing → staging → master` (`hath0r promote to <stage> --gate`).

### Canonical branches (locked / protected)

| Branch | Role |
|--------|------|
| `development` | Default; only merge target for work PRs |
| `testing` | Pre-staging; accepts `development` or `release/x.x.x` |
| `staging` | Pre-production; human review |
| `master` | Production; human review |

Full checklist: `docs/governance/branch-rules.md`

## Environment promotion (CRITICAL — CR-BAI-001)

```text
local → work branch → development → (release/x.x.x) → testing → staging → master (Production)
```

Never skip stages. Details: `WARP.md` (this folder), `docs/governance/branch-rules.md`, and CI `.github/workflows/enforce-promotion-path.yml`.

## Credentials

`/Users/raybayly/Development/.credentials/<service>/.env` — never hardcode or print secrets.

## Private vs OpenSource

Do **not** treat private internal trees (e.g. `/Users/raybayly/Development/BAI/...`) as canonical sources for OpenSource Project docs, KB, or product identity.

## CR-HATH0R-INIT-001: Hath0r repo initialization entry gate (CRITICAL — org-wide)

**Main entry statement:** Before initializing (or re-initializing) any repository with Hath0r, agents MUST:

1. **Setup playbook** — Locate and follow the canonical Hath0r setup playbook:
   - `/Users/raybayly/Development/OpenSource/hath0r-framework/docs/developers/hathor-playbook-001-repo-init-setup-20260919.md`
2. **Same-technology runbook** — Locate a runbook for an **individual repo with the same technology stack** (`docs/runbook.md`).
3. Only after (1) and (2) are satisfied: apply fileset/layout, `.hath0r/`, `cfg/`, contracts pin, `AGENTS.md` + `CLAUDE.md` identity, and `./bin/hath0r-bootstrap.sh`.

## PR workflow hardening (CRITICAL)

Documented in control tower `docs/governance/pr-workflow.md`.

1. Work PR → `development` (agent/bot review + CODEOWNERS).
2. Release train via `release/x.x.x` → `testing`.
3. **Human initiates** staging and production promotions.
4. Use feature vs release PR templates under `.github/PULL_REQUEST_TEMPLATE/`.

## CR-SEMVER-BUMP-001 (Semantic Version Bump on Every PR — CANONICAL)
- Every pull request that is created and merged must create or bump this product's Semantic Version (`MAJOR.MINOR.PATCH`, https://semver.org). The root `VERSION` file is the source of truth; keep `VERSION` and `CHANGELOG.md` in step with it.
- Pick the bump by impact: MAJOR for breaking changes, MINOR for backward-compatible features, PATCH for fixes, docs, chores and everything else. `Version Impact: none` is not allowed.
- New products start at `0.1.0`.
- Declare the bump in the PR body as `Version Impact: patch|minor|major` and add a matching `CHANGELOG.md` entry. Verify with `hath0r release validate` before announcing complete.
- A PR merged without a version bump is not Complete.

---

## CR-SONAR-PREANNOUNCE-001 (SonarCloud Thresholds Before Announcing Complete — CANONICAL)
- **Pre-Announcement SonarCloud Gate**: Before announcing any work as Complete, the agent MUST analyze the code and confirm it meets the repository's SonarCloud Quality Gate thresholds via `hath0r quality sonar`.

---

## CR-TASK-EVAL-001 (Automatic Task Evaluation Before Announcing Complete — CRITICAL · CANONICAL)
- **Mandatory Pre-Announcement Task Evaluation Gate**: Every task MUST be evaluated across the 4-tier hybrid evaluation pipeline (`hath0r evals run` and `hath0r evals verify`, `passed_gate: true`, `R_task >= 0.80`) prior to announcing work as Complete, and the agent MUST return a structured **Eval Scorecard** summary in its completion response.
