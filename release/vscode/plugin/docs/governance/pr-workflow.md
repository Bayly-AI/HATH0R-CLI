# PR workflow hardening (CR-BAI-001 / cr-branch-gov-001)

> Control tower: `Bayly-AI/HATH0R-CLI`  
> Companion: `docs/governance/branch-rules.md`  
> Issue track: PR workflow hardening (all-repos)

## Canonical end-to-end flow

```text
1) GitHub issue created (required)
2) Work branch from development:
     feature|bugfix|hotfix|enhancement|research|fix|chore/<issue>-slug
3) Implement on work branch
4) PR: work branch → development
5) Review: agents/bots + required checks (validate-promotion-path, CI, quality gates)
6) Owner CODEOWNERS approval → merge → development
7) Cut release branch: release/x.x.x (from development when ready)
8) Promote → testing (deploy + validate)
9) HUMAN REVIEW GATE  ← hard stop for automated/agent-heavy path
   Human initiates release to staging
10) testing → release PR → Human review → merge → staging
11) staging → release PR → Human review → merge → master (Production)
```

### Hard stops

| Stage | Who reviews | Notes |
|-------|-------------|-------|
| Work PR → `development` | Agents/bots + CODEOWNERS (`@somesayray`) | Primary automation surface |
| → `testing` | CI + promotion path check | Deploy/validate before next stage |
| → `staging` | **Human required** | Human initiates; no silent auto-promote |
| → `master` | **Human required** | Production |

Never skip: `development → testing → staging → master`.

## PR types

### Feature / work PR
- **Base:** `development` only
- **Head:** work branch with issue number
- **Template:** `.github/PULL_REQUEST_TEMPLATE/feature.md`
- Agent review allowed; CODEOWNERS still required where protection applies

### Release / promotion PR
- **Base:** `testing` | `staging` | `master`
- **Head:** `development` or `release/x.x.x` (per stage rules in branch-rules)
- **Template:** `.github/PULL_REQUEST_TEMPLATE/release.md`
- Staging/master: human approval mandatory

## GitHub Environments

| Environment | Purpose | Required reviewers |
|-------------|---------|-------------------|
| `testing` | Deploy/validate testing | optional / CI-oriented |
| `staging` | Pre-production | **@somesayray (human)** |
| `production` | master / Production | **@somesayray (human)** |

Deploy workflows that promote past testing MUST target `staging` / `production` environments so GitHub blocks until a human approves.

## CI gates (minimum)

1. `validate-promotion-path` (required on protected branches)
2. Repo CI / tests
3. Sonar / quality gates when configured (hard stop — separate ticket)
4. CODEOWNERS review on protected branches

## Checklists

- `docs/governance/checklists/pr-pre-merge-development.md`
- `docs/governance/checklists/pr-post-merge-development.md`
- `docs/governance/checklists/pr-pre-promote-testing.md`
- `docs/governance/checklists/pr-human-gate-before-staging.md`
- `docs/governance/checklists/pr-release-to-master.md`

## Playbook

See `docs/governance/playbooks/pr-workflow-playbook.md`.

## Procedure summary

1. Open issue → branch from `development` with correct name.
2. Open **feature** PR → `development`; fill feature template.
3. Wait for checks + CODEOWNERS; merge.
4. When releasing: cut `release/x.x.x`, open **release** PR into `testing`.
5. After testing validation: **human** opens/approves PR into `staging`.
6. After staging validation: **human** opens/approves PR into `master`.

## Acceptance criteria (ticket)

- [x] Workflow documented and linked from AGENTS/WARP
- [x] Feature PRs cannot target staging/master (CI + branch rules)
- [x] Release path uses release/x.x.x and stage order
- [x] Human review required for staging and master (environments + policy)
- [x] Testing is last automated/agent-heavy gate before human-initiated staging
- [x] Procedure/playbook/runbook/checklist exist

## Platform limits (GitHub plan)

If environment **required reviewers** fail with a billing-plan error, the policy still holds:

1. CODEOWNERS + branch protection (public repos) require human owner on protected branches.
2. Checklists/playbook require human initiation for staging/master.
3. `pr-workflow-guard` labels `pr:human-gate` on staging/master PRs.
4. Upgrade org plan when environment required-reviewers become available; re-run environment setup.
