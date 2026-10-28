# Strategy: Canonical Rule Rollout (`hath0r rules`)

> Canonical Governance Strategy · ID: `STRAT-RULE-ROLLOUT-001`
> Issue: #528 · Rule Compliance: `CR-CLI-FEATURE-STANDARD-001`, `CR-CLI-ENTRY-001`, `CR-SEMVER-BUMP-001`

---

## 1. Problem

Canonical `CR-*` rules live as sections in each repository's root `AGENTS.md`. When a new rule is adopted, it has to reach every repository, and each change needs its own issue, `chore/<issue>-<slug>` branch, SemVer patch bump, `CHANGELOG.md` entry, and pull request. Before #528 this was scripted by hand per rollout. On 2026-10-28, `CR-CLI-ENTRY-001` was present in only 20 of 145 `AGENTS.md` files, and the control tower itself was missing it.

## 2. Approach

`RuleRolloutBot` makes the rollout one CLI capability (`CR-CLI-ENTRY-001`: the CLI comes first):

- **One source for the section text.** Canonical sections ship inside HATH0R-CLI (`CANONICAL_RULE_SECTIONS`). Any other section can be passed with `--section-file`.
- **One PR per unique remote.** Extra clones of the same remote are grouped, and only the first is used.
- **Upstream is the truth.** A repository counts as compliant when `origin/development:AGENTS.md` contains the rule ID. A repository with an open PR whose title names the rule is reported as `pending-pr` and skipped.
- **Dirty checkouts stay untouched.** All edits happen in scratch worktrees cut from `origin/development`.
- **Default preview.** Without `--apply`, `ensure-all` only reports the plan. `--apply` commits in worktrees. `--publish` also opens issues and PRs.

## 3. Out of scope

Merging PRs, and editing `CLAUDE.md`-only repositories. A repository without a root `AGENTS.md` is reported as `no-agents-md`.
