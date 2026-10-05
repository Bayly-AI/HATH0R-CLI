# Strategy: Automated CLI Upgrade & Install Verification

> Document Type: **Strategy** (`cr-workflow-doc-001`) · Product: **HATH0R-CLI** · Factory: `upgrade-factory`
> Status: **Active** · Updated: 2026-10-05

## 1. Problem

The CLI ships frequently (v0.6.0 → v0.9.0 in two days). Operators upgrade by hand, inconsistently,
and nothing proves a new version works on *their* machine before they depend on it. A broken
upgrade is discovered mid-task, and the previous working version is gone.

## 2. Goals

1. **Hands-off upgrades** across every supported install method (source, pip, pipx, binary).
2. **Proof, not hope**: every install is followed by a test suite run against the installed CLI.
3. **Safe failure**: an upgrade that fails tests is rolled back and the rollback is re-verified.
4. **Actionable announcements**: a failure produces a message that says *what broke and how to
   fix it*, and (unattended) a de-duplicated GitHub issue that the team can work.
5. **Supply-chain hygiene**: only checksum-verified release artifacts are installed (GUIDE-047 trust rules).

## 3. Non-goals

- Publishing releases (owned by `release-bot` / `release.yml`).
- Upgrading member repositories' configuration (owned by `update-cli-factory` orientation step).
- Managing Python itself or system packages.
- Auto-merging or rewriting diverged source branches — the bot refuses and announces instead.

## 4. Design decisions

| Decision | Rationale |
|----------|-----------|
| Three bots (orchestrate / verify / announce) | Matches factory step model; the announcer runs even when the upgrade step fails (`on_failure: continue`). |
| Stdlib-only bot module | The upgrader must work when the CLI's optional deps are what broke. |
| Verify in a fresh subprocess | The running process still holds the old code; only a new interpreter proves the new install. |
| Doctor compared to a pre-upgrade baseline | Environments are often partially degraded (e.g. an MCP server down); block regressions, not pre-existing noise. |
| Command import scan | `Hath0rLazyGroup` swallows import errors and hides the command — a silent breakage only an explicit scan catches. |
| Binary staged + tested before swap | The live binary is never replaced by something that fails smoke tests. |
| Source installs: fast-forward only on `development`/`master`, clean tree | Never destroy local work; rollback via `git reset --hard <snapshot>` is safe only because the tree was verified clean. |
| State in `~/.hath0r/upgrade/` | Independent of cwd (MCP servers run with cwd `/`); follows `cr-hath0r-root-001` (`.hath0r/` only). |
| Issue de-duplication by exact title | Nightly runs must not open a new issue every night for the same defect; they comment instead. |

## 5. Integration boundaries

- **Inputs:** GitHub Releases API (`GITHUB_TOKEN`/`GH_TOKEN` optional; `gh api` fallback), release assets + digests.
- **Outputs:** envelope (`upgrade.*` commands), `last-run.json`, `history.jsonl`, voice spool, GitHub issues via `gh`.
- **Consumers:** operators, `factory run upgrade-factory`, launchd/cron schedule, `scripts/install_hath0r.py`.

## 6. Success measures

- Zero manual upgrades needed between releases on enrolled machines.
- Every failed upgrade leaves a working previous version (rollback re-verified) and an issue or report.
- Mean time from release to verified install on enrolled machines < 24 h (nightly schedule).
