# SonarCloud Quality Gates (PR hard stop)

> Control tower: `Bayly-AI/HATH0R-CLI`  
> Ticket track: PR quality gates — SonarCloud hard stop (all-repos)

## Policy (CRITICAL)

1. **SonarCloud Quality Gate** is the **only** canonical threshold source for ratings, coverage, duplications, security hotspots, etc.
2. **Do not** invent or relax project-local threshold numbers in `sonar-project.properties` (no `sonar.coverage.minimum`, no homemade rating floors that diverge from the cloud gate).
3. If the Quality Gate **fails**, the PR **cannot** be merged until fixed (required check **SonarCloud Quality Gate**).
4. Fix findings; **do not** weaken the org/project Quality Gate to go green.

## CI

Workflow: `.github/workflows/sonarcloud-quality-gate.yml`

- Runs on PRs into `development` / `testing` / `staging` / `master`
- Runs scan against **SonarCloud** (`https://sonarcloud.io`)
- Sets `sonar.qualitygate.wait=true` so the job **fails** when the gate fails

Required check context name: **`SonarCloud Quality Gate`**

## Required secrets / variables

| Name | Type | Purpose |
|------|------|---------|
| `SONAR_TOKEN` | Actions **secret** | SonarCloud analysis token (repo or org) |
| `SONAR_ORGANIZATION` | Actions **variable** (optional) | SonarCloud org key; default `bayly-ai` if unset; file `sonar.organization` wins when present |

Never commit tokens. Store operator copies under `/Users/raybayly/Development/.credentials/` if needed for local runs — not in git.

## sonar-project.properties (allowed keys)

Allowed (identity + analysis scope only), examples:

```properties
sonar.projectKey=bayly-ai_HATH0R-CLI
sonar.organization=bayly-ai
sonar.projectName=HATH0R-CLI
sonar.sources=src
sonar.tests=tests
sonar.exclusions=**/node_modules/**,**/dist/**,**/coverage/**
sonar.python.version=3.11
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.python.coverage.reportPaths=coverage.xml
```

**Forbidden** in-repo (examples): local quality-gate threshold overrides, minimum coverage percentages that try to replace the cloud gate, complexity caps that contradict the gate.

## Branch protection

On protected branches, require status check:

- `SonarCloud Quality Gate`

Public repos: applied via API where plan allows. Private repos: enable when protection API available; CI still fails closed when `SONAR_TOKEN` is set.

## Operator bootstrap

1. Create/bind SonarCloud project to the GitHub repo (org Quality Gate attached — **do not customize thresholds** without change-control).
2. Create token → add `SONAR_TOKEN` secret on repo or org.
3. Set `SONAR_ORGANIZATION` variable if not `bayly-ai`.
4. Merge this workflow + `sonar-project.properties`.
5. Confirm PR check appears and blocks on failed gate.
6. Complete checklist `docs/governance/checklists/sonarcloud-pr-gate.md`.

## Playbook

`docs/governance/playbooks/sonarcloud-quality-gate-playbook.md`
