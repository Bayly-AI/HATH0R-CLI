# Group policy pack (OpenSource Project)

Canonical **versioned** group agent rules and Warp policy for `hath0r-opensource`.

| File | Role |
|------|------|
| `AGENTS.md` | Group agent control rules |
| `WARP.md` | Group operator/agent policy |

## Why here

The OpenSource **folder root** (`~/Development/OpenSource`) is a workspace container, not a git repository. Policy that lived only there could not be recovered from GitHub.

**Source of truth:** this directory in [Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) (control tower).

## Materialize local hub copies

```sh
# from HATH0R-CLI checkout
./scripts/sync-group-hub.sh
# or:
# GROUP_ROOT=/path/to/OpenSource ./scripts/sync-group-hub.sh
```

Writes/updates:

- `$GROUP_ROOT/AGENTS.md`
- `$GROUP_ROOT/WARP.md`

Doctor and walk-up discovery continue to read the group root files after sync.

## Edit workflow

1. Change files in `cfg/group/` on a work branch (issue-first).
2. PR → `development` on HATH0R-CLI.
3. After merge/pull, run `./scripts/sync-group-hub.sh` on each machine.
4. Do not invent a second long-lived fork of policy only under the bare OpenSource folder.
