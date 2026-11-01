# Playbook: Autonomous End-of-Task Daemon Diagnostics & Troubleshooting

> Document Type: **Playbook** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #118 · SemVer: `minor`

## 1. Scenario: Polling Timeout Reached

If PR checks take longer than the timeout period (`--timeout`, default 600 seconds):
1. Check GitHub Actions UI or `gh run list --branch <branch>`.
2. Determine if runner queue is congested or a job is stuck.
3. Re-run `hath0r task finish --daemon --timeout 1200` to resume watching.

## 2. Scenario: CI Failure Detected

If CI check reports `FAILURE`:
1. Inspect failure logs:
   ```bash
   gh run view <run_id> --log-failed
   ```
2. If failure is a genuine code defect (e.g. `mypy`, `ruff`, test assertion failure):
   - Daemon halts execution and returns error status code.
   - Developer/agent fixes the code locally, pushes the fix, and restarts the daemon.
3. If failure is due to missing org secret (`SONAR_TOKEN`):
   - The daemon notes the failure as an infrastructure bypass condition per `cr-branch-gov-001` (admin bypass allowed).

## 3. Scenario: Merge Conflict or Unmergeable PR

If GitHub reports `mergeable: CONFLICTING`:
1. The daemon aborts merge step with `MERGE_CONFLICT`.
2. Developer checks out work branch and rebases onto `origin/development`:
   ```bash
   git fetch origin development
   git rebase origin/development
   git push --force-with-lease origin <branch>
   ```
3. Restart `hath0r task finish --daemon`.
