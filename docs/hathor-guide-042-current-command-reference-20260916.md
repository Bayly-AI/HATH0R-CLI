---
id: HATHOR-GUIDE-042
title: "HATH0R CLI v0.1 Command Reference"
summary: "Source-verified installation, commands, outputs, exits, configuration, and limitations for the current HATH0R CLI."
doc_type: GUIDE
diataxis: reference
audience: [developer, operator, agent]
tags: [cli, commands, reference, current-state]
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
  - "../README.md"
  - "../pyproject.toml"
  - "../src/hath0r_cli/__init__.py"
  - "../src/hath0r_cli/cli.py"
---
# HATH0R CLI v0.1 Command Reference

## 1. Authority and scope

This page documents the current `hath0r` executable as implemented in
`src/hath0r_cli/cli.py` and package version `0.1.0`.

Only the four invocations on this page are current integration commands.
Larger command trees in Framework papers are design targets, not aliases
available in this Python CLI.

## 2. Install

From this repository:

```sh
python3 -m pip install -e .
hath0r --version
```

Development dependencies:

```sh
python3 -m pip install -e ".[dev]"
```

The package requires Python 3.10 or newer and installs the `hath0r` console
script.

## 3. Current commands

| Command | Purpose | Success output | Current failure behavior |
|---------|---------|----------------|--------------------------|
| `hath0r --version` | Show installed CLI version | Click version text | Invocation/spawn error |
| `hath0r doctor` | Check group, Tower, member, and KB orientation | Rich table, version, pass summary | Exit `1` after reporting failed checks |
| `hath0r kb path` | Print canonical group KB path | Absolute path text | Prints path, then exits nonzero if directory is absent |
| `hath0r kb products` | Print canonical suite product catalog | YAML/text file contents | Exits nonzero if catalog is absent |

Click returns usage exit `2` for invalid command/argument input. The
application explicitly uses exit `1` for current doctor/KB failures.

## 4. `hath0r --version`

```sh
hath0r --version
```

Use this probe to detect whether the binary can be executed and to capture its
version. Treat the output as human text in v0.1; no JSON version payload exists.

## 5. `hath0r doctor`

```sh
hath0r doctor
```

Doctor checks:

- group root;
- group `AGENTS.md` and `WARP.md`;
- canonical KB and suite catalog;
- catalog reference to the control tower;
- four Tower configuration files;
- Tower identity, path, and GitHub remote;
- Framework, CLI, and POC member repositories;
- member `AGENTS.md` files; and
- member control-tower pointers.

The table's final exit status is the health verdict. Do not treat visible
`ok` rows or partial output as overall success when the process exits nonzero.
Rich formatting is not a stable machine schema.

## 6. `hath0r kb path`

```sh
hath0r kb path
```

The command prints the resolved canonical KB path. It then verifies that the
directory exists.

Important current behavior: the path is printed before the existence failure.
A machine consumer must evaluate the process exit before using stdout.

The POC should expose logical configured/available state instead of the raw
home-directory path in normal browser responses.

## 7. `hath0r kb products`

```sh
hath0r kb products
```

The command reads:

```text
<canonical-kb>/catalogs/suite-products.yaml
```

and prints its contents without parsing. Therefore:

- media is YAML/text, not JSON;
- field shape comes from the catalog file;
- parsing belongs in an isolated, schema-validating compatibility adapter;
- output must be byte-bounded by the caller; and
- a parse error is not an empty catalog.

## 8. Environment

| Variable | Default | Effect |
|----------|---------|--------|
| `HATH0R_GROUP_ROOT` | `/Users/raybayly/Development/OpenSource` | Changes the trusted local group root |
| `HATH0R_KB_PATH` | `<group-root>/.hath0r/knowledgebase` | Overrides the canonical KB path |

Values are read from the CLI process environment. The POC server may inherit
explicitly approved values, but browser requests must not set or override
them.

## 9. Current output and compatibility limits

HATH0R-CLI v0.1 does not provide:

- `--output` or `-o`;
- JSON response envelopes;
- command schema discovery;
- bounded collection flags;
- stable diagnostic codes;
- knowledge search/write;
- validation or orchestration domains; or
- mutating operator commands.

Do not invoke those features until their implementation, tests, and release
documentation exist.

## 10. Side effects

The four current operations are read-only with respect to repository, KB, Git,
and external system state. They read local configuration and files and emit
terminal output.

Installation changes the active Python environment and is not performed by
the POC at runtime.

## 11. Machine-consumer rule

For v0.1:

1. use only fixed argv from the four-operation allowlist;
2. spawn without a shell;
3. apply timeout and output caps;
4. classify by spawn result and process exit first;
5. treat stdout/stderr as bounded diagnostics;
6. parse catalog YAML only behind validation; and
7. migrate to HATHOR-TS-005 only after structured output ships.
