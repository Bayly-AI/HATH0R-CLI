# Checklist: Upgrade Bot

> Document Type: **Checklist** (`cr-workflow-doc-001`) · Factory: `upgrade-factory` · Updated: 2026-10-05

## Before enabling on a machine

- [ ] `hath0r upgrade check` succeeds and shows the expected install method
- [ ] `hath0r upgrade verify` passes on the current version (establishes a healthy baseline)
- [ ] `gh auth status` is logged in (only needed for `--file-issue`)
- [ ] Source checkouts: on `development`/`master`, clean tree
- [ ] `hath0r upgrade run --dry-run` shows the intended plan

## Before shipping a CLI release (release owner)

- [ ] Release has a `hath0r_cli-<ver>-py3-none-any.whl` asset
- [ ] Every installable asset has a GitHub digest or a `.sha256` sidecar
- [ ] Binary matrix covers the platforms of enrolled machines
- [ ] `hath0r upgrade run --version <ver> --force --tests full` passes on a source checkout

## Changes to the Upgrade Bot itself

- [ ] `pytest -q tests/unit/test_upgrade_bot.py` passes
- [ ] `hath0r factory validate` passes for `upgrade-factory`
- [ ] New failure codes have an actionable `hint` and a row in the playbook
- [ ] New checks documented in GUIDE-049 and the bot spec
- [ ] Live verification on a real install: `hath0r upgrade check`, `run --dry-run`, `verify`

## After a failed run

- [ ] `hath0r upgrade status` outcome is `rolled-back` (not `rollback-failed`)
- [ ] `hath0r upgrade verify` passes on the restored version
- [ ] Issue opened/updated with the failure code and fix hint
