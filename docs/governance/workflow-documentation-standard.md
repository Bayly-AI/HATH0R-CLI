# Workflow documentation standard

> Control tower: `Bayly-AI/HATH0R-CLI` · Issue track: #62  
> Every workflow/factory MUST have the full documentation set below.

## Required document types

| Type | Purpose | Typical path |
|------|---------|--------------|
| **Strategy** | Why / goals / non-goals | `docs/governance/strategies/<id>-strategy.md` |
| **Procedure** | Ordered normative steps | `docs/governance/procedures/<id>-procedure.md` |
| **Playbook** | Decision-rich how-to | `docs/governance/playbooks/<id>-playbook.md` |
| **Runbook** | Ops incident / day-2 | `docs/governance/runbooks/<id>-runbook.md` |
| **Checklist** | Pre/post gates | `docs/governance/checklists/<id>.md` |
| **Test-doc** | How to verify | `tests/` docstrings + `docs/.../test-doc` or unit module header |

## Scope

Applies to:

- Declarative factories under `cfg/factories/*.yaml`
- Docker workflows under `cfg/docker/workflows/*.json`
- Scheduled workflows (factory schedule)
- Any new automation introduced via CLI or MCP

## Inventory (control tower)

| Workflow / factory | Strategy | Procedure | Playbook | Runbook | Checklist | Test-doc |
|--------------------|----------|-----------|----------|---------|-----------|----------|
| start-of-task-factory | strategies/task-lifecycle-strategy.md | procedures/task-start-procedure.md | playbooks/task-lifecycle-playbook.md | runbooks/task-lifecycle-runbook.md | checklists/task-lifecycle.md | tests/unit/test_bots.py |
| end-of-task-factory | strategies/task-lifecycle-strategy.md | procedures/task-finish-procedure.md | playbooks/task-lifecycle-playbook.md | runbooks/task-lifecycle-runbook.md | checklists/task-lifecycle.md | tests/unit/test_bots.py |
| pr-and-branch-lifecycle-factory | strategies/pr-lifecycle-strategy.md | (pr-workflow.md) | playbooks/pr-workflow-playbook.md | runbooks/pr-lifecycle-runbook.md | checklists/pr-pre-merge-development.md | tests/unit/test_bots.py |
| docker-factory | strategies/docker-group-strategy.md | procedures/docker-group-procedure.md | playbooks/docker-group-playbook.md | runbooks/docker-group-runbook.md | checklists/docker-group.md | tests/unit/test_bots.py |
| quality-release-factory | strategies/quality-release-strategy.md | procedures/quality-release-procedure.md | (quality-bots.md) | runbooks/quality-release-runbook.md | checklists/quality-bots.md | tests/unit/test_quality_bots.py |
| mcp-doc-publish | strategies/mcp-doc-publish-strategy.md | procedures (via playbook) | playbooks/mcp-doc-publish-playbook.md | runbooks/mcp-doc-publish-runbook.md | checklists/mcp-doc-publish-checklist.md | docs/governance/mcp-doc-publish.md |

Gap fill: any row missing a file MUST add it before claiming the workflow “production ready”.

## Publish path

Durable docs may be shared to project MCP via `hath0r docs share` / `cfg/mcp-doc-publish.json` (never secrets).

## Enforcement

- Agents: session-start checklist gate  
- Humans: PR template “docs impact”  
- Optional CI: future factory validate hook checking doc paths in factory metadata `documentation:` block  
