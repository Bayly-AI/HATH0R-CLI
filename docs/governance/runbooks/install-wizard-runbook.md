# Runbook: Hath0r CLI & MCP Docker Install Wizard Operations

> Document Type: **Runbook** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `install-wizard-factory`
> Updated: 2026-11-01

## 1. First-Time Installation (Release Download)

```bash
# Interactive Install Wizard (downloads dependencies, installs CLI globally, builds & launches MCP Docker)
python3 scripts/install_hath0r.py

# Unattended / CI Install Wizard
python3 scripts/install_hath0r.py --yes

# Or via the release shell wrapper:
./release/install-wizard.sh
```

## 2. Day-2 Operations via `hath0r install-wizard` (`hath0r setup`)

```bash
# Check system prerequisites, global CLI PATH, hath0r-net, and Hath0r-MCP container health
hath0r install-wizard check

# Run the interactive or unattended install wizard from the CLI
hath0r install-wizard run
hath0r install-wizard run --yes --method pipx --mcp-port 38083

# Inspect last installation receipt and live container state
hath0r install-wizard status

# Repair Docker network, rebuild/restart Hath0r-MCP, and re-verify CLI
hath0r install-wizard repair

# Stop and remove the Hath0r-MCP container deployed by the wizard
hath0r install-wizard uninstall
```

## 3. Verifying Endpoints

```bash
hath0r --version
curl -fsS http://127.0.0.1:38083/health
curl -fsS http://127.0.0.1:38083/ready
hath0r mcp check
```

## 4. Packaging Native `.dmg` / `.exe` Installers & Canonical `release/previous/<version>/` Rotation (`CR-RELEASE-ROTATION-001`)

```bash
# Rotate any previous release files out of release/ root into release/previous/<version>/
hath0r release rotate

# Build native macOS (.dmg) and Windows (.exe) Install Wizard launchers in release/ root
hath0r install-wizard package --target all

# Full release build + previous rotation + Framework release/ sync
hath0r release build

# Validate VERSION, CHANGELOG, and clean release/ root
hath0r release validate
```
