# HATH0R CLI

Operator and developer **control plane** for the HATHOR OpenSource agentic stack.

| Field | Value |
|-------|-------|
| Package | `hath0r-cli` |
| Binary | `hath0r` |
| Group | `hath0r-opensource` |
| Canonical KB | `/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase` |
| GitHub | [Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) |

## Install

```sh
cd /Users/raybayly/Development/OpenSource/HATH0R-CLI
python3 -m pip install -e .
hath0r --version
hath0r doctor
hath0r kb path
```

## Commands (v0.1)

| Command | Purpose |
|---------|---------|
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r kb path` | Print canonical group knowledgebase path |
| `hath0r kb products` | Show suite product catalog |
| `hath0r --version` | Package version |

These four invocations are the complete implemented v0.1 integration surface.
Structured JSON, schema discovery, knowledge search/write, validation,
orchestration, and mutating commands are not currently implemented.

## Documentation

- [Documentation index](docs/INDEX.md)
- [Current v0.1 command reference](docs/hathor-guide-042-current-command-reference-20260916.md)
- [CLI, control-tower, and POC architecture](docs/hathor-arch-004-cli-control-tower-integration-20260916.md)
- [Proposed POC machine interface](docs/hathor-ts-005-poc-machine-interface-20260916.md)
- [POC adapter integration guide](docs/hathor-guide-043-poc-adapter-integration-20260916.md)

The current command reference reflects executable source. The machine
interface is a draft contract and must not be treated as shipped behavior.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `HATH0R_GROUP_ROOT` | `/Users/raybayly/Development/OpenSource` | OpenSource group root |
| `HATH0R_KB_PATH` | `$HATH0R_GROUP_ROOT/.hath0r/knowledgebase` | Canonical KB override |

## Group membership

This repo is a **canonical** member of OpenSource HATHOR alongside:

- Framework: `../hath0r` (`HATH0R-Agentic-Framework`)
- POC: `../hath0r-poc` (`HATH0R-Agentic-POC`)

See `AGENTS.md`, `cfg/suite.yaml`, and the group hub `../AGENTS.md`.

## License

Apache License 2.0 — see `LICENSE`.
