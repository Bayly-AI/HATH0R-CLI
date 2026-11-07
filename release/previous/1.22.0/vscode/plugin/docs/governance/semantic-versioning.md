# Semantic Versioning Policy & Specification

> Product: **HATH0R Agentic Framework & Ecosystem**  
> Status: **Canonical Policy** (cr-semver-gov-001 / CR-BAI-001)  
> Updated: 2026-09-24

---

## 1. Core Principle & Format

All repositories across the Hath0r ecosystem strictly adhere to **Semantic Versioning 2.0.0** (`MAJOR.MINOR.PATCH`):

- **`MAJOR`**: Incompatible API, contract, schema, or structural changes.
- **`MINOR`**: Backwards-compatible new features, capabilities, or schema additions.
- **`PATCH`**: Backwards-compatible bug fixes, security patches, documentation enhancements, and internal chores.

Optional pre-release identifiers (`-rc.1`, `-alpha.1`) are permitted exclusively on release staging branches (`release/x.x.x`).

---

## 2. Single Canonical Source of Truth

To eliminate version drift across artifacts, configurations, and manifests:

1. **`VERSION` file in repository root** is the **exclusive canonical source of truth** for repository version state.
2. Package manifests (e.g. `pyproject.toml`, `package.json`, `Cargo.toml`, Helm `Chart.yaml`) MUST derive from or match `VERSION`.
3. In-code version constants MUST read from `VERSION` or import from package metadata aligned with `VERSION`.

---

## 3. PR Version Impact Declaration

Every PR targeting `development` MUST declare its semantic version impact in the PR description or via GitHub labels:

- `semver:major` — Breaking architectural or contract change.
- `semver:minor` — New feature, command, or schema addition.
- `semver:patch` — Fix, patch, refactor, or optimization.
- `semver:none` — Documentation, meta, or internal maintenance with no artifact impact.

Automated CI gate (`.github/workflows/version-policy-guard.yml`) enforces that all work PRs declare version impact prior to merge.

---

## 4. Promotion & Release Train

Releases are cut from `development` onto a dedicated release branch:

```text
development → release/x.x.x → testing → staging → master (Production)
```

1. **Branch creation**: `git checkout -b release/x.x.x development`
2. **Version bump**: Update `VERSION` and associated manifests (`pyproject.toml`, `package.json`).
3. **Changelog**: Append release notes in `CHANGELOG.md`.
4. **Promotion**: Promote along canonical environment path.
5. **Tag & Release**: Upon successful merge into `master`, tag `vX.Y.Z` and publish GitHub release notes.
