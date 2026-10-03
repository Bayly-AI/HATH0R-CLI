---
title: "Ticket: Refactor Agents Files to Utilize AgentGraph Substrate"
repository: "OpenSource/hathor-cli"
github_issue: "https://github.com/Bayly-AI/HATH0R-CLI/issues/295"
created: "2026-10-03"
status: "closed"
closed_at: "2026-10-03"
validation_result: "PASSED (32 nodes, 11 edges)"
---

# Refactor Agent Files to Utilize Hath0r AgentGraph Substrate

## Repository Context
- **Repository**: `OpenSource/hathor-cli`
- **System Archetype / Role**: Operator CLI, FastMCP & Command Surface
- **Technology Stack**: Python 3.11 / Click / FastMCP / Hatchling
- **Primary Subsystems**: `src/hath0r_cli/commands`, `src/hath0r_cli/bots`, `packaging/fileset`
- **Current Agent Files**: `AGENTS.md`, `packaging/fileset/templates/AGENTS.md`, `tests/AGENTS.md`, `docs/AGENTS.md`, `cfg/AGENTS.md`, `cfg/group/AGENTS.md` (+2 more) (8 total)
- **Current AgentGraph Snapshot**: Initialized (30 nodes, 5 edges)

---

## Architectural Purpose

Under **CR-BAI-001** and the **Hath0r Zero-Prompt-Tax Governance** model, storing static policies, rules, and tool authorizations as monolithic Markdown documents in `AGENTS.md` wastes 40%–60% of LLM context windows and introduces probabilistic security bypasses. 

This work refactors this repository's agent configuration into the deterministic **AgentGraph Quad-Graph Substrate** (KnowledgeGraph, ContextGraph, MemoryGraph, and RuleDAG).

---

## Step-by-Step Implementation Plan

### Step 1: Inventory & De-duplicate Agent Prompts
- Audit all existing `AGENTS.md` files (root and subsystems).
- Strip out static prompt-stuffing, duplicate headers, and obsolete instructions.
- Ensure only essential repository identity, UPL layout, and operational pointers remain.

### Step 2: Initialize / Synchronize AgentGraph Substrate
- Run `hath0r agentgraph sync` (or `./bin/hath0r-bootstrap.sh`) to extract all local subsystem rules into `.hath0r/agentgraph/snapshot.json`.
- Verify contracts under `contracts/*.schema.json` are registered in the Knowledge plane.
- Classify repository rules into mathematical precedence tiers:
  - **Tier 4 (Org Invariants)**: `CR-*` policies (e.g. `CR-CLI-ENTRY-001`, `CR-BAI-001`).
  - **Tier 3 (Repository Standards)**: Product-level standards and conventions.
  - **Tier 2 (Subsystem Rules)**: Scoped rules in `src/hath0r_cli/commands`, `src/hath0r_cli/bots`, `packaging/fileset`.
  - **Tier 1 (Role Guidelines)**: Role-specific instructions.

### Step 3: Define Deterministic Agent Roles (RBAC)
- Define explicit agent roles in the Rule plane:
  - `role:developer`: Permitted (`read_file`, `write_file`, `run_command`, `search_code`), Forbidden (`direct_push_master`).
  - `role:reader`: Permitted (`read_file`, `search_code`), Forbidden (`run_command`, `write_file`, `git_push`).
  - Domain-specific roles tailored to `Operator CLI, FastMCP & Command Surface`.
- Attach `RESTRICTED_BY` and `GOVERNS` edges between rules and roles.

### Step 4: Refactor AGENTS.md for Dynamic Substrate Resolution
- Update root `AGENTS.md` and subsystem `AGENTS.md` files with the canonical AgentGraph block:
  ```markdown
  ## AgentGraph Substrate
  This repository is governed by the Hath0r AgentGraph substrate.
  Dynamic rule retrieval, role RBAC, and policy graphs are stored under `.hath0r/agentgraph/`.
  - Query status: `hath0r agentgraph status`
  - Query rules: `hath0r agentgraph query "<topic>"`
  - Route role: `hath0r agentgraph route --role <role>`
  - Validate rules: `hath0r agentgraph validate`
  ```

### Step 5: Integrate Graph Validation into Quality Gates & CI
- Add `hath0r agentgraph validate` to repository build/test scripts and GitHub Actions workflows.
- Verify zero cyclic dependencies, zero contradictions, and zero orphan edges during every pull request.

---

## Acceptance Criteria
- [ ] `.hath0r/agentgraph/snapshot.json` exists, is committed, and is up-to-date with all local rules.
- [ ] `hath0r agentgraph validate` passes with 0 errors and 0 contradictions.
- [ ] All `AGENTS.md` files reference dynamic AgentGraph commands rather than static prompt-stuffing.
- [ ] Subsystem roles and permitted/forbidden tool boundaries are mathematically deterministic.


## Tracking & References
- **GitHub Issue**: [https://github.com/Bayly-AI/HATH0R-CLI/issues/295](https://github.com/Bayly-AI/HATH0R-CLI/issues/295)
- **Framework Specification**: `HATHOR-GUIDE-048` / `BC-ARTICLE-009`
- **CLI Commands**: `hath0r agentgraph status`, `hath0r agentgraph sync`, `hath0r agentgraph validate`
