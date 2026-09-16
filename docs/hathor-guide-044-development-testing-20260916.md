---
id: HATHOR-GUIDE-044
title: "HATH0R CLI Development and POC Contract Testing"
summary: "Development workflow and target test strategy for keeping CLI behavior, machine schemas, POC fixtures, and documentation synchronized."
doc_type: GUIDE
diataxis: how-to
audience: [developer, agent]
tags: [development, testing, pytest, contracts, fixtures]
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
  - HATHOR-REQ-002
  - HATHOR-TS-005
  - HATHOR-GUIDE-039
  - "../Makefile"
  - "../pyproject.toml"
  - "../src/hath0r_cli/cli.py"
---
# HATH0R CLI Development and POC Contract Testing

## 1. Current-state warning

The package declares `pytest` as a development dependency, but this
repository currently has no checked-in Python tests. The Makefile's `test`
target also masks pytest failure with `|| true`.

Therefore `make test` is not current evidence of a passing blocking test gate.
This document describes the target testing contract; it does not claim that
the suite exists.

## 2. Set up

```sh
python3 -m pip install -e ".[dev]"
hath0r --version
```

Development must use an authorizing issue and a branch from `development`.

## 3. Target test layout

```text
tests/
├── unit/
│   ├── test_paths.py
│   ├── test_catalog.py
│   ├── test_results.py
│   └── test_redaction.py
├── cli/
│   ├── test_version.py
│   ├── test_doctor.py
│   ├── test_kb_path.py
│   └── test_kb_products.py
├── contract/
│   ├── test_response_schema.py
│   ├── test_exit_codes.py
│   └── fixtures/
└── integration/
    └── test_poc_fixture_compatibility.py
```

Tests should use temporary directories and Click's test runner. They must not
depend on or mutate the developer's real group KB.

## 4. Test layers

### Unit

Test pure behavior:

- group-root and KB resolution;
- catalog parsing/validation;
- result and diagnostic construction;
- state aggregation;
- version normalization;
- redaction; and
- collection bounding.

### CLI

Invoke each command through Click and assert:

- process exit;
- stdout/stderr discipline;
- current text behavior;
- future JSON schema;
- no ANSI contamination in JSON;
- missing file/path behavior; and
- no write side effects.

### Contract

For HATHOR-TS-005:

- validate every golden JSON document;
- ensure codes and exits agree;
- reject unsupported schema majors;
- accept unknown additive fields;
- enforce required fields;
- enforce response-size limits; and
- test all documented error classes.

### POC compatibility

Publish a fixture set that the TypeScript adapter can consume without running
the real CLI. Include the response schema version and CLI release version in
fixture metadata.

The POC may copy released fixtures for hermetic tests. It must not copy Tower
or KB authoritative data.

### Real-suite smoke

Opt-in smoke tests may run:

```sh
hath0r --version
hath0r doctor
hath0r kb path
hath0r kb products
```

They are read-only and environment-dependent, so they do not replace
hermetic tests.

## 5. Required negative cases

| Area | Cases |
|------|-------|
| Invocation | Unknown command, invalid output mode, missing executable at consumer |
| Doctor | Missing group files, Tower config mismatch, member missing, KB missing |
| KB path | Override missing, permission failure, path exists as wrong type |
| Catalog | Missing file, invalid YAML, invalid fields, oversized source |
| JSON | Truncated document, unsupported major, wrong type, contradictory state |
| Streams | ANSI/progress on stdout, partial JSON, output overflow |
| Security | Secret-like diagnostic, untrusted path/argv input, unsafe YAML payload |
| Consumer | Timeout, cancellation, fixture/live confusion, legacy fallback refusal |

## 6. Development sequence

For a CLI contract change:

1. identify the authorizing issue and affected requirement;
2. add a failing unit/contract test;
3. implement one result model independent of renderer;
4. preserve or intentionally version compatibility;
5. generate/update golden fixtures;
6. run Python tests and static checks;
7. run the POC's fixture compatibility tests when available;
8. perform the four-command local smoke;
9. update command/capability documentation; and
10. attach reproducible evidence to the issue/PR.

## 7. Target quality gate

A future blocking repository check should fail on:

- pytest failure or no tests collected when tests are expected;
- format/lint/type failure;
- invalid JSON schema fixtures;
- documented exit mismatch;
- generated documentation index drift;
- unsupported command claims;
- secret findings;
- active legacy metadata roots;
- broken links; or
- POC fixture incompatibility for a declared supported contract.

The existing Makefile must be corrected in a separately authorized code
change before it can serve as that gate.

## 8. Fixture ownership

HATH0R-CLI owns:

- canonical command success/error fixtures;
- response schemas;
- diagnostic-code registry;
- exit mappings; and
- compatibility policy.

The POC owns:

- process-spawn and timeout fixtures;
- HTTP envelope fixtures;
- redaction at the browser boundary;
- UI state fixtures; and
- live/fixture source labeling.

Shared fixtures must be traceable to a CLI version and must not contain local
secrets or real absolute home paths.

## 9. Definition of done

A command-contract change is done only when source, tests, schemas, fixtures,
help, product docs, and POC capability state agree. A passing local smoke
without hermetic negative tests is insufficient.
