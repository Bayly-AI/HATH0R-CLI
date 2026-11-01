---
id: HATHOR-GUIDE-043
title: "Integrating the HATHOR POC with HATH0R CLI"
summary: "Task-oriented guidance for safely connecting the React/TypeScript POC adapter to current and future HATH0R CLI contracts."
doc_type: GUIDE
diataxis: how-to
audience: [developer, operator, agent]
tags: [poc, typescript, adapter, cli, integration]
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
  - HATHOR-REQ-001
  - HATHOR-ARCH-003
  - HATHOR-GUIDE-038
  - HATHOR-REQ-002
  - HATHOR-ARCH-004
  - HATHOR-TS-005
  - "../src/hath0r_cli/cli.py"
---
# Integrating the HATHOR POC with HATH0R CLI

## 1. Integration status

The CLI operations are implemented. The TypeScript adapter is a documented
POC target and may not exist yet. Verify the POC repository before assuming
its routes, scripts, or runner are available.

## 2. Verify local orientation

Run the source-verified probes:

```sh
hath0r --version
hath0r doctor
hath0r kb path
hath0r kb products
```

Fix orientation failures before testing a live adapter. Do not use
design-stage Framework commands as a workaround.

## 3. Define named operations

The server owns exactly four operation keys:

| Key | Current argv |
|-----|--------------|
| `version` | `["hath0r", "--version"]` |
| `doctor` | `["hath0r", "doctor"]` |
| `kb.path` | `["hath0r", "kb", "path"]` |
| `kb.products` | `["hath0r", "kb", "products"]` |

The API accepts route intent, not argv. Reject any request field that attempts
to select an executable, argument, flag, environment value, path, profile, or
working directory.

## 4. Build the runner boundary

The runner must:

1. resolve a trusted `hath0r` executable;
2. spawn directly with an argv array;
3. use no shell;
4. set an explicit safe working directory;
5. pass a minimal approved environment;
6. cap stdout and stderr independently;
7. enforce a deadline and concurrency ceiling;
8. terminate the process on timeout/limit;
9. retain exit, signal, and termination class separately; and
10. redact before logs or HTTP responses.

Return a process result to a pure normalizer. Do not mix process control with
React or route rendering.

## 5. Normalize v0.1 results

### Version

- Exit `0` plus non-empty bounded text means available.
- Parse version conservatively and retain raw text only as local diagnostic.
- Compare versions with SemVer logic.

### Doctor

- Process exit is the overall verdict.
- Do not scrape Rich table cells into a stable check API.
- A nonzero exit maps to degraded suite health, not a server crash.

### KB path

- Evaluate exit before stdout.
- Return configured/available state in ordinary browser responses.
- Keep absolute path details out of normal logs and UI.

### Products

- Treat stdout as YAML/text.
- Parse with a safe YAML parser only if the UI requires normalized products.
- Validate the normalized shape.
- Map parse failure to invalid output, never `[]`.

## 6. Map runner failures

| Runner result | POC state | Guidance |
|---------------|-----------|----------|
| Spawn error / missing binary | `unavailable` | Install/configure CLI |
| Exit `0` | Operation-specific `ok` or declared state | Validate output |
| Doctor nonzero | `degraded` | Preserve bounded remediation |
| KB/catalog nonzero | `unavailable` for dependent capability | Do not use partial stdout |
| Timeout | `error` | Process must be terminated |
| Output limit | `error` | Do not parse truncated output |
| Malformed normalized data | `error` | Contract/fixture issue |

HTTP status and the POC envelope state have separate purposes. An overview can
return HTTP `200` while accurately reporting an unavailable CLI dependency.

## 7. Publish capability state

The POC capability document should derive:

| Capability | v0.1 state |
|------------|------------|
| `cli.version` | Implemented when the probe succeeds |
| `cli.doctor` | Implemented; health may be degraded |
| `kb.path` | Implemented; availability may fail |
| `kb.products` | Implemented; current media is YAML/text |
| `cli.structured-output` | Planned |
| `framework.knowledge-search` | Unavailable |
| `framework.validation` | Unavailable |
| `framework.orchestration` | Unavailable |
| `operator.mutations` | Out of scope |

Capabilities must not become implemented based only on a UI flag.

## 8. Use deterministic fixtures

Maintain fixtures for:

- all four successes;
- missing executable;
- doctor failure;
- KB missing;
- catalog missing;
- malformed catalog;
- timeout;
- stdout/stderr limit;
- redaction candidate; and
- fixture-source labeling.

Fixtures contain no real home paths, tokens, credential contents, or complete
environment values. Tests label fixture responses as synthetic.

## 9. Adopt structured output

After HATHOR-TS-005 is implemented:

1. add explicit `--output json` argv to the operation map;
2. validate `hath0r.cli.response/1`;
3. add released success and refusal fixtures from the CLI repository;
4. retain the old parser only for an explicit compatibility window;
5. fail closed on an unsupported response major;
6. remove Rich/YAML screen scraping when compatibility ends; and
7. update CLI and POC capability documentation together.

Do not silently fall back to text when JSON was requested and returned an
invalid schema.

## 10. Add a future Framework capability

Before adding any new operation:

1. confirm the command exists in released HATH0R-CLI;
2. review its authority and side effects;
3. require a versioned input/output/error contract;
4. add a fixed operation key and argv;
5. add negative security and failure fixtures;
6. update API schemas and browser states;
7. perform a threat review if authority expands; and
8. update both product documentation trees.

Mutating, credential-bearing, path-accepting, or deployment operations require
separate authorization and must not be added to the initial POC allowlist.
