# Runbook: `hath0r rules`

> Canonical Governance Runbook · ID: `RB-RULE-ROLLOUT-001` · Issue: #528

## Commands

| Command | Effect |
|---|---|
| `hath0r rules list` | Canonical sections shipped with the CLI. |
| `hath0r rules status --rule <ID> [--root DIR]` | Per-remote coverage: `compliant`, `pending-pr`, `missing`, `no-agents-md`, `no-remote`. |
| `hath0r rules ensure-all --rule <ID>` | Preview only. |
| `... --apply [--keep-worktrees] [--work-dir DIR]` | Insert the section, bump the patch version, update the CHANGELOG, validate, and commit in a scratch worktree. |
| `... --publish` | `--apply`, plus an issue (`IssueManagerBot`), a push, and a PR to `development`. |

## Recovery

- **Worktrees left behind:** `git -C <repo> worktree remove --force <path>`.
- **Issue opened but push failed:** re-run with `--publish`. The repo is still `missing` because no PR names the rule. Close the orphan issue by hand.
