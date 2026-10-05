# Playbook: Upgrade Failure Triage

> Document Type: **Playbook** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `upgrade-factory`
> Updated: 2026-10-05

Start with: `hath0r upgrade status -o json` (or the GitHub issue the bot opened). The `failure.code`
selects the play below. `outcome` tells you the state of the machine:

- `rolled-back` → the previous version is installed **and passed re-verification**. No urgency for the operator; fix the release.
- `rollback-failed` → **critical**. The install may be broken. Go to §5 first.
- `failed` with no rollback → preflight/check failure; nothing was changed.

## 1. Release / feed problems

| Code | Meaning | Play |
|------|---------|------|
| `RELEASE_FEED_UNAVAILABLE` | GitHub API unreachable or rate-limited, `gh` fallback failed | `gh auth status`; set `GITHUB_TOKEN`; retry. Persisting → check network/proxy. |
| `ASSET_MISSING` | Release lacks a wheel or a binary for this platform | Check the release's assets; re-run `release.yml`. Binary users on an unbuilt platform: switch to pipx. |
| `CHECKSUM_MISSING` | No digest and no `.sha256` sidecar | Release pipeline defect — re-publish with sidecars. **Never** bypass. |
| `CHECKSUM_MISMATCH` | Downloaded bytes ≠ published digest | Treat as possible tampering. Re-download once; if it repeats, stop and raise a security issue. |

## 2. Local-state problems (nothing changed)

| Code | Play |
|------|------|
| `SOURCE_TREE_DIRTY` | Commit or stash, re-run. The bot will never discard local changes. |
| `SOURCE_BRANCH_NOT_CANONICAL` | `git switch development`, re-run — or upgrade your feature branch by hand. |
| `GIT_FAST_FORWARD_FAILED` | Local `development` diverged from origin. Reconcile (`git log origin/development..`), then re-run. Rollback already restored the snapshot SHA. |
| `SOURCE_BEHIND_RELEASE` | `origin/development` hasn't received the release merge-back yet. Wait, or track `master`. |
| `UPGRADE_IN_PROGRESS` | Another run holds the lock. Wait; if `ps -p <pid>` shows nothing, delete `~/.hath0r/upgrade/upgrade.lock`. |
| `PIPX_MISSING` / `BINARY_NOT_WRITABLE` | Fix PATH / permissions, or reinstall with `scripts/install_hath0r.py`. |

## 3. Install failures (rolled back)

`PIP_INSTALL_FAILED` — read the pip error in the report (`failure.message`). Typical causes:
dependency conflict in a shared interpreter (prefer pipx), Python version below `requires-python`,
or the wheel's metadata is wrong (release defect → fix and re-release).

## 4. Verification failures (rolled back)

Open `last_run.verification.checks` and act on the failing one:

| Check | Likely cause | Fix |
|-------|--------------|-----|
| `version` | Wrong artifact installed, stale editable install, PATH points at another `hath0r` | `which -a hath0r`; reinstall. For releases: VERSION/pyproject drift (`hath0r release validate`). |
| `command-imports` | A command module raises on import (new optional dep, syntax error) — the detail names the command and exception | Fix the import (guard optional deps with lazy imports) and release a patch. |
| `doctor` | New version reports more failed checks than before the upgrade | Run `hath0r doctor` on the new version (`pipx run`/venv) to see which check regressed. |
| `unit-tests` | `--tests full` on a source checkout found a failing test | Reproduce with `pytest -q -x tests/unit`; fix on a work branch. |

## 5. `rollback-failed` (critical)

1. `hath0r upgrade status -o json` → `last_run.rollback.error` and `last_run.snapshot`.
2. Restore by method:
   - source: `git -C <repo_root> reset --hard <snapshot.head_sha> && python3 -m pip install -e <repo_root>`
   - pip/pipx: `python3 scripts/install_hath0r.py --version <snapshot.version>`
   - binary: `cp <snapshot.backup_path> <snapshot.binary_path>`
3. `hath0r upgrade verify` must pass before closing the incident.
4. Comment the root cause on the bot's GitHub issue.

## 6. Issue hygiene

The bot comments on an existing open issue with the identical title instead of opening a new one.
Close the issue when the fixed release has been verified by a successful bot run
(`outcome: upgraded` in `hath0r upgrade status`).
