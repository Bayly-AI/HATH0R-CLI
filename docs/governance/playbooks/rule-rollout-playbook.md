# Playbook: Canonical Rule Rollout

> Canonical Governance Playbook · ID: `PB-RULE-ROLLOUT-001` · Issue: #528

| Situation | Play |
|---|---|
| New org-wide `CR-*` rule adopted | Add it to `CANONICAL_RULE_SECTIONS`, release the CLI, then follow `PROC-RULE-ROLLOUT-001`. |
| One-off rule for a subset of repos | `--section-file` plus `--root` pointing at that subset. |
| Repo shows `pending-pr` | An open PR already carries the rule. Review and merge it instead of opening another. |
| Repo shows `no-agents-md` | Run `hath0r init` in that repo first. |
| Pre-commit hook rejects the commit | The repo is reported as `error` with the hook output. Fix the section text for that repo by hand; never bypass hooks. |
| CI fails on the PR | Compare with the latest `development` run. If `development` fails the same way, report it as pre-existing. |
