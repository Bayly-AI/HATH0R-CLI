---
id: HATHOR-REQ-002
title: "HATH0R CLI and POC Integration Requirements"
summary: "Requirements for the OpenSource HATH0R CLI to serve the React/TypeScript POC without bypassing Framework control boundaries."
doc_type: REQ
diataxis: reference
audience: [developer, operator, architect, agent]
tags: [cli, poc, framework, requirements, control-tower]
version: 0.1.1
status: draft
created: 2026-09-16
updated: 2026-09-16
owner: "Raymond Bayly (BaylyAI)"
review:
  trust: unverified
  reviewed_by: null
  reviewed_at: null
  interval: 180d
  next_review: null
stale: false
supersedes: []
superseded_by: null
amended_by: []
parent: HATHOR-CANON-014
sources:
  - HATHOR-CANON-011
  - HATHOR-ADR-003
  - HATHOR-ADR-004
  - HATHOR-TS-004
  - HATHOR-REQ-001
  - "../src/hath0r_cli/cli.py"
  - "../cfg/control-tower.yaml"
  - "../cfg/knowledge-tower.yaml"
---
# HATH0R CLI and POC Integration Requirements

## 1. Purpose

Define what HATH0R-CLI must provide when it is used by the React/TypeScript
HATHOR Integration Console POC and how that product relationship remains
consistent with the HATHOR Framework.

This document covers both:

- the source-verified CLI v0.1 baseline; and
- proposed requirements for a stable machine interface.

Proposed requirements are not evidence that their flags, schemas, or commands
are implemented.

## 2. Product responsibilities

| Product | Owns | Must not become |
|---------|------|-----------------|
| HATH0R-CLI | OpenSource control-tower configuration, operator entry point, KB orientation, and product catalog mediation | Browser backend, copied Framework runtime, or second knowledge store |
| HATHOR Framework | Canonical architecture, requirements, principles, and future interface design | A source of claims about code that has not shipped |
| HATHOR POC | React/TypeScript integration client, safe adapter, fixtures, and consumer evidence | Shell, policy authority, deployment authority, or direct KB client |

The CLI is the runtime integration boundary for the POC. Framework documents
shape future contracts, but `src/hath0r_cli/cli.py` determines what executes
today.

## 3. Current capability baseline

| Capability | Current state | Evidence | POC treatment |
|------------|---------------|----------|---------------|
| Version | Implemented | `hath0r --version` | Read-only allowlisted probe |
| Version structured JSON | Implemented | `hath0r --output json --version` → `hath0r.cli.response/1` | Prefer JSON probe when available |
| Suite diagnostics | Implemented | `hath0r doctor` | Exit status is authoritative |
| Doctor structured JSON | Implemented | `hath0r --output json doctor` → checks/counts; exit `6` when degraded | Prefer JSON probe when available |
| Canonical KB path | Implemented | `hath0r kb path` | Adapter returns logical availability by default |
| Product catalog | Implemented | `hath0r kb products` | Bounded YAML/text until JSON ships |
| JSON output flag | Implemented | `--output, -o json\|text\|auto` | Request JSON explicitly |
| JSON payloads (kb path/products) | Partial | Envelope ships; command `data` still landing | Keep text path until full payloads |
| Schema discovery | Not implemented | No schema command in CLI source | Framework design |
| Knowledge search/write | Not implemented | No command in CLI source | Unavailable to POC |
| Validation/orchestration/gates | Not implemented | Framework design only | Unavailable to POC |
| Mutating operations | Not implemented and out of initial POC scope | No current command | Refused |

## 4. Functional requirements

### HT-CLI-001 — One mediated POC ingress

The POC must reach HATHOR capabilities through HATH0R-CLI. It must not read the
Tower configuration, canonical KB, or product catalog directly.

**Acceptance:** every HATHOR-backed POC operation maps to a documented,
server-owned operation key and fixed CLI argv.

### HT-CLI-002 — Truthful capability discovery

The integration contract must distinguish `implemented`, `planned`, and
`unavailable` capabilities.

**Acceptance:** an absent CLI command or output mode cannot be advertised as
implemented merely because the Framework describes a target surface.

### HT-CLI-003 — Stable structured output

The CLI must add a versioned JSON output mode for machine consumers. Human
rendering and machine data must be generated from the same underlying result,
not independently inferred.

**Acceptance:** each POC-consumed command has a schema-versioned success and
error envelope, documented in HATHOR-TS-005.

### HT-CLI-004 — Explicit output selection

The future machine contract must use the Framework-aligned global output flag
`--output, -o json|text|auto`. The POC adapter must request JSON explicitly
rather than rely on terminal detection.

**Acceptance:** consumer fixtures invoke `-o json`; current adapters retain
their source-verified legacy path until the flag is implemented.

### HT-CLI-005 — Exit and envelope separation

Process exits must follow one public CLI table. Named states such as
`degraded` remain envelope data and must not reuse an error code for a
different meaning.

**Acceptance:** tests cover every declared command outcome and prove the
process exit agrees with the envelope error class.

### HT-CLI-006 — Stream discipline

Machine data belongs on stdout. Progress, warnings, and human diagnostics
belong on stderr. Piped JSON must not contain Rich decoration or incidental
logging.

**Acceptance:** stdout parses as one complete JSON document for every
structured success or refusal.

### HT-CLI-007 — Bounded output

Default structured responses must be bounded. Collections must support
projection and pagination before they can grow beyond the Framework default
response budget.

**Acceptance:** no default machine response exceeds 8 KB; truncation is
explicit and never presented as complete data.

### HT-CLI-008 — Safe local configuration

Group-root and KB overrides may come from trusted process configuration. They
must not be accepted from POC HTTP input, printed in logs as full environment
dumps, or copied into browser configuration.

**Acceptance:** request schemas contain no executable, argv, path,
environment, or working-directory fields.

### HT-CLI-009 — Actionable failures

Every machine refusal must carry a stable code, message, remediation, and
provenance. Missing CLI, Tower, KB, or catalog dependencies must not produce
an empty-success response.

**Acceptance:** the POC can render a remediation without scraping human
terminal output.

### HT-CLI-010 — Catalog mediation

The product catalog must be obtained through the CLI. The structured command
must parse and validate the canonical YAML source before returning normalized
JSON.

**Acceptance:** malformed catalog data returns an invalid/dependency error,
not an empty product list.

### HT-CLI-011 — Read-only initial allowlist

The initial POC contract contains only version, doctor, KB path, and product
catalog operations.

**Acceptance:** arbitrary command, argument, shell metacharacter, path, and
environment input cannot reach process execution.

### HT-CLI-012 — Contract evolution

A new Framework capability can enter the POC only after the CLI implements a
versioned command contract, publishes positive and negative fixtures, and the
POC adds a named operation.

**Acceptance:** documentation, schemas, CLI tests, fixtures, and POC
capability state change in the same coordinated release.

## 5. Non-functional requirements

| ID | Requirement |
|----|-------------|
| HT-CLI-NFR-001 | Supported CLI hosts are macOS and Linux for v1 |
| HT-CLI-NFR-002 | Source, docs, and generated indexes must agree on command availability |
| HT-CLI-NFR-003 | JSON schemas must preserve unknown additive fields while refusing unsupported required schema versions |
| HT-CLI-NFR-004 | Tests must run without a live Tower, external service, or writable canonical KB |
| HT-CLI-NFR-005 | Real-suite smoke tests are read-only and opt-in |
| HT-CLI-NFR-006 | Secrets, credential contents, and complete environment values never enter output fixtures |
| HT-CLI-NFR-007 | Diagnostic messages are deterministic enough for codes and schemas—not prose—to drive consumer behavior |
| HT-CLI-NFR-008 | Machine response generation must not materially exceed the underlying command's bounded local work |
| HT-CLI-NFR-009 | Documentation follows `hathor-doc@1` with globally unique IDs |
| HT-CLI-NFR-010 | Framework-created metadata uses only `.hath0r/` in this OpenSource product |

## 6. POC operation baseline

| Operation key | Current argv | Future explicit machine argv |
|---------------|--------------|------------------------------|
| `version` | `["hath0r", "--version"]` | `["hath0r", "--output", "json", "--version"]` |
| `doctor` | `["hath0r", "doctor"]` | `["hath0r", "--output", "json", "doctor"]` |
| `kb.path` | `["hath0r", "kb", "path"]` | `["hath0r", "--output", "json", "kb", "path"]` |
| `kb.products` | `["hath0r", "kb", "products"]` | `["hath0r", "--output", "json", "kb", "products"]` |

The future argv column is a requirement, not a current usage example.

## 7. Source-of-truth precedence

For executable behavior:

1. checked-in CLI source and tests;
2. released package behavior;
3. CLI product documentation;
4. POC consumer documentation;
5. Framework design intent.

For OpenSource governance and paths, repository and group rules override
product prose. A contradiction must be documented and resolved; consumers
must not choose the most convenient interpretation.

## 8. Definition of done

The CLI-side POC contract is complete when:

1. every current command is documented with success, failure, output, and
   side-effect behavior;
2. HATHOR-TS-005 schemas and exits have implementation tests;
3. CLI and POC golden fixtures share a declared contract version;
4. invalid output, timeout, missing dependency, and redaction paths are
   covered;
5. the POC uses explicit structured output and removes legacy screen
   scraping;
6. capability documentation matches released code; and
7. issue, branch, review, and promotion evidence satisfy repository policy.

Documentation completion alone does not satisfy implementation items 2–5.
