# HATHOR OpenSource fileset

Drop-in project pack for orienting a HATHOR OpenSource member or standalone stub.

| Field | Value |
|-------|-------|
| Fileset version | `{{FILESET_VERSION}}` |
| Engine (CLI) version | `{{CLI_VERSION}}` |
| Contracts pin | `{{CONTRACTS_VERSION}}` |
| License | Apache-2.0 |

## Unpack

```sh
tar -xzf hath0r-fileset-{{FILESET_VERSION}}.tar.gz
cd hath0r-fileset-{{FILESET_VERSION}}
# optional: export HATH0R_GROUP_ROOT=/path/to/OpenSource
./bin/hath0r-bootstrap.sh
```

## Contents

- `AGENTS.md` — agent orientation template
- `cfg/` — suite / knowledge-tower stubs (non-secret)
- `.hath0r/knowledgebase/` — local KB stub/pointer
- `contracts/` — pinned CLI response schemas + exit-code contract (when available)
- `bin/hath0r-bootstrap.sh` — doctor-oriented smoke check
- `MANIFEST.json` — version matrix
- `LICENSE` / `NOTICE`

## Modes

- **Member**: place under a group root with `hath0r-opensource` markers.
- **Standalone**: use env overrides; keep stub KB until a hub exists.

## Security

- No secrets, no absolute developer paths.
- Install the engine from a trusted channel (PyPI / checksummed Release binary).
- Do not pipe unverified `curl | sh` installers.
