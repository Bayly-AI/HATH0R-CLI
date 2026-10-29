# Git Workflow & Environment Promotion — Runbook

| Task | Command |
|------|---------|
| Pipeline snapshot (pending/drift/versions/open PRs) | `hath0r promote status` |
| Validate a PR path before pushing | `hath0r pr check --head <branch> --base <base>` |
| Start work | `hath0r branch start <type> <issue> <slug>` |
| Update work branch | `hath0r branch sync [--rebase]` |
| Open work PR | `hath0r pr create [--semver minor] [--draft]` |
| PR checks | `hath0r pr status <n>` |
| Merge (policy strategy) | `hath0r pr merge <n> [--human-approved]` |
| Cut release | `hath0r promote release <x.y.z>` |
| Promote | `hath0r promote to testing|staging|production [--from release/x.y.z] [--gate]` |

Reading `promote status`:
- **Pending** — commits in the source stage not yet in the target (work to promote).
- **Drift** — commits in the target not in the source (usually merge commits from earlier promotions or a hotfix
  that needs back-merging into `development`).
