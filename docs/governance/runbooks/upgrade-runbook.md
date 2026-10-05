# Runbook: CLI Upgrade Operations

> Document Type: **Runbook** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `upgrade-factory`
> Updated: 2026-10-05

## 1. Routine

```bash
hath0r upgrade check                     # daily glance / before starting work
hath0r upgrade run --dry-run             # see exactly what would happen
hath0r upgrade run                       # upgrade + verify + auto-rollback + announce
hath0r upgrade status                    # outcome of the last run + history
```

After any manual install or environment change: `hath0r upgrade verify` (add `--tests full` on a
source checkout).

## 2. Enrol a machine in nightly upgrades

```bash
gh auth status                           # issue filing needs an authenticated gh
hath0r upgrade schedule --write
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.baylyai.hath0r.upgrade.plist
```

Verify enrolment: `launchctl print gui/$(id -u)/com.baylyai.hath0r.upgrade | head`.
Logs: `~/.hath0r/upgrade/scheduled.log`. Disable: `launchctl bootout gui/$(id -u)/com.baylyai.hath0r.upgrade`.
Linux: use the crontab line printed by `hath0r upgrade schedule`.

## 3. Factory execution

```bash
hath0r factory validate
hath0r factory run upgrade-factory -w upgrade-check
hath0r factory run upgrade-factory -w upgrade-and-verify --dry-run
hath0r factory run upgrade-factory -w upgrade-and-verify
hath0r factory run upgrade-factory -w verify-install
```

## 4. Pin / hold a version

- Install a specific release: `hath0r upgrade run --version 0.9.0 --force`.
- Hold upgrades: unload the launchd job (§2) — the bot has no "hold" flag by design.

## 5. Manual rollback

```bash
hath0r upgrade rollback --dry-run        # shows the snapshot that would be restored
hath0r upgrade rollback
hath0r upgrade verify
```

## 6. Files

| Path | Content |
|------|---------|
| `~/.hath0r/upgrade/last-run.json` | Full report of the last run (`hath0r.upgrade.report/1`) |
| `~/.hath0r/upgrade/history.jsonl` | One summary line per run |
| `~/.hath0r/upgrade/backups/` | Binary snapshots (prune old ones manually) |
| `~/.hath0r/upgrade/upgrade.lock` | PID of the running upgrade |
| `~/.hath0r/upgrade/scheduled.log` | stdout/stderr of scheduled runs |

Override the directory with `HATH0R_UPGRADE_HOME`.

## 7. Escalation

Failures → `docs/governance/playbooks/upgrade-playbook.md`. `rollback-failed` is critical: follow
playbook §5 immediately.
