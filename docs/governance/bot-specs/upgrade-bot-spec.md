# Upgrade Bot Spec

> Product: **HATH0R Control Tower** · Subsystem: **Bot Specification**
> Status: **Active Spec** · Updated: 2026-10-05

## Bot identity

| Factory bot id | Class | Module |
|----------------|-------|--------|
| `upgrade-bot` | `UpgradeBot` | `src/hath0r_cli/bots/upgrade_bot.py` |
| `upgrade-verifier-bot` | `UpgradeVerifierBot` | same |
| `upgrade-announcer-bot` | `UpgradeAnnouncerBot` | same |

- **CLI binding:** `hath0r upgrade` (`src/hath0r_cli/commands/upgrade.py`)
- **Factory:** `cfg/factories/upgrade-factory.yaml`
- **Dependencies:** Python stdlib only (voice queue + `gh` used opportunistically)

## Subcommands & methods

| CLI subcommand | Method | Factory action |
|----------------|--------|----------------|
| `hath0r upgrade check [--version]` | `UpgradeBot.check(version)` | `upgrade-bot: check` |
| `hath0r upgrade run [--version --force --tests --no-rollback --file-issue --no-speak --dry-run]` | `UpgradeBot.run(...)` + `UpgradeAnnouncerBot.announce(...)` | `upgrade-bot: run` → `upgrade-announcer-bot: announce` |
| `hath0r upgrade verify [--tests --expect-version --announce --file-issue]` | `UpgradeVerifierBot.verify(...)` | `upgrade-verifier-bot: verify` |
| `hath0r upgrade rollback [--dry-run]` | `UpgradeBot.rollback(last_snapshot())` | `upgrade-bot: rollback` |
| `hath0r upgrade status [--limit]` | `UpgradeBot.status(limit)` | `upgrade-bot: status` |
| `hath0r upgrade schedule [--hour --minute --no-file-issue --write]` | `UpgradeBot.schedule_spec(...)` | — |

## Factory step arguments

| Action | Args |
|--------|------|
| `upgrade-bot: run` | `version`, `force`, `test_level` (`smoke`/`full`), `auto_rollback`, `repo` |
| `upgrade-verifier-bot: verify` | `expect_version`, `test_level` |
| `upgrade-announcer-bot: announce` | `file_issue`, `speak`, `repo` |

Steps share state through the workflow context key `upgrade_report`. The announcer step's success
mirrors the upgrade outcome so a failed upgrade fails the workflow.

## Report contract (`hath0r.upgrade.report/1`)

`run_id, started_at, finished_at, duration_ms, dry_run, test_level, install, from_version,
to_version, release, stages[], baseline, snapshot, verification{passed, checks[], summary},
failure{stage, code, message, hint}, rollback{success, …, verification}, outcome, success,
message, exit_code, announcement`.

`outcome` ∈ `up-to-date | dry-run | upgraded | failed | rolled-back | rollback-failed`.

## Exit codes

0 ok/no-op · 1 failed (rolled back or nothing changed) · 6 rollback failed (install unhealthy).

## Artifact hexad

- **Strategy**: `docs/governance/strategies/upgrade-strategy.md`
- **Procedure**: `docs/governance/procedures/upgrade-procedure.md`
- **Playbook**: `docs/governance/playbooks/upgrade-playbook.md`
- **Runbook**: `docs/governance/runbooks/upgrade-runbook.md`
- **Checklist**: `docs/governance/checklists/upgrade.md`
- **Bot spec**: `docs/governance/bot-specs/upgrade-bot-spec.md`
- **Guide**: `docs/hathor-guide-049-automated-upgrade-install-20261005.md`
- **Test-doc**: `tests/unit/test_upgrade_bot.py`
