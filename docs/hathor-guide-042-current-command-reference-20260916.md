---
id: HATHOR-GUIDE-042
title: "HATH0R CLI v0.2 Command Reference"
summary: "Source-verified installation, commands, outputs, exits, configuration, and limitations for the current HATH0R CLI."
doc_type: GUIDE
diataxis: reference
audience: [developer, operator, agent]
tags: [cli, commands, reference, current-state]
version: 0.2.1
status: draft
created: 2026-09-16
updated: 2026-09-19
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
# HATH0R CLI v0.2 Command Reference

## 1. Authority and scope

This page documents the current `hath0r` executable as implemented in
`src/hath0r_cli/cli.py` and package version `0.2.0`.

The shipped integration commands on this page are current. Larger ADR-003 domain trees remain design targets until status flips to shipped in `hath0r planes`.
Larger command trees in Framework papers are design targets, not aliases
available in this Python CLI. Structured JSON is available via
`--output json` (version payload is complete; doctor/kb command `data`
payloads are still landing).

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
| `hath0r --version` | Show installed CLI version | Text: version line; JSON: `hath0r.cli.response/1` with version data | Invocation/spawn error |
| `hath0r doctor` | Check group, Tower, member, and KB orientation | Text: Rich table; JSON: checks/counts payload | Exit `6` when required dependency checks fail |
| `hath0r kb path` | Print canonical group KB path | Text: absolute path; JSON: configured/available/path | Exit `3` + `KNOWLEDGEBASE_NOT_FOUND` when directory is absent |
| `hath0r kb products` | Print canonical suite product catalog | Text: YAML/text; JSON: normalized products | Exit `3` missing; exit `2` invalid |
| `hath0r planes` | List ADR-003 domains with shipped/partial/planned status | Text table; JSON planes payload | — |
| `hath0r schema` | Bounded surface schema (commands + planes + forbidden legacy) | Text list; JSON schema payload | — |

Click returns usage exit `2` for invalid command/argument input. Doctor
uses exit `6` (dependency unhealthy) when required checks fail. KB path
uses exit `3` when missing. Products use exit `3` when missing and exit `2`
when invalid.

## 4. `hath0r --version`

```sh
hath0r --version
hath0r --output json --version
```

Use this probe to detect whether the binary can be executed and to capture its
version. With `--output json` (or `-o json`), the CLI emits a
`hath0r.cli.response/1` envelope whose `data` matches the Framework
`hath0r-cli-version-v1` schema (`binary`, `package`, `version`). Text mode
prints `hath0r, version <semver>`.

## 5. `hath0r doctor`

```sh
hath0r doctor
hath0r --output json doctor
hath0r --output json --verbose doctor
```

JSON mode emits `hath0r.cli.response/1` with doctor `data` (`group_id`,
`control_tower`, `checks`, `counts`). Normal JSON omits absolute paths;
`--verbose` includes them. Failed required checks set `state: degraded`
and process exit `6`. Doctor also compares tower `cfg/products.yaml` with
the hub catalog for `product_id` / `is_control_tower` drift.

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
hath0r --output json kb path
```

Text mode prints the resolved canonical KB path, then verifies the directory
exists (path may appear before a nonzero exit).

JSON mode emits `hath0r.cli.response/1` with `data`:
`configured` (bool), `available` (bool), and `path` (string). Missing
directory → `state: unavailable`, diagnostic `KNOWLEDGEBASE_NOT_FOUND`,
exit `3`. The POC should expose logical configured/available state and strip
`path` from normal browser responses.

## 7. `hath0r kb products`

```sh
hath0r kb products
hath0r --output json kb products
```

The command reads the **group KB hub** catalog:

```text
<canonical-kb>/catalogs/suite-products.yaml
```

Text mode prints the raw file contents.

JSON mode parses with `yaml.safe_load`, validates required fields, derives
`control_tower_product_id` from the single `is_control_tower: true` product,
and emits only documented product fields (`product_id`, `product_name`,
`role`, `canonical`, `is_control_tower`). Missing catalog → exit `3`
(`PRODUCT_CATALOG_NOT_FOUND`). Malformed/invalid catalog → exit `2`
(`PRODUCT_CATALOG_INVALID`) — never an empty product list.


## 7b. `hath0r planes` / `hath0r schema` (ADR-003 discovery)

```sh
hath0r planes
hath0r --output json planes
hath0r schema
hath0r --output json schema --status shipped
```

These commands close the discoverability gap for the HATHOR-ADR-003 target
tree without claiming full domain execution. Planned domains appear with
`status: planned` and must not be invented as live verbs. Forbidden legacy
roots/binaries (`.aegis/`, `aegis`) are listed in the JSON payload.

## 8. Environment

| Variable | Default | Effect |
|----------|---------|--------|
| `HATH0R_GROUP_ROOT` | walk-up discovery, then `~/Development/OpenSource` soft fallback | Overrides the trusted local group root |
| `HATH0R_KB_PATH` | `<group-root>/.hath0r/knowledgebase` | Overrides the canonical KB path |

Values are read from the CLI process environment. The POC server may inherit
explicitly approved values, but browser requests must not set or override
them.

## 9. Current output and compatibility limits

HATH0R-CLI v0.2 provides `--output`/`-o` (`json|text|auto`) and the
`hath0r.cli.response/1` envelope. Structured `data` payloads are complete for
version, doctor, kb.path, and kb.products.

Still not provided (or only partial):

- full domain execution for planned planes (process/work/validate/…);
- bounded collection flags;
- complete stable diagnostic-code coverage on every failure path;
- knowledge search/write;
- validation or orchestration domains; or
- mutating operator commands.

Do not invoke unavailable features until their implementation, tests, and
release documentation exist.

## 10. Side effects

The four current operations are read-only with respect to repository, KB, Git,
and external system state. They read local configuration and files and emit
terminal output.

Installation changes the active Python environment and is not performed by
the POC at runtime.

## 11. Machine-consumer rule

For v0.2:

1. use only fixed argv from the four-operation allowlist;
2. spawn without a shell;
3. apply timeout and output caps;
4. request `--output json` explicitly for machine consumers;
5. classify by spawn result and process exit first;
6. validate `hath0r.cli.response/1` before using JSON `data`;
7. treat text stdout/stderr as bounded diagnostics when not using JSON; and
8. validate `kb.products` JSON against the Framework products schema (do not treat parse failure as an empty catalog).
