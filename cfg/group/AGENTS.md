<!--
  CANONICAL SOURCE (git): HATH0R-CLI/cfg/group/AGENTS.md
  Repo: Bayly-AI/HATH0R-CLI
  Materialize to OpenSource group root via: scripts/sync-group-hub.sh
  Do not treat the bare OpenSource/ folder as the git source of truth.
-->

# AGENTS.md — OpenSource Project (group `hath0r-opensource`)

> Group control rules for every product under `/Users/raybayly/Development/OpenSource`  
> Updated: 2026-09-23

## Identity (CRITICAL)

| Field | Value |
|-------|-------|
| Group | `hath0r-opensource` |
| Project | **OpenSource Project** |
| Group root | `/Users/raybayly/Development/OpenSource` |
| **Control tower** | **`HATH0R-CLI`** |
| Control tower path | `/Users/raybayly/Development/OpenSource/HATH0R-CLI` |
| Control tower GitHub | `Bayly-AI/HATH0R-CLI` |
| Operator CLI | `hath0r` |
| Canonical KB hub | `/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase` |
| Group policy | `/Users/raybayly/Development/OpenSource/WARP.md` |
| Framework hidden root | `.hath0r/` only |

## Membership rule (CRITICAL)

**All git repositories directly under the OpenSource folder are canonically part of the OpenSource Project** (siblings of the control tower), unless explicitly excluded in the control-tower product catalog.

### Current canonical members

| Product | Local path | GitHub | Role |
|---------|------------|--------|------|
| **HATH0R-CLI** | `.../OpenSource/HATH0R-CLI` | `Bayly-AI/HATH0R-CLI` | **Control tower** + operator CLI |
| HATHOR Framework | `.../OpenSource/hath0r` | `Bayly-AI/HATH0R-Agentic-Framework` | Framework + canonical `docs/` |
| HATHOR POC | `.../OpenSource/hath0r-poc` | `Bayly-AI/HATH0R-Agentic-POC` | Integration test bed |

Member repos keep their own `AGENTS.md` but **defer** to this file and to the control tower for group identity, KB hub, and suite orientation.

## Control tower (CRITICAL — cr-kb-tower-001)

1. Resolve suite/control-tower questions to **HATH0R-CLI** (`cfg/control-tower.yaml`, `cfg/suite.yaml`, `cfg/products.yaml`).
2. Resolve durable local knowledge to the **group hub** KB (not member stubs).
3. Use operator CLI **`hath0r`** for path/doctor/KB orientation when installed.
4. Framework `hath0r/docs/` remains the **canonical documentation corpus** (content), while HATH0R-CLI remains the **governance/control** tower.

## CLI-First & Missing Capability Offer (CRITICAL — cr-cli-first-001)

1. **CLI-First**: For any request involving a connection, MCP, workflow, factory, Docker workflow, KB path, or suite orientation, invoke **`hath0r`** (or the documented operator CLI entrypoint) rather than inventing ad-hoc scripts.
2. **Missing Capability Offer**: If the required connection, MCP, workflow, or factory does not exist, do not silently improvise or hack workarounds. Offer to switch the task to:
   - Creating the missing connection / MCP / workflow / factory, and
   - Using the user's original request as the automated acceptance test of that new capability.
   *Example*: "MCP connection missing → create MCP registration in config + re-run original request."
3. **Session Start Checklist**: Review and follow `docs/governance/checklists/agent-session-start.md` before executing work.
4. **Procedure & Runbook Requirement**: Require procedure/strategy/playbook/runbook before scaffolding or writing implementation code.

## Hidden root (CRITICAL — cr-hath0r-root-001)

- **Use only** `.hath0r/` for framework-created / modified / saved project metadata.
- **Do not** create or write `.ai/`, `.aegis/`, or `.infraOS/`.

## Open issues tracking (group-wide)

Track **all open issues** across the three canonical OpenSource GitHub repos with this verified search query (GitHub Search / Issues API):

```text
is:issue state:open repo:Bayly-AI/HATH0R-Agentic-Framework repo:Bayly-AI/HATH0R-Agentic-POC repo:Bayly-AI/HATH0R-CLI
```

| Field | Value |
|-------|-------|
| Repos covered | Framework, POC, CLI (control tower) |
| Verified | 2026-09-15 — combined `total_count` matched per-repo open-issue sum |
| UI | GitHub → Search issues → paste query |
| CLI | `gh search issues --state open --repo Bayly-AI/HATH0R-Agentic-Framework --repo Bayly-AI/HATH0R-Agentic-POC --repo Bayly-AI/HATH0R-CLI` |
| API | `GET /search/issues?q=…` with the query above |

Multiple `repo:` qualifiers are OR’d. Prefer this group query over single-repo filters when doing suite triage.

## Branch & PR governance (CRITICAL — cr-branch-gov-001)

Applies to every OpenSource Project member repo (and org siblings following this tower):

1. **Issue first** — no GitHub issue → no work branch.
2. Branch from **`development` only** using a work prefix:
   `feature|bugfix|hotfix|enhancement|research|fix|chore/<issue-number>-short-slug`
3. **Work PRs target `development` only** (never testing/staging/master).
4. Owner approval required (`@somesayray` / CODEOWNERS + branch protection).
5. **Release trains** use `release/x.x.x` cut from `development` for promotion beyond development.
6. Promote only along: `development → testing → staging → master` (via `development` and/or `release/x.x.x` heads — never feature/* into stage branches).

### Canonical branches (locked / protected)

| Branch | Role |
|--------|------|
| `development` | Default; only merge target for work PRs |
| `testing` | Pre-staging; accepts `development` or `release/x.x.x` |
| `staging` | Pre-production; human review |
| `master` | Production; human review |

Protection (where GitHub plan allows): PR required, 1 approving review, code-owner review, no force-push, no deletions, required check `validate-promotion-path`, conversation resolution required.

### Release branches

`release/x.x.x` (SemVer) — promotion only; not day-to-day feature work.

Forbidden: sideways merges of canonical branches; work PRs into non-development; branches without issue numbers; force-push/delete on locked branches.

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
   - `/Users/raybayly/Development/OpenSource/hath0r/docs/developers/hathor-playbook-001-repo-init-setup-20260919.md`
   - If the playbook is missing or incomplete, **create or update it first**, then proceed.
2. **Same-technology runbook** — Locate a runbook for an **individual repo with the same technology stack** (e.g. React+Vite UXP, Python CLI):
   - Prefer a sibling/product `docs/runbook.md` (or `docs/*runbook*`) in that tech family.
   - If none exists, **create a tech-appropriate runbook in the target repo** before finishing init.
3. Only after (1) and (2) are satisfied: apply fileset/layout, `.hath0r/`, `cfg/`, contracts pin, `AGENTS.md` identity, and `./bin/hath0r-bootstrap.sh`.

Do not skip the playbook/runbook gate. Layout scaffolding without a documented ops path is incomplete initialization.

## PR workflow hardening (CRITICAL)

Documented in control tower `docs/governance/pr-workflow.md` (materialize via member checkout / fileset).

1. Work PR → `development` (agent/bot review + CODEOWNERS).
2. Release train via `release/x.x.x` → `testing`.
3. **Human initiates** staging and production promotions.
4. Use feature vs release PR templates under `.github/PULL_REQUEST_TEMPLATE/`.

## Semantic Versioning (SemVer)

- Canonical source of truth: `VERSION` in repo root.
- PRs must declare version impact (`major`, `minor`, `patch`, or `none`).
- See `docs/governance/semantic-versioning.md` and `docs/governance/playbooks/release-runbook.md`.
