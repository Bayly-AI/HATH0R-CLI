<p align="center">
  <img src="lib/assets/images/hathor-logo-1.png" alt="HATHOR logo" width="280" />
</p>

# HATH0R CLI

Operator and developer **control plane** for the HATHOR OpenSource agentic stack.

| Field | Value |
|-------|-------|
| Package | `hath0r-cli` |
| Binary | `hath0r` |
| Group | `hath0r-opensource` |
| Canonical KB | `$HATH0R_GROUP_ROOT/.hath0r/knowledgebase` (discovered; see Environment) |
| GitHub | [Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) |

## Install

Preferred (operators):

```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli
hath0r --version
hath0r doctor
```

Developer (editable monorepo):

```sh
cd /path/to/OpenSource/HATH0R-CLI   # or set HATH0R_GROUP_ROOT
python3 -m pip install -e ".[dev]"
hath0r --version
hath0r doctor
hath0r kb path
```

Release packaging (fileset, binary, npm client, CI): see
[Install and release matrix](docs/hathor-guide-047-install-and-release-20260918.md)
and issue [#30](https://github.com/Bayly-AI/HATH0R-CLI/issues/30).

```sh
make fileset
make wheel
# optional engine binary:
# pip install -e ".[release]" && make binary
```


## Commands (v0.2)

| Command | Purpose |
|---------|---------|
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r kb path` | Print canonical group knowledgebase path |
| `hath0r kb products` | Show suite product catalog |
| `hath0r --version` | Package version |
| `hath0r planes` | ADR-003 domain status map (shipped/partial/planned) |
| `hath0r schema` | Bounded surface schema + forbidden legacy roots |
| `hath0r mcp sources list` | List 1-Nation federal vote-source inventory through MCP |
| `hath0r mcp sources test SOURCE_ID` | Test an allowlisted vote source through 1N-MCP |
| `hath0r mcp sources fetch-sample SOURCE_ID` | Fetch a bounded vote-source sample through 1N-MCP |

Shipped surface is discoverable via `planes`/`schema`. Full process/work/validate/
knowledge-write domains remain **planned** until implemented behind contracts.
Never call `aegis` or create `.aegis/`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history (current: **v0.2.0**).

## Documentation

- [Documentation index](docs/INDEX.md)
- [Current v0.2 command reference](docs/hathor-guide-042-current-command-reference-20260916.md)
- [CLI, control-tower, and POC architecture](docs/hathor-arch-004-cli-control-tower-integration-20260916.md)
- [Proposed POC machine interface](docs/hathor-ts-005-poc-machine-interface-20260916.md)
- [POC adapter integration guide](docs/hathor-guide-043-poc-adapter-integration-20260916.md)

The current command reference reflects executable source. The machine
interface is a draft contract and must not be treated as shipped behavior.

## Environment

| Variable | Default / discovery | Purpose |
|----------|---------------------|---------|
| `HATH0R_GROUP_ROOT` | See discovery order below | OpenSource group root override |
| `HATH0R_KB_PATH` | `$HATH0R_GROUP_ROOT/.hath0r/knowledgebase` | Canonical KB override |

### Group root discovery order

1. **`HATH0R_GROUP_ROOT`** — if set, use it (expanded/resolved).
2. **Walk-up from cwd** — find a directory with `AGENTS.md` containing `hath0r-opensource` and a `.hath0r/` directory.
3. **Soft fallback** — `~/Development/OpenSource` only if it looks like a real group root (same markers).
4. **Error** — clear message with remediation if nothing matches.

`HATH0R_KB_PATH` always wins for the knowledgebase path when set; otherwise KB is `$group_root/.hath0r/knowledgebase`.

## Group membership

This repo is a **canonical** member of OpenSource HATHOR alongside:

- Framework: `../hath0r` (`HATH0R-Agentic-Framework`)
- POC: `../hath0r-poc` (`HATH0R-Agentic-POC`)

See `AGENTS.md`, `cfg/suite.yaml`, and the group hub `../AGENTS.md`.

## License

Apache License 2.0 — see `LICENSE`.

## Group hub policy sync

Canonical OpenSource group `AGENTS.md` / `WARP.md` live in `cfg/group/`. Materialize to the group root with `./scripts/sync-group-hub.sh` (see `cfg/group/README.md`).
