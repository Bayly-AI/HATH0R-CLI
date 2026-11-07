# Strategy: Hath0r CLI & Hath0r MCP (Docker) Install Wizard

> Document Type: **Strategy** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `install-wizard-factory`
> Status: **Active** · Updated: 2026-11-01

## 1. Problem

Operators and developers downloading a release of the Hath0r ecosystem need a single, deterministic, guided onboarding workflow that:
1. Installs all required host dependencies (Python 3.10+, `pipx`/`pip`, Git, `curl`, Docker Engine, and Docker Compose v2).
2. Installs the **`hath0r` CLI globally** on `PATH` with cryptographic SHA-256 verification.
3. Stages the **`Hath0r-MCP` Dockerfile, `docker-compose.yml`, and canonical knowledgebase**.
4. Provisions the canonical **`hath0r-net`** Docker network (`CR-DOCKER-HATH0R-GROUP-001`) and launches the hardened **`Hath0r-MCP` container** on `127.0.0.1:38083`.
5. Verifies end-to-end readiness (`http://127.0.0.1:38083/ready`, `hath0r upgrade verify`, `hath0r mcp check`) and produces an immutable installation receipt.

Previously, CLI installation (`scripts/install_hath0r.py`) and MCP container deployment (`hath0r mcp install --container`) were separate steps requiring manual dependency management.

## 2. Goals

1. **Single Release & Download Entrypoint**: Provide both a standalone zero-dependency bootstrap wizard (`scripts/install_hath0r.py` / `release/install-wizard.sh`) and a built-in CLI wizard (`hath0r install-wizard` / `hath0r setup`) owned by `InstallWizardBot`.
2. **Automated Dependency Resolution**: Detect and install missing prerequisites (Python, `pipx`, Git, Docker, Docker Compose v2) and start the Docker daemon when inactive.
3. **Global CLI Availability**: Install `hath0r` globally via `pipx`, standalone binary (`~/.local/bin/hath0r` or `/usr/local/bin/hath0r`), or `pip --user`, ensuring shell `PATH` registration.
4. **Turnkey Docker MCP Provisioning**: Stage the hardened multi-stage `Hath0r-MCP` `Dockerfile` (`USER 10001:10001`), `docker-compose.yml` (`name: hath0r`, network `hath0r-net`, labels `com.hath0r.*`), and canonical knowledgebase under `~/.hath0r/mcp`, then build/pull and launch `Hath0r-MCP`.
5. **Cryptographic & Operational Verification**: Verify SHA-256 digests before installing, verify `/health` and `/ready` endpoints on port `38083`, wire `.hath0r/mcp.json`, and persist `~/.hath0r/install/INSTALL_RECEIPT.json`.

## 3. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Two-tier architecture (stdlib bootstrap + `InstallWizardBot`) | Allows execution on a brand-new machine before `hath0r` is installed, while keeping full orchestration, repair, and status inside `HATH0R-CLI` (`CR-CLI-FEATURE-STANDARD-001`). |
| Embedded fallback `Dockerfile` & `docker-compose.yml` in `InstallWizardBot` | Guarantees that even if a user downloads only the CLI binary or wheel without a git checkout of `HATH0R-MCP`, the wizard can still materialize a compliant, hardened `Hath0r-MCP` Docker environment and launch the container. |
| Canonical `hath0r` Docker group & `hath0r-net` | Enforces `CR-DOCKER-HATH0R-GROUP-001` (`name: hath0r`, `container_name: Hath0r-MCP`, `127.0.0.1:38083:8083`, `com.hath0r.*` labels). |
| Non-root & read-only container hardening | Enforces `CR-AGENTIC-SEC-001` (`USER 10001:10001`, `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges:true`). |
| Immutable `INSTALL_RECEIPT.json` | Persists full provenance (versions, SHA-256 digests, paths, container health, verification checks) under `~/.hath0r/install/INSTALL_RECEIPT.json`. |
