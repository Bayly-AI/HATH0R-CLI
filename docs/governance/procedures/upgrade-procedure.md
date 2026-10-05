# Procedure: Automated CLI Upgrade

> Document Type: **Procedure** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `upgrade-factory`
> Updated: 2026-10-05

Normative order of operations executed by `UpgradeBot.run()` (`hath0r upgrade run`). Each stage
records `{stage, status}` in the run report; a failure stops the pipeline at that stage.

| # | Stage | Action | Fails with |
|---|-------|--------|------------|
| 1 | detect | Determine install method, version, interpreter, repo root/branch/SHA (source) or binary path. | — |
| 2 | check | Read the latest (or `--version`) GitHub release; compare SemVer. Equal/older and no `--force` → **stop: up-to-date**. | `RELEASE_FEED_UNAVAILABLE`, `DOWNGRADE_REFUSED` |
| 3 | lock | Create `~/.hath0r/upgrade/upgrade.lock` (reclaim if the owning PID is dead). Skipped for `--dry-run`. | `UPGRADE_IN_PROGRESS` |
| 4 | preflight | source: clean tree + canonical branch. pip/pipx: wheel asset exists (+ `pipx` on PATH). binary: platform asset exists + install dir writable. | `SOURCE_TREE_DIRTY`, `SOURCE_BRANCH_NOT_CANONICAL`, `ASSET_MISSING`, `PIPX_MISSING`, `BINARY_NOT_WRITABLE` |
| — | dry-run | With `--dry-run`, report the plan and **stop**. Nothing is written. | — |
| 5 | baseline | Run `doctor` on the current install; record failed-check count. | — |
| 6 | snapshot | source: record SHA. binary: copy binary to `backups/`. pip/pipx: record version. | — |
| 7 | install | Download asset → verify SHA-256 → install via the detected method (binary: smoke-test staged file before atomic swap). | `CHECKSUM_MISSING`, `CHECKSUM_MISMATCH`, `DOWNLOAD_FAILED`, `PIP_INSTALL_FAILED`, `GIT_FETCH_FAILED`, `GIT_FAST_FORWARD_FAILED`, `SOURCE_BEHIND_RELEASE`, `STAGED_BINARY_FAILED` |
| 8 | verify | `UpgradeVerifierBot.verify(level)` against the installed CLI. Any required check failing → failure. | `VERIFICATION_FAILED` |
| 9 | rollback | Only for failures at install/verify, when a snapshot exists and rollback is enabled. Restore snapshot, then smoke-verify the restored version. | outcome `rollback-failed` (exit 6) |
| 10 | report | Write `last-run.json`, append `history.jsonl`, release the lock (always, via `finally`). | never fatal |
| 11 | announce | `UpgradeAnnouncerBot.announce()` — console, report, voice queue, optional GitHub issue (dedup). | — |

## Extending

- **New install method:** add detection in `UpgradeBot.detect_install`, branches in `preflight`,
  `snapshot`, `install`, `rollback`, and `UpgradeVerifierBot.command_for`; add tests mirroring
  `test_run_pip_upgrade_success` / `test_run_verification_failure_rolls_back`.
- **New verification check:** add to `UpgradeVerifierBot.verify` with an explicit `required`
  flag; document it in GUIDE-049 "What tested means" and the bot spec.
- **New failure code:** raise `UpgradeError(stage, CODE, message, hint)` — the hint is what the
  announcement tells the operator to do, so it must be an action, not a restatement.
