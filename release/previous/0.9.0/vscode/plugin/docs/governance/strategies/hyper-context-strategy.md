# Hyper Context Strategy

**Goal:** Establish a Hyper Context Architecture to manage agentic LLM context windows and localize rules down to specific feature directories.

## Context Chain
- **Playbook:** [Hyper Context Playbook](../playbooks/hyper-context-playbook.md)
- **Procedure:** [Hyper Context Procedure](../procedures/hyper-context-procedure.md)
- **Runbook:** [Hyper Context Runbook](../runbooks/hyper-context-runbook.md)
- **Checklist:** [Hyper Context Checklist](../checklists/hyper-context-checklist.md)
- **Factory:** `cfg/factories/hyper-context-factory.yaml`

## Strategy Summary
To prevent context poisoning and token overflow, we do not place all agentic rules in a single root file. Instead, the root `AGENTS.md` acts as an index/router. When an agent needs to work on a specific feature, it reads the root rules, identifies the target directory, and descends. Each subdirectory contains its own specific `AGENTS.md`, `rules.md`, and `canonical.md` containing only the localized rules for that feature.
