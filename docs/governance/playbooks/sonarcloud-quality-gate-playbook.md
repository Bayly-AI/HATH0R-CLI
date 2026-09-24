# Playbook: SonarCloud Quality Gate on PRs

## First-time setup

1. Log into SonarCloud with org admin.
2. Ensure GitHub org `Bayly-AI` is bound (or correct Sonar org).
3. Create project (or auto-provision on first scan) with **default/org Quality Gate** only.
4. Generate project/org token → GitHub secret `SONAR_TOKEN`.
5. Set Actions variable `SONAR_ORGANIZATION` if needed.
6. Open a PR; confirm job **SonarCloud Quality Gate** runs.

## PR failed the gate

1. Open SonarCloud project → PR decoration / Quality Gate details.
2. Fix **blocker/new code** conditions required by the gate (bugs, vulnerabilities, coverage on new code, etc.).
3. Push commits; do **not** edit gate conditions.
4. Re-run checks until green.

## Missing SONAR_TOKEN

Job fails closed with explicit error. Add secret, then re-run workflow.

## Local preview (optional)

```bash
# token from credentials store — do not print
export SONAR_TOKEN="..."   # from secure store
sonar-scanner -Dsonar.qualitygate.wait=true
```

Prefer CI as source of truth.

## Anti-patterns

- Lowering coverage % in `sonar-project.properties` to pass CI
- Disabling the workflow on protected branches
- Marking the check optional on branch protection
- Using a second homemade gate that conflicts with SonarCloud
