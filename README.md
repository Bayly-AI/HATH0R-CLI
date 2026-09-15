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
