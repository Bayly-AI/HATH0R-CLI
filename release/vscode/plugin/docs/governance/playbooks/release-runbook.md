# Release Runbook — Semantic Versioning Promotion

> Scope: **Hath0r Ecosystem Release Automation**  
> Rule: **CR-BAI-001 / cr-semver-gov-001**

---

## Pre-Release Phase (on `development`)

1. Verify `development` branch is green across all CI checks and tests:
   ```bash
   git checkout development && git pull origin development
   ./bin/hath0r-bootstrap.sh test
   ```
2. Determine release version according to cumulative PR impacts:
   - Any `semver:major` -> bump `MAJOR`, reset `MINOR` and `PATCH` to 0.
   - Any `semver:minor` -> bump `MINOR`, reset `PATCH` to 0.
   - Only `semver:patch` -> bump `PATCH`.

## Release Branch Creation

3. Create the release train branch:
   ```bash
   git checkout -b release/X.Y.Z development
   ```
4. Update `VERSION` in root:
   ```bash
   echo "X.Y.Z" > VERSION
   ```
5. Update `CHANGELOG.md` with release summary and linked PRs/issues.
6. Commit changes:
   ```bash
   git commit -am "chore(release): bump version to X.Y.Z"
   git push -u origin release/X.Y.Z
   ```

## Environment Promotion Path

7. Promote to `testing`:
   - Open PR: `release/X.Y.Z` -> `testing`
   - Automated test suite runs.
   - Merge PR into `testing`.
8. Promote to `staging`:
   - Open PR: `testing` -> `staging`
   - **Mandatory Human Gate**: Owner review and staging deployment verification.
   - Merge PR into `staging`.
9. Promote to `master` (Production):
   - Open PR: `staging` -> `master`
   - **Mandatory Human Gate**: Final production signoff.
   - Merge PR into `master`.

## Post-Merge Release Tagging

10. On `master`:
    ```bash
    git checkout master && git pull origin master
    git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
    git push origin "vX.Y.Z"
    ```
11. Create GitHub Release referencing `vX.Y.Z` with changelog notes.
12. Back-merge `master` into `development` to ensure version sync.
