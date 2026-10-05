---
id: HATHOR-GUIDE-049
title: Automated upgrade & install (Upgrade Bot)
date: 2026-10-05
status: implemented
supersedes: none
related: HATHOR-GUIDE-047 (install and release matrix)
---

# Automated upgrade & install

The **Upgrade Bot** keeps the `hath0r` CLI current without an operator watching. It installs a
new release, **tests the result**, **rolls back automatically** if the tests fail, and
**announces** what happened — including a GitHub issue describing what must be fixed when an
upgrade does not pass.

```text
detect ─► check ─► preflight ─► baseline ─► snapshot ─► install ─► verify ─┬─► announce (upgraded)
                                                                          └─► rollback ─► re-verify ─► announce (issue)
```

## Quick start

```sh
hath0r upgrade check                 # what's installed, how, and is there a newer release?
hath0r upgrade run --dry-run         # show the plan, change nothing
hath0r upgrade run                   # upgrade + smoke tests + auto-rollback + announce
hath0r upgrade run --tests full      # also run tests/unit (source checkouts)
hath0r upgrade run --file-issue      # on failure, open/update a GitHub issue
hath0r upgrade status                # last report + history
hath0r upgrade verify                # test the current install (e.g. after a manual install)
hath0r upgrade rollback              # restore the snapshot from the last run
hath0r upgrade schedule --write      # nightly unattended run (launchd); see below
```

All subcommands support `-o json` and emit the standard `hath0r.cli.response/1` envelope.

## Install methods

The bot detects the method automatically and upgrades in place using the same method.

| Method | Detected when | Upgrade action | Snapshot / rollback |
|--------|---------------|----------------|---------------------|
| `source` | package lives in a git checkout of `hath0r-cli` (editable install) | `git fetch` → `git merge --ff-only origin/<branch>` → `pip install -e .` | record `HEAD` SHA → `git reset --hard <sha>` + `pip install -e .` |
| `pip` | regular site-packages install | download release wheel → verify SHA-256 → `pip install --upgrade --force-reinstall <wheel>` | reinstall previous release's wheel (checksum-verified) |
| `pipx` | interpreter under `pipx/venvs/` | same wheel, `pipx install --force <wheel>` | previous wheel via pipx |
| `binary` | PyInstaller frozen executable | download `hath0r-<ver>-<platform>` → verify → **test the staged binary before swapping** → atomic replace | copy kept in `~/.hath0r/upgrade/backups/` → restore |

Source-checkout guardrails (preflight): the working tree must be clean and on `development` or
`master`; the branch must fast-forward. Feature branches are never touched.

## Trust and safety rules

- **Checksums are mandatory.** The expected SHA-256 comes from the digest GitHub records for
  each release asset, or the `.sha256` sidecar. No checksum → the bot refuses (`CHECKSUM_MISSING`).
  Mismatch → the file is deleted and nothing is installed (`CHECKSUM_MISMATCH`).
- No `curl | sh`, no shell interpolation: every subprocess runs with an argv list.
- One run at a time: `~/.hath0r/upgrade/upgrade.lock` (stale locks from dead processes are reclaimed).
- Downgrades are refused unless an explicit `--version` is given together with `--force`.
- The bot module is stdlib-only, so it still works when the CLI's optional dependencies are broken.

## What "tested" means

`UpgradeVerifierBot` runs every check against the **installed** CLI in a fresh subprocess (the
running process still has the old code loaded):

| Check | Required | Passes when |
|-------|----------|-------------|
| `version` | yes | `hath0r -o json --version` reports ≥ the target release |
| `command-imports` | yes | every command in `COMMAND_REGISTRY` imports (the lazy group otherwise *hides* broken commands) |
| `cli-help` (binaries) | yes | root `--help` exits 0 |
| `doctor` | yes | `doctor` emits an envelope and has **no more failed checks than the pre-upgrade baseline** |
| `factory-validate` | advisory | factory manifests still validate |
| `unit-tests` (`--tests full`) | yes | `pytest -q -x tests/unit` passes (source checkouts) |

The doctor check compares against a baseline taken just before installing, so an environment
that was already partially unhealthy does not block upgrades — only regressions do.

## Outcomes, exit codes and announcements

| Outcome | Exit | Envelope state | Announced as |
|---------|------|----------------|--------------|
| `up-to-date` | 0 | ok | — (no-op) |
| `dry-run` | 0 | ok | — |
| `upgraded` | 0 | ok | info |
| `failed` (no rollback needed / disabled) | 1 | error | error + fix hint |
| `rolled-back` | 1 | error | error + fix hint; previous version restored and re-verified |
| `rollback-failed` | 6 | degraded | **critical** — install needs manual repair |

Announcement channels (`UpgradeAnnouncerBot`):

1. **Console / envelope** — message, failing stage, failing checks, the fix hint.
2. **Report** — `~/.hath0r/upgrade/last-run.json` (full) and `history.jsonl` (one line per run).
3. **Voice queue** — a spoken notification is queued for the speaker bot (best-effort; `--no-speak` disables).
4. **GitHub issue** (`--file-issue`, on by default in the nightly factory workflow) — titled
   `[upgrade-bot] hath0r <ver> upgrade failed: <CODE> at <stage>`, with environment, error, the
   verification table, rollback result and reproduction commands. If an identical issue is
   already open the bot **comments on it** instead of opening a duplicate.

Set `HATH0R_UPGRADE_HOME` to move the state directory.

## First-time install (bootstrap)

The Upgrade Bot can only run once `hath0r` exists, so a fresh machine uses the stdlib bootstrap,
which applies the same checksum rules and then hands over to the bot's verifier:

```sh
python3 scripts/install_hath0r.py              # latest release, pipx if available else pip
python3 scripts/install_hath0r.py --version 0.9.0 --installer pip --file-issue
```

It runs `hath0r upgrade verify --expect-version <ver> --announce` at the end, so a broken fresh
install is reported exactly like a broken upgrade. Developer checkouts keep using
`pip install -e ".[dev]"` (GUIDE-047).

## Unattended operation

**Factory** (`cfg/factories/upgrade-factory.yaml`):

```sh
hath0r factory run upgrade-factory --workflow upgrade-check
hath0r factory run upgrade-factory --workflow upgrade-and-verify     # nightly 04:17 in the manifest
hath0r factory run upgrade-factory --workflow verify-install
```

In `upgrade-and-verify` the run step uses `on_failure: continue` so the announcer always runs;
the announcer step then fails the workflow when the upgrade did not pass.

**Local schedule (macOS launchd):**

```sh
hath0r upgrade schedule                    # print plist + crontab alternative
hath0r upgrade schedule --write            # write ~/Library/LaunchAgents/com.baylyai.hath0r.upgrade.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.baylyai.hath0r.upgrade.plist
launchctl bootout   gui/$(id -u)/com.baylyai.hath0r.upgrade   # disable
```

Scheduled runs log to `~/.hath0r/upgrade/scheduled.log` and file issues by default
(`--no-file-issue` to opt out). Issue filing uses the `gh` CLI, so the scheduled user must be
logged in (`gh auth status`).

## Related documents

- Strategy — `docs/governance/strategies/upgrade-strategy.md`
- Procedure — `docs/governance/procedures/upgrade-procedure.md`
- Playbook (failure triage) — `docs/governance/playbooks/upgrade-playbook.md`
- Runbook (day-2 ops) — `docs/governance/runbooks/upgrade-runbook.md`
- Checklist — `docs/governance/checklists/upgrade.md`
- Bot spec — `docs/governance/bot-specs/upgrade-bot-spec.md`
- Install & release matrix — `docs/hathor-guide-047-install-and-release-20260918.md`
