# Procedure: Roll Out a Canonical Rule (`hath0r rules`)

> Canonical Governance Procedure · ID: `PROC-RULE-ROLLOUT-001` · Issue: #528

## Steps

1. **Check coverage**
   ```bash
   hath0r rules status --rule CR-CLI-ENTRY-001
   ```
2. **Preview the rollout.** Nothing is written.
   ```bash
   hath0r rules ensure-all --rule CR-CLI-ENTRY-001
   ```
3. **Prepare commits in scratch worktrees**, then review the diffs.
   ```bash
   hath0r rules ensure-all --rule CR-CLI-ENTRY-001 --apply --keep-worktrees
   ```
4. **Publish.** This opens one issue and one PR per remote, with a `Version Impact: patch` line in each PR body.
   ```bash
   hath0r rules ensure-all --rule CR-CLI-ENTRY-001 --publish
   ```
5. **Follow CI** on each PR. A failure that also fails on `development` predates the rollout and is reported, not fixed, by the rollout.

For a rule not shipped in the CLI, add `--section-file path/to/section.md`. The file must contain a `## <RULE-ID>` heading.
