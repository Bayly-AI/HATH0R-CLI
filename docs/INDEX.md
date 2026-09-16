---
id: HATHOR-CANON-014
title: "HATH0R CLI Integration Documentation Index"
summary: "Reading order and source-of-truth map for using HATH0R-CLI with the HATHOR POC and Framework."
doc_type: CANON
diataxis: reference
audience: [developer, operator, architect, agent]
tags: [cli, poc, framework, index, control-tower]
version: 0.1.1
status: draft
created: 2026-09-16
updated: 2026-09-16
owner: "Raymond Bayly (BaylyAI)"
review:
  trust: unverified
  reviewed_by: null
  reviewed_at: null
  interval: 365d
  next_review: null
stale: false
supersedes: []
superseded_by: null
amended_by: []
parent: null
sources:
  - HATHOR-CANON-001
  - HATHOR-REQ-001
  - "../AGENTS.md"
  - "../src/hath0r_cli/cli.py"
---
# HATH0R CLI Integration Documentation

Product-local documentation for using the OpenSource HATH0R CLI as the
control-tower and runtime boundary for the React/TypeScript HATHOR POC.

## Status legend

| State | Meaning |
|-------|---------|
| **Implemented** | Verified in current HATH0R-CLI source or checked-in configuration |
| **Proposed** | Required product contract that still needs implementation and tests |
| **Framework design** | Canonical design intent that may not exist in HATH0R-CLI |
| **Unavailable** | Not exposed to the POC through a current versioned CLI command |
| **Out of scope** | Deliberately excluded from the initial read-only integration |

Documentation examples do not make a proposed command executable.

## Reading order

1. [Integration requirements](hathor-req-002-cli-poc-integration-requirements-20260916.md) — what the CLI/POC boundary must provide.
2. [Architecture](hathor-arch-004-cli-control-tower-integration-20260916.md) — responsibility, data flow, authority, and trust boundaries.
3. [Current command reference](hathor-guide-042-current-command-reference-20260916.md) — what operators and adapters can execute now.
4. [POC machine interface](hathor-ts-005-poc-machine-interface-20260916.md) — proposed structured JSON and exit contract.
5. [POC adapter integration](hathor-guide-043-poc-adapter-integration-20260916.md) — how to connect the current and future contracts safely.
6. [Development and testing](hathor-guide-044-development-testing-20260916.md) — target tests, fixtures, and quality gates.
7. [Security, governance, and delivery](hathor-guide-045-security-governance-delivery-20260916.md) — execution boundaries and promotion rules.
8. [Troubleshooting](hathor-guide-046-troubleshooting-20260916.md) — diagnose CLI, Tower, KB, catalog, and adapter failures.

## Documents

| ID | Mode | Status | Document |
|----|------|--------|----------|
| HATHOR-CANON-014 | reference | draft | This index |
| HATHOR-REQ-002 | reference | draft | [Integration requirements](hathor-req-002-cli-poc-integration-requirements-20260916.md) |
| HATHOR-ARCH-004 | explanation | draft | [Architecture](hathor-arch-004-cli-control-tower-integration-20260916.md) |
| HATHOR-TS-005 | reference | draft | [POC machine interface](hathor-ts-005-poc-machine-interface-20260916.md) |
| HATHOR-GUIDE-042 | reference | draft | [Current command reference](hathor-guide-042-current-command-reference-20260916.md) |
| HATHOR-GUIDE-043 | how-to | draft | [POC adapter integration](hathor-guide-043-poc-adapter-integration-20260916.md) |
| HATHOR-GUIDE-044 | how-to | draft | [Development and testing](hathor-guide-044-development-testing-20260916.md) |
| HATHOR-GUIDE-045 | how-to | draft | [Security, governance, and delivery](hathor-guide-045-security-governance-delivery-20260916.md) |
| HATHOR-GUIDE-046 | how-to | draft | [Troubleshooting](hathor-guide-046-troubleshooting-20260916.md) |

## Current capability boundary

| Capability | State |
|------------|-------|
| `hath0r --version` | Implemented |
| `hath0r doctor` | Implemented |
| `hath0r kb path` | Implemented |
| `hath0r kb products` | Implemented |
| `hath0r --output json --version` | Implemented (`hath0r.cli.response/1` + version data) |
| Versioned JSON output (all commands) | Partial — version done; doctor/kb payloads still landing |
| Schema discovery | Framework design |
| Knowledge search/write | Unavailable |
| Validation/orchestration/gates | Unavailable |
| Mutating and deployment actions | Out of scope |

The source file `../src/hath0r_cli/cli.py` is authoritative for this boundary.

## Product responsibility map

| Product | Responsibility |
|---------|----------------|
| HATH0R-CLI | OpenSource control tower, local operator CLI, KB/catalog mediation, future machine command contract |
| HATHOR Framework | Canonical OpenSource architecture, requirements, principles, and evolving interface design |
| HATHOR POC | React/TypeScript integration consumer, DMZ adapter, consumer fixtures, and UI evidence |

The POC must not copy CLI/Tower authority. HATH0R-CLI must not present
Framework designs as shipped commands. The Framework remains the canonical
documentation corpus while these pages apply it to this product.

## Source-of-truth boundaries

| Concern | Authority |
|---------|-----------|
| Current command behavior | `../src/hath0r_cli/cli.py` and released package |
| Package metadata/version | `../pyproject.toml` and `../src/hath0r_cli/__init__.py` |
| OpenSource control-tower orientation | `../cfg/` |
| Repository governance | `../AGENTS.md` and group policy |
| POC consumer contract | `../../hath0r-poc/docs/` |
| Framework architecture/design | `../../hath0r/docs/` |
| Canonical local knowledge | OpenSource group `.hath0r/knowledgebase` hub |

When product prose conflicts with current CLI source, source determines what
can execute today. When source or product prose conflicts with repository or
group governance, governance wins.

## Documentation maintenance

- Follow `hathor-doc@1` from HATHOR-CANON-001.
- Keep IDs stable and globally unique across the OpenSource documentation
  namespace.
- Bump `version` and `updated` for content changes.
- Keep `review.trust: unverified` until a named reviewer verifies a page
  end-to-end.
- Update this index when adding, replacing, or retiring documents.
- Generate `index.json` and `llms.txt` from front matter.
- Update the POC capability map when a CLI contract changes.
- Do not change a proposed capability to implemented without source and test
  evidence.

## Scope note

These documents define product requirements and usage. They do not implement
the TypeScript POC, structured output, Framework bots, Tower REST services, or
deployment controls.
