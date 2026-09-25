# Procedure: Autonomous End-of-Task Daemon Bot Execution

> Document Type: **Procedure** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #118 · SemVer: `minor`

## 1. Scope

Normative procedure for running, supervising, and verifying the `EndOfTaskDaemonBot` in CLI task execution.

## 2. Procedure Steps

### Step 1: Pre-Execution Verification
1. Verify working directory is clean or commits are pushed on the active work branch.
2. Confirm active branch matches `feature|bugfix|hotfix|chore/<issue>-<slug>`.
3. Confirm test pyramid passes locally (`pytest` or `npm run check`).

### Step 2: Running the Daemon Bot
Invoke `hath0r task finish` with `--daemon` or `--watch`:
```bash
hath0r task finish --daemon --semver minor
```
Optional arguments:
- `--poll-interval <seconds>` (default: 10s)
- `--timeout <seconds>` (default: 600s / 10m)
- `--pr <pr_number>` (optional explicit PR number)
- `--dry-run` (simulates entire state machine without mutating git or GitHub)

### Step 3: Lifecycle Phases Managed by the Daemon
1. **PR Verification**: Locates or creates PR for the branch against base `development`.
2. **Checks Polling**: Continuously polls GitHub status checks until terminal state (all passed, or hard failure).
3. **Quality Gate Evaluation**:
   - Required checks: `CI / test-and-lint`, `PR Workflow Guard`, `Version Policy Guard`, `Enforce Promotion Path`.
   - Admin bypass handled cleanly if non-code gates (e.g. missing `SONAR_TOKEN`) fail while code checks pass.
4. **Merge Execution**: Dispatches `gh pr merge --squash --admin --delete-branch`.
5. **Branch Reaping**: Deletes local work branch and switches local checkout to `development`.
6. **Workspace Sync**: Runs `git checkout development && git pull origin development`.
7. **Knowledge Share**: Dispatches `DocumentationBot.share_knowledge()` to update local MCP/KB.
8. **Announcement & Telemetry**: Emits task completion event and spools telemetry to `.hath0r/spool/`.
