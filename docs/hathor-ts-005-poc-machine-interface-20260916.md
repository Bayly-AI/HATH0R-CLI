---
id: HATHOR-TS-005
title: "HATH0R CLI Machine Interface for the POC"
summary: "Proposed versioned JSON, error, exit, stream, and compatibility contract for machine consumption of HATH0R-CLI."
doc_type: TS
diataxis: reference
audience: [developer, architect, agent]
tags: [cli, json, schema, exit-codes, poc, specification]
version: 0.1.0
status: draft
created: 2026-09-16
updated: 2026-09-16
owner: "Raymond Bayly (BaylyAI)"
review:
  trust: unverified
  reviewed_by: null
  reviewed_at: null
  interval: 90d
  next_review: null
stale: false
supersedes: []
superseded_by: null
amended_by: []
parent: HATHOR-CANON-014
sources:
  - HATHOR-ADR-001
  - HATHOR-ADR-003
  - HATHOR-CANON-011
  - HATHOR-TS-004
  - HATHOR-REQ-002
  - HATHOR-GUIDE-038
  - "../src/hath0r_cli/cli.py"
---
# HATH0R CLI Machine Interface for the POC

## 1. Status and scope

This is a proposed technical specification. HATH0R-CLI v0.1 does not implement
`--output`, JSON envelopes, schema discovery, or the command-specific JSON
payloads below.

This specification covers only the four read-only operations needed by the
POC. It does not authorize knowledge writes, gates, orchestration, deployment,
or arbitrary command execution.

## 2. Design goals

1. One result model for human and machine renderers.
2. Explicit, versioned, bounded JSON for the POC.
3. Stable error codes and process exits.
4. No screen scraping or Rich-format parsing.
5. Additive evolution with strict required-schema handling.
6. Actionable, secret-free remediation.

## 3. Global output contract

Target flag:

```text
--output, -o json|text|auto
```

Target behavior:

| Value | Behavior |
|-------|----------|
| `json` | One JSON document on stdout; diagnostics/errors remain structured |
| `text` | Human-readable output; current CLI style may evolve |
| `auto` | TTY uses text; non-TTY uses JSON |

The POC must always pass `--output json`. It must not depend on TTY detection
or a changing default.

Current v0.1 behavior remains documented in HATHOR-GUIDE-042 until this
contract ships.

## 4. Response envelope

Every structured result uses:

```json
{
  "schema": "hath0r.cli.response/1",
  "command": "doctor",
  "generated_at": "2026-09-16T16:00:00Z",
  "state": "ok",
  "data": {},
  "diagnostics": [],
  "meta": {
    "cli_version": "0.1.0",
    "duration_ms": 12
  }
}
```

Required top-level fields:

| Field | Type | Contract |
|-------|------|----------|
| `schema` | string | Exact response major; consumer refuses unsupported major |
| `command` | string | Stable operation identity, not raw argv |
| `generated_at` | RFC 3339 string | UTC result timestamp |
| `state` | enum | `ok`, `degraded`, `unavailable`, or `error` |
| `data` | object or null | Command-specific payload |
| `diagnostics` | array | Structured refusals/warnings/remediation |
| `meta.cli_version` | SemVer string | Producing package version |
| `meta.duration_ms` | non-negative integer | Bounded command duration |

Consumers may ignore unknown additive fields. They must reject:

- an unsupported response major;
- a missing required field;
- a type-invalid command payload; or
- a success state with a required diagnostic contradiction.

## 5. Diagnostic envelope

```json
{
  "code": "KNOWLEDGEBASE_NOT_FOUND",
  "message": "The canonical OpenSource knowledgebase is unavailable.",
  "remediation": "Verify the group root and run hath0r doctor.",
  "severity": "error",
  "provenance": {
    "component": "hath0r-cli",
    "operation": "kb.path"
  },
  "ttl": null,
  "details": {}
}
```

Rules:

- `code` is stable, uppercase snake case.
- `message` is safe for an operator and contains no secret.
- `remediation` names the next safe action.
- `provenance` identifies the emitter and operation.
- `ttl` is present when bounded offline trust applies.
- `details` is schema-bounded and must not contain environment dumps.

## 6. Process exit contract

Target public exits align with the Framework:

| Exit | Meaning |
|------|---------|
| `0` | Success, including dry-run, idempotent no-op, and any explicitly declared non-blocking outcome |
| `1` | Runtime/internal failure |
| `2` | Usage or validation error |
| `3` | Not found |
| `4` | Authentication or permission failure |
| `5` | Conflict or already exists |
| `6` | Dependency unhealthy |
| `7` | Confirmation required in a non-interactive context |

Rules:

1. A process exit and a diagnostic code describe the same failure class.
2. `degraded` is an envelope state, not a second meaning for exit `2`.
3. A command-specific non-error exit requires a documented, non-overlapping
   outcome declaration.
4. State alone does not determine exit: a completed health check may report
   `degraded` and exit `6` when its required dependency assertion fails.
5. The current v0.1 commands use `0`, `1`, and Click usage exit `2`; migration
   to the target table must be release-noted and fixture-tested.
6. A missing executable is a caller spawn failure because no CLI process
   exists to return an exit.

## 7. Stream contract

For `--output json`:

- stdout contains exactly one UTF-8 JSON document and a final newline;
- stderr contains no progress on success when `--quiet` is active;
- no ANSI/Rich decoration enters stdout;
- no partial payload is success;
- a broken pipe exits without emitting a second envelope; and
- secret redaction occurs before either stream is written.

For text output, stdout remains data and stderr remains warning/progress/error
content where practical. Human text is not a compatibility API.

## 8. Command identity and invocation

| Operation | `command` field | Target argv |
|-----------|-----------------|-------------|
| Version | `version` | `hath0r --output json --version` |
| Doctor | `doctor` | `hath0r --output json doctor` |
| KB path | `kb.path` | `hath0r --output json kb path` |
| Products | `kb.products` | `hath0r --output json kb products` |

The POC owns this operation map. HTTP input cannot alter executable, argv,
flags, path, environment, profile, or working directory.

## 9. Version payload

```json
{
  "schema": "hath0r.cli.response/1",
  "command": "version",
  "generated_at": "2026-09-16T16:00:00Z",
  "state": "ok",
  "data": {
    "binary": "hath0r",
    "package": "hath0r-cli",
    "version": "0.1.0"
  },
  "diagnostics": [],
  "meta": {
    "cli_version": "0.1.0",
    "duration_ms": 1
  }
}
```

`data.version` is SemVer. Consumers must compare it with a SemVer parser, not
lexical string ordering.

## 10. Doctor payload

```json
{
  "schema": "hath0r.cli.response/1",
  "command": "doctor",
  "generated_at": "2026-09-16T16:00:00Z",
  "state": "degraded",
  "data": {
    "group_id": "hath0r-opensource",
    "control_tower": {
      "product_id": "hath0r-cli",
      "configured": true
    },
    "checks": [
      {
        "id": "canonical-kb",
        "state": "unavailable",
        "message": "Canonical knowledgebase is unavailable."
      }
    ],
    "counts": {
      "ok": 12,
      "failed": 1
    }
  },
  "diagnostics": [
    {
      "code": "KNOWLEDGEBASE_NOT_FOUND",
      "message": "The canonical OpenSource knowledgebase is unavailable.",
      "remediation": "Verify the configured group knowledgebase and rerun hath0r doctor.",
      "severity": "error",
      "provenance": {
        "component": "hath0r-cli",
        "operation": "doctor"
      },
      "ttl": null,
      "details": {
        "check_id": "canonical-kb"
      }
    }
  ],
  "meta": {
    "cli_version": "0.1.0",
    "duration_ms": 12
  }
}
```

Requirements:

- check IDs are stable kebab-case identifiers;
- counts agree with checks;
- normal JSON omits absolute host paths;
- optional verbose local diagnostics may expose paths only through an
  explicitly documented operator mode;
- overall state is derived from required check results; and
- a completed doctor result with a failed required dependency uses target
  exit `6`; an internal inability to evaluate uses exit `1`.

## 11. KB path payload

```json
{
  "schema": "hath0r.cli.response/1",
  "command": "kb.path",
  "generated_at": "2026-09-16T16:00:00Z",
  "state": "ok",
  "data": {
    "configured": true,
    "available": true,
    "path": "/trusted/local/path/.hath0r/knowledgebase"
  },
  "diagnostics": [],
  "meta": {
    "cli_version": "0.1.0",
    "duration_ms": 2
  }
}
```

The path is operator data. The POC adapter must remove it from normal browser
responses and return logical configured/available state unless a separately
authorized local diagnostic view needs the value.

If the directory is missing, `data.available` is false, state is
`unavailable`, and the process returns the declared not-found/dependency
class. A printed path never overrides a nonzero exit.

## 12. Product catalog payload

```json
{
  "schema": "hath0r.cli.response/1",
  "command": "kb.products",
  "generated_at": "2026-09-16T16:00:00Z",
  "state": "ok",
  "data": {
    "group_id": "hath0r-opensource",
    "control_tower_product_id": "hath0r-cli",
    "products": [
      {
        "product_id": "hath0r-poc",
        "product_name": "HATHOR POC",
        "role": "integration-test-bed",
        "canonical": true,
        "is_control_tower": false
      }
    ]
  },
  "diagnostics": [],
  "meta": {
    "cli_version": "0.1.0",
    "duration_ms": 3
  }
}
```

Requirements:

- parse YAML with a safe loader;
- validate required catalog fields before rendering JSON;
- emit only documented fields by default;
- never return credentials or arbitrary local file contents;
- use `--fields`, `--limit`, and `--cursor` before the catalog can exceed
  the default response budget; and
- malformed or absent source data is an explicit failure.

## 13. Bounded collections

Structured collection commands must support:

```text
--fields <comma-separated-fields>
--limit <positive-integer>
--cursor <opaque-cursor>
```

Default limit is 25. Cursor values are opaque to consumers. Responses with
pagination add:

```json
{
  "page": {
    "limit": 25,
    "next_cursor": null,
    "truncated": false
  }
}
```

The current three-product catalog does not justify mandatory pagination in
v0.1, but the contract must be available before unbounded growth.

## 14. Error cases

| Condition | State | Target exit | Diagnostic code |
|-----------|-------|-------------|-----------------|
| Invalid output value | `error` | `2` | `USAGE_INVALID` |
| Doctor required dependency check fails | `degraded` | `6` | Dependency-specific code |
| Missing KB directory from `kb.path` | `unavailable` | `3` | `KNOWLEDGEBASE_NOT_FOUND` |
| Missing product catalog | `unavailable` | `3` | `PRODUCT_CATALOG_NOT_FOUND` |
| Invalid catalog schema | `error` | `2` | `PRODUCT_CATALOG_INVALID` |
| Permission denied reading governed source | `error` | `4` | `SOURCE_PERMISSION_DENIED` |
| Unexpected runtime failure | `error` | `1` | `INTERNAL_ERROR` |

Tests and help output become the executable authority after this draft
contract is implemented.

## 15. POC mapping

The adapter validates `hath0r.cli.response/1`, then emits its own
`hathor-poc.response/1` envelope.

| CLI field | POC treatment |
|-----------|---------------|
| `state` | Mapped without upgrading failure to success |
| `data` | Reduced to route-specific browser-safe data |
| `diagnostics` | Redacted and mapped to user remediation |
| `meta.cli_version` | Exposed as CLI version |
| `meta.duration_ms` | Used for request audit/health |
| KB `path` | Removed from normal browser payload |
| Fixture input | POC source remains `fixture`, never `live-cli` |

## 16. Compatibility and versioning

- Response major changes only for breaking field/semantic changes.
- Additive optional fields keep major `1`.
- Removing or retyping a field requires a new major.
- Diagnostic codes are stable within a response major.
- The POC pins supported response majors.
- Unsupported major returns unavailable/contract-mismatch; it never falls
  back to scraping human text silently.
- Legacy text/YAML fixtures remain only during an announced migration window.

## 17. Security requirements

1. JSON generation never serializes the complete process environment.
2. Secret redaction combines known patterns with entropy/provider-aware
   detection where diagnostic text is accepted.
3. Normal doctor JSON minimizes absolute local paths.
4. Catalog parsing uses no unsafe object construction.
5. Output byte limits apply before unbounded accumulation.
6. JSON strings are data; consumers never render them as raw HTML.
7. Machine mode adds no new command or filesystem authority.

## 18. Acceptance tests

The implementation must provide:

- schema-valid success fixtures for all four operations;
- one fixture for every documented diagnostic code;
- unknown additive field compatibility;
- unsupported-major rejection;
- stdout-only JSON checks;
- ANSI/progress contamination checks;
- byte-limit tests;
- malformed catalog and missing-path tests;
- path-minimization and secret-redaction tests;
- exit/envelope agreement tests; and
- POC consumer tests against the same released fixtures.

Until these tests and the output flag exist in source, this entire machine
interface remains `planned`.
