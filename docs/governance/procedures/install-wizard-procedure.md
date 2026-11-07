# Procedure: Hath0r CLI & Hath0r MCP (Docker) Install Wizard

> Document Type: **Procedure** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `install-wizard-factory`
> Updated: 2026-11-01

Normative 5-stage order of operations executed by `InstallWizardBot.run_wizard()` (`hath0r install-wizard run` / `hath0r setup` / `scripts/install_hath0r.py`).

| # | Stage | Action | Failure Code |
|---|-------|--------|--------------|
| 1 | `dependencies` | Inspect Python >=3.10, `pipx`/`pip`, `git`, `curl`, `docker`, and `docker compose`. Install missing tools (with operator approval or `--yes`) and ensure the Docker daemon is reachable. | `DEPENDENCY_MISSING`, `DEPENDENCY_INSTALL_FAILED`, `DOCKER_DAEMON_UNAVAILABLE` |
| 2 | `cli_install` | Resolve target release from GitHub Releases or local `release/` bundle, verify SHA-256 digest, install `hath0r` globally (`pipx`, `binary`, or `pip`), and ensure binary directory is on `PATH`. | `CHECKSUM_MISSING`, `CHECKSUM_MISMATCH`, `CLI_INSTALL_FAILED`, `CLI_PATH_MISSING` |
| 3 | `mcp_stage` | Stage `Hath0r-MCP` `Dockerfile`, `docker-compose.yml`, `requirements.txt`, and `knowledgebase/canonical/` into `~/.hath0r/mcp` (or workspace sibling `hath0r-mcp`), write `.env` defaults, and validate compose config. | `MCP_STAGE_FAILED`, `COMPOSE_CONFIG_INVALID` |
| 4 | `mcp_launch` | Create external Docker network `hath0r-net` with `com.hath0r.*` labels if absent, then build/pull and launch `Hath0r-MCP` (`docker compose -p hath0r up -d --build --wait hath0r-mcp`) on `127.0.0.1:38083`. | `DOCKER_NETWORK_FAILED`, `MCP_CONTAINER_LAUNCH_FAILED` |
| 5 | `verify` | Probe `http://127.0.0.1:38083/health` and `/ready`, provision `.hath0r/mcp.json`, run `UpgradeVerifierBot.verify()`, optionally register Claude Desktop connector, and write `~/.hath0r/install/INSTALL_RECEIPT.json`. | `MCP_READINESS_FAILED`, `CLI_VERIFICATION_FAILED` |
