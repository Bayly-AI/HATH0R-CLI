# AGENTS.md — HATH0R CLI (OpenSource Control Tower)

> Role: **OpenSource Project control tower + operator/developer CLI (`hath0r`)** · group `hath0r-opensource`  
> Updated: 2026-09-23

## Group membership (CRITICAL)

| Field | Value |
|-------|-------|
| Group | `hath0r-opensource` |
| Project | **OpenSource Project** |
| Group root | `/Users/raybayly/Development/OpenSource` |
| **Control tower** | **this repo** (`HATH0R-CLI`) |
| This product | `HATH0R-CLI` |
| GitHub | `Bayly-AI/HATH0R-CLI` |
| Local path | `/Users/raybayly/Development/OpenSource/HATH0R-CLI` |
| Canonical KB | `/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase` |
| Operator CLI | `hath0r` |
| KB mode | stub → group hub |
| Tower flag | `is_control_tower: true` |

### Canonical siblings (OpenSource Project members)

Every git repo under the group root is part of the OpenSource Project. Current canonical set:

- **Control tower / CLI**: `/Users/raybayly/Development/OpenSource/HATH0R-CLI` → `Bayly-AI/HATH0R-CLI`
- Framework: `/Users/raybayly/Development/OpenSource/hath0r` → `Bayly-AI/HATH0R-Agentic-Framework`
- POC: `/Users/raybayly/Development/OpenSource/hath0r-poc` → `Bayly-AI/HATH0R-Agentic-POC`

Group rules: `/Users/raybayly/Development/OpenSource/AGENTS.md`  
Group policy: `/Users/raybayly/Development/OpenSource/WARP.md`

## Control tower duties (CRITICAL — cr-kb-tower-001)

1. Own suite orientation: `cfg/control-tower.yaml`, `cfg/suite.yaml`, `cfg/products.yaml`, `cfg/knowledge-tower.yaml`.
2. Mediate operator paths via `hath0r` (doctor, KB path resolution, product catalog).
3. Keep member knowledgebases as **stubs**; durable group KB lives at the OpenSource hub.
4. Do **not** treat private internal product trees (e.g. BAI/AEGIS) as OpenSource canonical sources.

## Framework hidden root (CRITICAL — cr-hath0r-root-001)

Use **only** `.hath0r/` for framework-created / modified / saved project metadata (including this repo’s KB stub).

Do **not** use `.ai/`, `.aegis/`, or `.infraOS/`.

## Knowledgebase (CRITICAL — cr-kb-tower-001)

1. Point local knowledgebase operations at the OpenSource group hub.
2. Keep `.hath0r/knowledgebase` as stub/pointer only (see README there).
3. Framework `docs/` is the **canonical OpenSource documentation** corpus.
4. Do **not** treat private internal product trees as OpenSource canonical sources.

## Branch & PR targets (CRITICAL — cr-branch-gov-001)

1. **Issue first**: create a GitHub issue before any work branch. No issue → no branch.
2. Branch from `development` only, using:
   `feature|bugfix|hotfix|enhancement|research|fix|chore/<issue-number>-short-slug`
   Example: `chore/51-define-branch-rules`
3. Open the PR with **base = `development`** (work never targets testing/staging/master).
4. **Owner approval required** before merge (`@somesayray` via CODEOWNERS + branch protection).
5. Merge into **`development` only** for feature/bugfix/hotfix work.
6. Cut **`release/x.x.x`** from `development` when promoting a release train.
7. Promote via `development`/`release/x.x.x` → `testing` → `staging` → `master` — do not skip stages.

### Canonical branches (locked)

`development` (default), `testing`, `staging`, `master`

- Must not be deleted
- Must not be used as feature/work branches
- Must not be merged into each other except along the promotion path above
- Branch protection: PR required, 1 approving review, code-owner review, no force-push, no deletions, `validate-promotion-path` required, conversation resolution required

### Release branches

`release/x.x.x` — SemVer release trains only (not feature work).

Forbidden: work PRs targeting `master`, `testing`, or `staging`; PRs without an issue number in the work branch name; merging canonical branches sideways.

See `docs/governance/branch-rules.md`.

## Config pointers in this repo

- `cfg/control-tower.yaml` — tower identity
- `cfg/suite.yaml` — suite / group orientation
- `cfg/products.yaml` — product catalog (tower copy)
- `cfg/knowledge-tower.yaml` — KB + tower flags
- `.hath0r/knowledgebase/README.md` — stub pointer

## CR-BAI-001: Environment Promotion Path (CRITICAL — org-wide)

Canonical policy: `/Users/raybayly/Development/BAI/WARP.md` (org-wide). Group mirror: `/Users/raybayly/Development/OpenSource/WARP.md`.

Required order (never skip):

```text
local → development → testing → staging → master (Production)
```

CI enforcement: `.github/workflows/enforce-promotion-path.yml`

- PRs into `testing` must come from `development` or `release/x.x.x`
- PRs into `staging` must come from `testing` or `release/x.x.x` (human review)
- PRs into `master` must come from `staging` or `release/x.x.x` (human review)
- Each stage needs deploy + URL validation before the next promote

## Credentials

`/Users/raybayly/Development/.credentials/<service>/.env` — never hardcode or print secrets.

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

Canonical flow, human gates, and PR templates:

- `docs/governance/pr-workflow.md`
- Playbook: `docs/governance/playbooks/pr-workflow-playbook.md`
- Templates: `.github/PULL_REQUEST_TEMPLATE/feature.md`, `release.md`
- CI: `.github/workflows/pr-workflow-guard.yml` + `enforce-promotion-path.yml`

**Human review is mandatory** for merges into `staging` and `master`. Agents/bots are primary on work PRs into `development`. Testing is the last automated/agent-heavy gate before a human initiates staging.
## SonarCloud Quality Gate (CRITICAL)

- Canonical thresholds: **SonarCloud Quality Gate only** (do not modify gate thresholds ad hoc).
- PR check **SonarCloud Quality Gate** is a **hard stop** on failure.
- Docs: `docs/governance/sonarcloud-quality-gates.md`
- Workflow: `.github/workflows/sonarcloud-quality-gate.yml`
- Secret: `SONAR_TOKEN` (required)
## Documentation → MCP publish (CRITICAL)

| Group | MCP |
|-------|-----|
| Hath0r/OpenSource | Hath0r MCP / OpenSource hub |
| BAI | BAI-MCP |
| 1-Nation | 1-Nation-MCP |

- `cfg/mcp-doc-publish.json`
- `python3 scripts/publish-docs-to-mcp.py`
- `docs/governance/mcp-doc-publish.md`
