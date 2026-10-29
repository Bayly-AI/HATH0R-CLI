# Git Workflow & Environment Promotion — Strategy

**Policy:** CR-BAI-001 · cr-branch-gov-001 · **Bot:** `GitWorkflowBot` (`src/hath0r_cli/bots/git_workflow_bot.py`)

## Goal
Give operators and agents one CLI surface for the whole branch → PR → promotion lifecycle that returns the
**same verdict locally as CI** (`.github/workflows/enforce-promotion-path.yml`), before anything is pushed.

## Design
- **Single policy source in the CLI.** `GitWorkflowBot.check_path()` uses the same work/release regexes and
  per-base rules as the CI job. `pr check`, `pr create`, `pr merge` and `promote to` all call it.
- **Chain:** `development → testing → staging → master`; environments `testing`, `staging`, `production`.
- **Human gates:** `staging` and `master`. `pr merge` refuses them without `--human-approved`; the CLI never
  uses `--admin` bypass.
- **Merge strategy is policy, not preference.** Work PRs squash into `development` (branch deleted).
  Promotion PRs use a merge commit so the CI push gate (`origin/<prev>` is an ancestor of the target) holds.
- **Non-destructive release cutting.** `promote release` pushes `origin/development:refs/heads/release/x.y.z`
  without touching the operator's checkout.
- **Safe sync.** `branch sync` refuses dirty trees and canonical branches and aborts on conflict, reporting
  the conflicted files instead of leaving a half-merged tree.
- **Idempotent promotion.** `promote to` reuses an open PR for the same head/base and is a no-op when the
  target already contains the source.

## Boundaries
- GitHub access is via `gh`; git via the local checkout and `origin`.
- Environment approval itself lives in GitHub Environments (`promotion-environment-gates.yml`, dispatched with `--gate`).
