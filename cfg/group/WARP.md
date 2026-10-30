# Synced from HATH0R-CLI/cfg/group (control tower)
# Canonical git path: Bayly-AI/HATH0R-CLI → cfg/group/
# Re-run: ./scripts/sync-group-hub.sh

# WARP.md — OpenSource Project policy

> Group: `hath0r-opensource`  
> Control tower: `HATH0R-CLI` (`Bayly-AI/HATH0R-CLI`)  
> Updated: 2026-10-29

## Purpose

Agent and operator policy for the **OpenSource Project**: every canonical repo under `/Users/raybayly/Development/OpenSource`.

## Control tower

| Field | Value |
|-------|-------|
| Tower product | HATH0R-CLI |
| Path | `/Users/raybayly/Development/OpenSource/hathor-cli` |
| Remote | `Bayly-AI/HATH0R-CLI` |
| Infra Tower | `HATH0R-ATC` (`/Users/raybayly/Development/OpenSource/hath0r-atc`, `Bayly-AI/HATH0R-ATC`) |
| CLI | `hath0r` |
| Config | `hathor-cli/cfg/control-tower.yaml` |

Members point `control_tower_path` at the tower repo, not at the bare group folder.

## Membership

- **In scope**: all sibling git repositories under the OpenSource folder (`hathor-cli`, `hath0r-atc`, `hath0r-framework`, `hath0r-mcp`, `hath0r-poc`).
- **Registry**: tower `cfg/products.yaml` and hub `/.hath0r/knowledgebase/catalogs/suite-products.yaml`.
- New sibling repos join the OpenSource Project by default and must maintain `AGENTS.md`, `CLAUDE.md` (1:1 mirror via `CR-CLAUDE-SYNC-001`), `THREATMODEL.md` (`CR-AGENTIC-SEC-001`), and `.hath0r/memory/` (`CR-MEMORY-COMPOUND-001`).

## Knowledge & docs

| Surface | Path | Role |
|---------|------|------|
| Group KB hub | `OpenSource/.hath0r/knowledgebase` | Canonical local knowledge |
| Member KB | `<repo>/.hath0r/knowledgebase` | Stub/pointer only |
| Docs corpus | `OpenSource/hath0r-framework/docs` | Canonical documentation |
| Group rules | `OpenSource/AGENTS.md` & `OpenSource/CLAUDE.md` | Agent rules (1:1 synced) |
| Tower configs | `OpenSource/hathor-cli/cfg/*` | Suite governance |

## Hidden root

Only `.hath0r/`. Forbidden: `.ai/`, `.customerSystem/`, `.infraOS/`.

## CLI-first & missing capability offer (`CR-CLI-ENTRY-001` / `cr-cli-first-001`)

- **CLI-First**: Operators and agents MUST invoke `hath0r` CLI commands for connections, MCP tools, workflows, factories, Docker stacks, security audits, and KB queries rather than ad-hoc scripts.
- **Offer Missing Capability**: When a requested capability/workflow/factory is missing, do not improvise ad-hoc solutions. Offer to switch the task to create the capability/factory first and use the user request as the acceptance test.
- **Checklist**: Follow `docs/governance/checklists/agent-session-start.md` at session start.
- **Procedure Gate**: Validate or author a runbook/playbook before writing code.

## Mandatory Rule Synchronization (`CR-CLAUDE-SYNC-001`) & Agentic Security (`CR-AGENTIC-SEC-001`)

- **`CLAUDE.md` ↔ `AGENTS.md` Sync**: `CLAUDE.md` must always match `AGENTS.md` 1:1 (`hath0r agentgraph sync`, `hath0r memory hash --sync`, `hath0r agentgraph validate`).
- **BITE & Threat Model Gates**: Run `hath0r skills audit`, `hath0r mcp audit`, `hath0r threatmodel validate`, and `hath0r finops tokens verify-ledger` during preflight and clean-repos workflows.

## Branch protection & promotion (`CR-BAI-001` / `cr-branch-gov-001` / `CR-SEMVER-BUMP-001`)

```text
local → work branch → development → (release/x.x.x) → testing → staging → master (Production)
```

- Issue before branch (`hath0r branch start <type> <issue> <slug>`)
- Work prefixes: `feature|bugfix|hotfix|enhancement|research|fix|chore/<issue>-slug`
- Work PRs merge to **`development` only** (`hath0r pr create --semver <patch|minor|major>`)
- Every PR must bump Semantic Version (`MAJOR.MINOR.PATCH`); `Version Impact: none` is forbidden (`CR-SEMVER-BUMP-001`)
- Release branches: `release/x.x.x` (`hath0r promote release <x.y.z>`) for promotion only
- Stage heads: `development`/`release/*` → testing; then staging → master (human review on staging/master via `hath0r promote to <stage> --gate`)
- Detail: `docs/governance/branch-rules.md` in HATH0R-CLI

## Secrets

Never commit secrets. Use `/Users/raybayly/Development/.credentials/<service>/.env`.

## CR-HATH0R-INIT-001: Hath0r repo initialization entry gate (CRITICAL — org-wide)

1. **Setup playbook** — Follow `/Users/raybayly/Development/OpenSource/hath0r-framework/docs/developers/hathor-playbook-001-repo-init-setup-20260919.md`.
2. **Same-technology runbook** — Maintain `docs/runbook.md` in the target repo.
3. Apply fileset/layout, `.hath0r/`, `cfg/`, contracts pin, `AGENTS.md` + `CLAUDE.md` identity, and `./bin/hath0r-bootstrap.sh`.

## PR workflow hardening

See HATH0R-CLI `docs/governance/pr-workflow.md`. Feature PRs → development (agents + CODEOWNERS). Human gate before staging/master. Environments: `testing`, `staging`, `production`.

## Suite standards (control tower)

Canonical docs in HATH0R-CLI `docs/governance/`:

- OpenTelemetry — `opentelemetry-standards.md` (#60)
- OpenFeature — `openfeature-standards.md` (#59)
- OpenObservation — `openobservation-standards.md` (#58)
- CLI-first — `cli-first-rules.md` (#61) + root `AGENTS.md`
- Workflow documentation set — `workflow-documentation-standard.md` (#62)
- Docker groups — `docker-group-standard.md` + `cfg/docker/groups/*` (#63)

---

## CR-TASK-EVAL-001 (Automatic Task Evaluation Before Announcing Complete — CRITICAL · CANONICAL)
- **Mandatory Pre-Announcement Task Evaluation Gate**: Every task MUST be evaluated across the 4-tier hybrid evaluation pipeline (Tier 1 Deterministic Rubrics, Tier 2 Trajectory & FinOps Efficiency, Tier 3 Adversarial & Diff Critics, Tier 4 Goal Alignment & Consensus) prior to announcing work as Complete.
- **Composite Reward Threshold**: Task completion requires `passed_gate: true` and composite reward score `R_task >= 0.80` persisted in `.hath0r/evals/latest.json` and compounded as an `eval:<task_id>` node in `.hath0r/memory/graph.json`.
- **How to Verify**: Run `hath0r evals run` and `hath0r evals verify` before announcing Complete (`EndOfTaskBot`, `TaskAnnouncerBot.announce_complete`, and `CleanReposWorkflowBot` enforce this gate automatically) and include the structured **Eval Scorecard** summary in the completion response.
