# Changelog

All notable changes to **HATH0R CLI** (`hath0r-cli`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Factory Manager bot CRUD: `hath0r factory create|update|delete` (#64)
- Preflight bot: `hath0r preflight run` (#67)
- Deploy test bot: `hath0r deploy pre|post` (#66)
- Quality gates bot: `hath0r quality check <pr>` with Sonar hard-stop aggregate (#68)
- Release bot: `hath0r release validate|notes|publish` (#69)
- Docs bots: `hath0r docs wiki` and `hath0r docs share` (#70, #71)
- `cfg/quality-gates.json`, `cfg/factories/quality-release-factory.yaml`, governance docs

## [0.2.0] — 2026-09-18

First public **OpenSource release train** for the operator CLI: structured machine JSON, packaging surfaces, GitHub Release assets, and PyPI publication.

### Highlights

- Package / binary version **0.2.0**
- Response envelope **`hath0r.cli.response/1`**
- PyPI: https://pypi.org/project/hath0r-cli/0.2.0/
- GitHub Release: https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.2.0
- Tracking epic: [#30](https://github.com/Bayly-AI/HATH0R-CLI/issues/30)

### Added

#### Machine interface

- Global `--output json|text|auto` and shared response envelope infrastructure
- Structured JSON for:
  - `hath0r --version`
  - `hath0r doctor`
  - `hath0r kb path`
  - `hath0r kb products`
- Portable group-root discovery (`HATH0R_GROUP_ROOT`, walk-up, soft fallback)
- Golden contract fixtures under `tests/contract/fixtures/`
- Pytest suite, mypy, ruff, and CI workflow on PRs to `development`

#### Release packaging (#30)

- **Fileset** builder: `scripts/build_fileset.py` → `hath0r-fileset-<ver>.tar.gz` + `.sha256`
- **Standalone binary** builder: `scripts/build_binary.py` (PyInstaller) → `hath0r-<ver>-<platform>` + `.sha256`
- **npm thin client**: `packaging/npm/hath0r-client` (`@bayly-ai/hath0r`) — fixed operations, `shell: false`, env allowlist
- **Release workflow**: `.github/workflows/release.yml` (tag `v*` and `workflow_dispatch`)
- Install / release guide: `docs/hathor-guide-047-install-and-release-20260918.md`
- PyPI Trusted Publisher documentation and GitHub environments `pypi` / `test-pypi`

### Changed

- `VERSION` lockstep with `pyproject.toml` at **0.2.0**
- README install section documents pipx/PyPI, editable monorepo, and packaging targets

### Fixed

- Release workflow OIDC `id-token: write` for PyPI publish path (#32)

### Release assets (`v0.2.0`)

| Asset | Notes |
|-------|--------|
| `hath0r_cli-0.2.0-py3-none-any.whl` / `.tar.gz` | Python package (also on PyPI) |
| `hath0r-0.2.0-linux-x64` (+ `.sha256`) | Standalone engine |
| `hath0r-0.2.0-darwin-arm64` (+ `.sha256`) | Standalone engine |
| `hath0r-fileset-0.2.0.tar.gz` (+ `.sha256`) | Drop-in OpenSource fileset |
| CLI JSON Schema snapshots | From Framework contracts pin |

### Install

```sh
pipx install hath0r-cli
# or
python3 -m pip install hath0r-cli==0.2.0
hath0r --version
hath0r --output json --version
```

### Related issues / PRs

- Packaging epic: #30 · PR #31
- OIDC publish fix: #32 · PR #33
- Trusted Publisher docs: #34 · PR #35
- Structured JSON / tests / CI: #10–#18

## [0.1.0] — 2026-09

Initial private/control-tower CLI surface (pre-structured-output):

- `hath0r doctor`, `hath0r kb path`, `hath0r kb products`, `hath0r --version`
- Control-tower cfg pointers and OpenSource group orientation
- Text-oriented operator UX (Rich)

[Unreleased]: https://github.com/Bayly-AI/HATH0R-CLI/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.2.0
[0.1.0]: https://github.com/Bayly-AI/HATH0R-CLI/commits/development
