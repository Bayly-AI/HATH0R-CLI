# Semantic Versioning Checklist

## PR Author Checklist
- [ ] PR title adheres to Conventional Commits format (`feat:`, `fix:`, `chore:`, etc.).
- [ ] PR description specifies **Version Impact**: `major`, `minor`, `patch`, or `none`.
- [ ] Canonical `VERSION` in root is unmodified on feature PRs (bump happens on release branch).
- [ ] All code, test fixtures, and schema samples reflect canonical SemVer.

## PR Reviewer Checklist
- [ ] Version impact declaration matches the actual diff scope.
- [ ] Breaking changes are explicitly tagged as `semver:major` and documented.
- [ ] Quality gates (CI, SonarCloud) passed.

## Release Train Checklist
- [ ] Branch created as `release/X.Y.Z` from `development`.
- [ ] `VERSION` in root updated to `X.Y.Z`.
- [ ] `CHANGELOG.md` updated with release highlights.
- [ ] Passed promotion gates through `testing` and `staging`.
- [ ] Human approval obtained before merge to `staging` and `master`.
- [ ] Tag `vX.Y.Z` published to GitHub.
