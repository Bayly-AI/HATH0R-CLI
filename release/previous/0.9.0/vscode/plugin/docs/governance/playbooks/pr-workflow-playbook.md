# Playbook: PR workflow (agent + human)

## Scenario A — Feature delivery into development

1. Confirm GitHub issue exists.
2. `git fetch origin && git checkout development && git pull --ff-only`
3. `git checkout -b feature/<issue>-short-slug`
4. Implement; run local tests / `hath0r` preflight when available.
5. Push branch; open PR with **feature** template, base `development`.
6. Ensure `validate-promotion-path` and CI green.
7. Request CODEOWNERS review (`@somesayray`).
8. Agents may comment/review; merge only after required approvals + checks.
9. Run post-merge development checklist.

## Scenario B — Release train to testing

1. Ensure development is green and release notes/version ready (version ticket).
2. `git checkout development && git pull --ff-only`
3. `git checkout -b release/x.x.x` (SemVer)
4. Open **release** PR: `release/x.x.x` → `testing` (or `development` → `testing` if policy allows for that cut).
5. Deploy/validate testing environment.
6. Complete pre-promote-testing checklist.

## Scenario C — Human gate to staging (STOP for automation)

1. Human confirms testing sign-off.
2. Human initiates release PR: `testing` or `release/x.x.x` → `staging`.
3. Environment `staging` requires human approval.
4. Complete human-gate-before-staging checklist before merge.
5. Merge only after human approval + checks.

## Scenario D — Production (master)

1. Staging validated.
2. Human opens PR → `master` using release template.
3. Environment `production` requires human approval.
4. Merge; tag/release per version bot/ticket.

## Decision branches

| Situation | Action |
|-----------|--------|
| No issue number on branch | Stop; open issue; rename branch |
| Work PR targets staging/master | Close/retarget to development |
| Auto-bot tries to approve staging | Reject; human only |
| Promotion path CI red | Fix head/base; do not bypass |
| Private repo lacks branch protection | Rely on CI + CODEOWNERS + environments; escalate org plan |
