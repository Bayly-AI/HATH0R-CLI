# Strategy: Autonomous End-of-Task Daemon Bot

> Document Type: **Strategy** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #118 · SemVer: `minor`  
> Canonical Control Tower Specification

## 1. Context & Motivation

In the Hath0r development model, completing a development assignment involves a canonical multi-step lifecycle:
1. Verify branch state and ensure all changes are committed and pushed.
2. Create or verify the Pull Request targeting `development`.
3. Generate PR release notes and contextual metadata.
4. Continuous observation and polling of PR status checks (CI, SonarCloud, Version Policy, Promotion Path, PR Workflow Guard).
5. Merge PR via squash + admin bypass + automatic branch deletion upon passing required gates.
6. Local and remote work branch cleanup and synchronization back to `development`.
7. Knowledge sharing to local project MCP / knowledgebase.
8. Task completion announcement and telemetry spooling.

Previously, running `hath0r task finish` performed a single pass: if PR checks were still pending in CI, step 4 (`monitor-checks`) could return incomplete or fail on transient delays. Developers or agents were forced to manually wait, poll, diagnose failures, run merge commands, and prune branches.

Issue #118 automates this entire lifecycle as an autonomous event-driven daemon bot (`EndOfTaskDaemonBot` and `hath0r task finish --daemon` / `--watch`).

## 2. Goals & Non-Goals

### Goals
- Implement `EndOfTaskDaemonBot` with a robust finite state machine (FSM):
  - `INIT` $\rightarrow$ `PR_CHECK` $\rightarrow$ `POLL_CHECKS` $\rightarrow$ `EVALUATE_GATES` $\rightarrow$ `MERGE` $\rightarrow$ `CLEANUP` $\rightarrow$ `KNOWLEDGE_SHARE` $\rightarrow$ `ANNOUNCE` $\rightarrow$ `COMPLETE`.
- Support `--daemon` (continuous background monitoring loop with configurable interval and timeout) and `--watch` options in `hath0r task finish`.
- Provide automated CI check diagnosis:
  - Separate hard failures (code error, test failure, lint failure) from known bypassable infrastructure issues (e.g. missing `SONAR_TOKEN` when org secret onboarding is pending).
  - Distinguish between pending checks and completed checks.
- Safely merge PRs via admin squash when required checks pass.
- Reap local and remote feature branches while preserving canonical branches (`development`, `testing`, `staging`, `master`).
- Sync local git workspace with updated `development`.
- Record and spool structured telemetry events to `.hath0r/spool/`.

### Non-Goals
- Bypassing human approval gates on staging or master promotions. Work PRs only target `development`.
- Silently ignoring real code/lint/test failures. If test suites or lint rules fail, the daemon halts and diagnoses the root cause.
