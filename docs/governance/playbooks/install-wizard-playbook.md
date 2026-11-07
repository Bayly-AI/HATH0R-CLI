# Playbook: Hath0r Install Wizard Triage & Recovery

> Document Type: **Playbook** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `install-wizard-factory`
> Updated: 2026-11-01

## 1. Failure Modes & Remediation

### `DOCKER_DAEMON_UNAVAILABLE`
- **Symptom**: `docker info` fails during Stage 1 (`dependencies`) or Stage 4 (`mcp_launch`).
- **Resolution**:
  - macOS: Start Docker Desktop (`open -a Docker`) or Colima (`colima start`), wait until `docker info` succeeds, and run `hath0r install-wizard repair`.
  - Linux: Run `sudo systemctl enable --now docker` and ensure the current user is in the `docker` group (`sudo usermod -aG docker $USER`).

### `CLI_PATH_MISSING`
- **Symptom**: `hath0r` installed via `pipx` or `binary` into `~/.local/bin`, but `which hath0r` is empty in the current shell.
- **Resolution**:
  - Run `pipx ensurepath` or source your shell profile (`source ~/.zshrc` or `source ~/.bashrc`).
  - Re-verify with `hath0r install-wizard check`.

### `CHECKSUM_MISMATCH` / `CHECKSUM_MISSING`
- **Symptom**: Downloaded release wheel or binary SHA-256 does not match `CHECKSUMS.sha256` or GitHub asset digest.
- **Resolution**:
  - Refuses to install by design (`CR-AGENTIC-SEC-001`). Re-run `hath0r release build` to regenerate synchronized checksums or re-download from official GitHub Releases.

### `MCP_CONTAINER_LAUNCH_FAILED` / `MCP_READINESS_FAILED`
- **Symptom**: Container `Hath0r-MCP` fails to start or `http://127.0.0.1:38083/ready` times out.
- **Resolution**:
  - Check port conflicts on `38083` (`lsof -i :38083`) or override port via `hath0r install-wizard run --mcp-port 38084`.
  - Inspect logs: `docker compose -p hath0r -f ~/.hath0r/mcp/docker-compose.yml logs --tail=100 hath0r-mcp`.
  - Run `hath0r install-wizard repair` to recreate `hath0r-net` and rebuild `Hath0r-MCP`.
