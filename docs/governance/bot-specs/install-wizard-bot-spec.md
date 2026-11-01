# Install Wizard Bot Spec

> Product: **HATH0R Control Tower** · Subsystem: **Bot Specification**
> Status: **Active Spec** · Updated: 2026-11-01

## Bot Identity

| Factory bot id | Class | Module |
|----------------|-------|--------|
| `install-wizard-bot` | `InstallWizardBot` | `src/hath0r_cli/bots/install_wizard_bot.py` |

- **CLI binding:** `hath0r install-wizard` / `hath0r setup` (`src/hath0r_cli/commands/install_wizard.py`)
- **Bootstrap entrypoint:** `scripts/install_hath0r.py` & `release/install-wizard.sh`
- **Factory:** `cfg/factories/install-wizard-factory.yaml`

## Subcommands & Methods

| CLI subcommand | Method | Factory action |
|----------------|--------|----------------|
| `hath0r install-wizard check` | `InstallWizardBot.check_environment()` | `install-wizard-bot: check` |
| `hath0r install-wizard run` | `InstallWizardBot.run_wizard(...)` | `install-wizard-bot: run` |
| `hath0r install-wizard status` | `InstallWizardBot.status()` | `install-wizard-bot: status` |
| `hath0r install-wizard repair` | `InstallWizardBot.repair(...)` | `install-wizard-bot: repair` |
| `hath0r install-wizard uninstall` | `InstallWizardBot.uninstall(...)` | `install-wizard-bot: uninstall` |

## Receipt Contract (`hath0r.install.receipt/1`)

Persisted at `~/.hath0r/install/INSTALL_RECEIPT.json`:
- `schema`: `"hath0r.install.receipt/1"`
- `run_id`, `started_at`, `finished_at`, `duration_ms`, `success`, `outcome`
- `dependencies`: `{python, pipx, git, curl, docker, docker_compose, docker_daemon}`
- `cli`: `{method, version, binary_path, on_path, sha256}`
- `mcp`: `{mcp_dir, dockerfile, compose_file, network, container_name, image, host_port, ready_url, healthy}`
- `verification`: `{cli_verified, mcp_ready, mcp_config_path}`
- `stages`: `[{stage, status, ...}]`

## Artifact Hexad

- **Strategy**: `docs/governance/strategies/install-wizard-strategy.md`
- **Procedure**: `docs/governance/procedures/install-wizard-procedure.md`
- **Playbook**: `docs/governance/playbooks/install-wizard-playbook.md`
- **Runbook**: `docs/governance/runbooks/install-wizard-runbook.md`
- **Bot Spec**: `docs/governance/bot-specs/install-wizard-bot-spec.md`
- **Workflow / Factory**: `cfg/factories/install-wizard-factory.yaml`
