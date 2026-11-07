---
id: HATHOR-GUIDE-045
title: "HATH0R CLI Integration Security, Governance, and Delivery"
summary: "Security boundaries, issue-backed change control, and environment promotion rules for CLI and POC integration."
doc_type: GUIDE
diataxis: how-to
audience: [developer, operator, architect, agent]
tags: [security, governance, delivery, secrets, promotion]
version: 0.1.0
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
  - HATHOR-RP-013
  - HATHOR-TS-004
  - HATHOR-GUIDE-040
  - "../AGENTS.md"
  - "../cfg/knowledge-tower.yaml"
  - "../.github/workflows/enforce-promotion-path.yml"
---
# HATH0R CLI Integration Security, Governance, and Delivery

## 1. Security posture

The current CLI-to-POC boundary is local-first and read-only. It reduces
accidental authority leakage; it is not an operating-system sandbox against a
malicious process already running with the developer's permissions.

## 2. Non-negotiable boundaries

1. Browser code cannot execute `hath0r`.
2. HTTP input cannot choose executable, argv, flag, path, environment, or
   working directory.
3. The POC server uses only named operations and fixed argv.
4. No shell evaluates an integration command.
5. CLI failures remain failures/degraded states.
6. The POC does not read Tower config or the canonical KB directly.
7. Initial integration performs no write, waiver, promotion, credential, or
   deployment action.
8. Framework-created OpenSource metadata lives only under `.hath0r/`.

Legacy metadata roots are forbidden and must not be written for compatibility.

## 3. Process controls

The POC runner must:

- resolve a trusted CLI executable;
- spawn directly;
- apply deadline and output limits;
- cap concurrency;
- terminate timed-out/oversized processes;
- use a minimal environment;
- set a safe working directory;
- distinguish exit, signal, timeout, and spawn failure;
- redact before logging; and
- record request ID, operation key, duration, exit class, and byte counts.

Audit the operation key rather than future sensitive raw argv.

## 4. Data minimization

Normal browser responses may include:

- CLI version;
- logical Tower identity;
- capability and health state;
- product-catalog fields required by the UI;
- sanitized diagnostics;
- source and freshness; and
- request correlation.

They should not include:

- home-directory paths;
- complete environment values;
- credential locations or contents;
- arbitrary CLI stderr;
- stack traces;
- unrequested KB records;
- signing or provider tokens; or
- unlabeled fixture data.

## 5. Secrets

Credentials remain outside the repository under group credential policy.

Rules:

- never commit or print secret contents;
- never put secrets in docs, fixtures, snapshots, KB records, or browser
  bundles;
- never expose server-only configuration through frontend build variables;
- redact diagnostic candidates before logs and responses;
- use layered pattern/entropy/provider-aware detection for future free-form
  diagnostics; and
- fail closed when an operation requires credentials without a mediated
  contract.

The four current CLI commands require no product-managed secret.

## 6. Structured output security

HATHOR-TS-005 implementation must:

- parse governed YAML with a safe loader;
- validate before serialization;
- omit absolute paths from normal doctor JSON;
- bound collection and diagnostic size;
- keep stdout free of terminal decoration;
- escape all string data through a standard JSON encoder;
- prevent arbitrary file selection; and
- never turn malformed source into empty-success data.

Structured output reduces parsing ambiguity; it does not grant new authority.

## 7. Work authorization

Every substantive change follows:

1. create or select a GitHub issue;
2. branch from `development`;
3. use
   `feature|bugfix|enhancement|research|fix|chore/<issue-number>-short-slug`;
4. implement and validate locally;
5. open the PR against `development`; and
6. obtain owner/code-owner approval before merge.

Canonical branches are never feature branches.

## 8. Environment promotion

Required path:

```text
local → development → testing → staging → master (Production)
```

- Feature work targets `development`.
- `testing` accepts promotion only from `development`.
- `staging` accepts promotion only from `testing`.
- `master` accepts promotion only from `staging`.
- Each stage requires its validation evidence before the next promotion.
- Humans authorize promotion.

Neither the current CLI nor the POC may initiate promotion.

## 9. Review triggers

Require explicit security and architecture review before:

- adding any mutating CLI operation;
- accepting user-provided paths or arbitrary arguments;
- handling credentials or human identity tokens;
- exposing raw KB records;
- binding a POC service beyond loopback;
- adding a public listener;
- storing durable adapter state;
- changing exit-code meaning;
- weakening timeout, output, redaction, or environment limits; or
- adding deployment or promotion capability.

## 10. Evidence

Attach as applicable:

- test and contract-schema results;
- CLI/POC fixture compatibility result;
- real-suite read-only smoke result;
- documentation validation;
- secret scan;
- dependency scan;
- affected command/exit matrix;
- known degraded cases; and
- stage deployment/URL validation for promotion.

Evidence must be reproducible and secret-free.

## 11. Refusal behavior

When a control fails:

1. stop the affected operation;
2. preserve the narrowest truthful state;
3. return a stable, secret-free diagnostic;
4. provide safe remediation;
5. leave unrelated read-only UI usable where safe;
6. do not silently switch to fixtures or legacy parsing; and
7. do not add an undocumented bypass.

## 12. Trust-model statement

Mechanical integration controls address a cooperative-but-fallible actor using
the documented interfaces. A process with arbitrary local file access can
tamper with files outside this contract. Do not describe subprocess limits,
redaction, or fixed argv as a complete local security sandbox.
