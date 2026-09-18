---
id: HATHOR-GUIDE-047
title: Install and release matrix (HATH0R CLI)
date: 2026-09-18
status: implemented
---

# Install and release matrix

This guide covers **Tier 0** distribution for OpenSource HATHOR (issue #30):
PyPI/pipx, GitHub Release binaries, fileset tarball, and the npm thin client.

## Version matrix

| Surface | Identity | Current |
|---------|----------|---------|
| Python package | `hath0r-cli` | `0.2.0` |
| Binary | `hath0r` | same as package |
| Fileset | `hath0r-fileset-<ver>.tar.gz` | same as package |
| npm client | `@bayly-ai/hath0r` | `0.2.0` |
| Envelope | `hath0r.cli.response/1` | major lock |

`VERSION`, `pyproject.toml`, and npm `package.json` must stay in lockstep for a release train.

## Tier 0 install methods

### 1. pip / pipx (recommended operators)

```sh
python3 -m pip install hath0r-cli
# or isolated:
pipx install hath0r-cli
hath0r --version
hath0r doctor
```

Editable monorepo install (developers):

```sh
cd HATH0R-CLI
python3 -m pip install -e ".[dev]"
```

### 2. Standalone binary (GitHub Releases)

1. Download `hath0r-<ver>-<platform>` and `.sha256` from the release.
2. Verify checksum (`shasum -a 256 -c …`).
3. `chmod +x` and place on `PATH`.
4. Run `hath0r --output json --version`.

Build locally:

```sh
pip install -e ".[release]"
python scripts/build_binary.py
```

### 3. OpenSource fileset (drop-in project pack)

```sh
python scripts/build_fileset.py
tar -tzf dist/fileset/hath0r-fileset-0.2.0.tar.gz | head
# unpack, then:
./bin/hath0r-bootstrap.sh
```

Contains `AGENTS.md`, `cfg/` stubs, `.hath0r/` KB stub, pinned contracts, `MANIFEST.json`.
No secrets and no absolute developer paths.

### 4. npm thin client

```sh
cd packaging/npm/hath0r-client
npm install
npm test
npm run build
# publish (maintainers): npm publish --access public
```

Requires a separate engine install (`hath0r` on PATH). Never pass untrusted argv into `runOperation`.

## CI / release automation

| Workflow | Purpose |
|----------|---------|
| `.github/workflows/ci.yml` | PR gate: pytest, mypy, ruff, fixtures |
| `.github/workflows/release.yml` | Tag `v*` / manual: wheel+sdist, fileset, binaries, optional PyPI |

Secrets (optional):

- `TEST_PYPI_API_TOKEN` — TestPyPI
- `PYPI_API_TOKEN` — production PyPI

## Trust rules

- Prefer checksummed Release assets over unsigned scripts.
- Never recommend `curl | sh` without verification.
- Libraries are thin clients; the CLI remains host authority.
- Member KB stubs stay pointers; group hub is canonical.

## Makefile helpers

```sh
make fileset
make binary          # requires [release] extra
make wheel
make release-local   # fileset + wheel (binary optional)
```
