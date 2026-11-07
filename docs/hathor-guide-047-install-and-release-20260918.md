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

> **Official Install Wizard (Recommended):** The Install Wizard (`python3 scripts/install_hath0r.py`, `./release/install-wizard.sh`, or `hath0r install-wizard run`) installs all host dependencies (Python, `pipx`, Git, `curl`, Docker Engine & Compose v2), installs the `hath0r` CLI globally, stages the `Hath0r-MCP` `Dockerfile` & `docker-compose.yml`, provisions the `hath0r-net` Docker network, launches the `Hath0r-MCP` container (`127.0.0.1:38083:8083`), and verifies end-to-end health.
>
> **Automated upgrades:** once installed, keep the CLI current with `hath0r upgrade run`
> (verify + auto-rollback + announce).
> See [GUIDE-049](hathor-guide-049-automated-upgrade-install-20261005.md) and [`docs/governance/playbooks/install-wizard-playbook.md`](governance/playbooks/install-wizard-playbook.md).

### 0. Official Install Wizard (CLI + Hath0r MCP via Docker)

- **macOS Disk Image (`.dmg`)**: Open `release/Hath0r-Install-Wizard.dmg` (or `release/Hath0r-Install-Wizard-<ver>-macos.dmg`) and double-click **`Hath0r Install Wizard.app`** (or `Install Hath0r Wizard.command`).
- **Windows Executable (`.exe`)**: Launch `release/Hath0r-Install-Wizard.exe` (or `release/Hath0r-Install-Wizard-<ver>-windows-x64.exe`).

```sh
# Rebuild the macOS .dmg and Windows .exe Install Wizard installers:
hath0r install-wizard package --target all

# Interactive or automated full installation (dependencies + global CLI + Docker MCP):
python3 scripts/install_hath0r.py
# Or from the release directory:
./release/install-wizard.sh

# Post-install CLI wizard commands:
hath0r install-wizard check
hath0r install-wizard run
hath0r install-wizard status
hath0r install-wizard repair
```

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



## PyPI Trusted Publisher (required for OIDC publish)

GitHub Actions publishes with **OIDC trusted publishing** (no long-lived token in the default path).

### GitHub (already configured)

| Setting | Value |
|---------|-------|
| Repository | `Bayly-AI/HATH0R-CLI` |
| Workflow file | `release.yml` |
| Job | `publish-pypi` |
| Environment | `pypi` |
| Permissions | `id-token: write` |
| Environment URL | https://github.com/Bayly-AI/HATH0R-CLI/settings/environments |

Also: environment `test-pypi` for TestPyPI publishes.

### PyPI.org (configure once in the browser)

1. Sign in as a maintainer of project **`hath0r-cli`** (create the project on first pending publisher if needed).
2. Open **Publishing** (pending publisher or project publishing settings):
   - https://pypi.org/manage/account/publishing/
   - or https://pypi.org/manage/project/hath0r-cli/settings/publishing/
3. Add a **GitHub** trusted publisher with **exactly**:

| Field | Value |
|-------|-------|
| Owner | `Bayly-AI` |
| Repository | `HATH0R-CLI` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

4. Save. For a not-yet-uploaded project, use a **pending publisher**; the first successful publish claims the name.

### TestPyPI (optional)

Same form on https://test.pypi.org/manage/account/publishing/ with environment name **`test-pypi`**.

### Alternate: API token

If not using trusted publishing, set Actions secret **`PYPI_API_TOKEN`** on the `pypi` environment (and `TEST_PYPI_API_TOKEN` for TestPyPI). The workflow still accepts `password: ${{ secrets.PYPI_API_TOKEN }}` when present.

### Publish command

```sh
gh workflow run release.yml --ref development \
  -f publish_pypi=true \
  -f publish_test_pypi=false
```

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
