# Agent Session Start Checklist

> Canonical checklist for AI agents and operators beginning any task across the OpenSource Project suite (`HATH0R-CLI`, `HATH0R-Agentic-Framework`, `HATH0R-Agentic-POC`).

## Pre-Work Verification

1. **Verify Control Tower & Tools**:
   - Ensure `hath0r` CLI is installed and responsive: `python3 -m hath0r_cli.cli --version`.
   - Run `hath0r doctor --factories` to ensure configuration, catalog, and registered factories are 100% green.

2. **CLI-First Orientation**:
   - For all operations involving connections, MCPs, workflows, factories, Docker stacks, or KB lookups, use `hath0r` commands directly (`hath0r factory ...`, `hath0r task ...`, `hath0r docker ...`, `hath0r kb ...`).
   - Do **not** invent ad-hoc shell scripts or temporary tools when a CLI command or factory exists.

3. **Missing Capability Gate**:
   - If a requested connection, MCP registration, workflow, or factory does **not** exist:
     - **Do not silently improvise or hack workarounds.**
     - Offer to pivot the task: first build/register the missing connection/MCP/workflow/factory, using the user's original request as the automated acceptance test of the new capability.

4. **Issue-First & Branch Governance (`cr-branch-gov-001`)**:
   - Every task must correspond to an open GitHub issue.
   - Run `hath0r task start --issue <number> --slug <short-slug>` to verify the issue and checkout the canonical work branch `feature/<issue>-<slug>` from `development`.
   - Never commit directly to protected canonical branches (`development`, `testing`, `staging`, `master`).

5. **Procedure / Strategy / Playbook / Runbook Gate (`CR-HATH0R-INIT-001`)**:
   - Before scaffolding or writing code for new features, verify or create the corresponding procedure/playbook/runbook under `docs/`.
   - Layout scaffolding without an operational runbook is incomplete.

6. **Hidden Root Compliance (`cr-hath0r-root-001`)**:
   - Store all project metadata, KB pointers, and local caches under `.hath0r/` only.
   - Never create `.ai/`, `.aegis/`, or `.infraOS/`.

7. **End-of-Task Lifecycle (`#64`)**:
   - When implementation and local tests/lint pass, execute the canonical end-of-task automation:
     `hath0r task finish --semver [patch|minor|major]`
   - Verify PR checks, merge via admin squash bypass, prune branches, pull `development`, and announce completion.
