---
id: HATHOR-PLAYBOOK-001
title: Hath0r repository initialization setup playbook
date: 2026-09-19
status: canonical
rule: CR-HATH0R-INIT-001
---

# HATHOR-PLAYBOOK-001 — Repo init setup

## Main entry statement (CRITICAL)

**Before initializing (or re-initializing) any repository with Hath0r, agents MUST:**

1. **Locate this setup playbook** (canonical). If missing or incomplete, **create or update it first**, then proceed.
2. **Locate a runbook for an individual repo with the same technology stack** (e.g. React+Vite UXP, Python CLI, Amplify hosting).  
   - Prefer an existing sibling/product `docs/runbook.md` (or `docs/*runbook*`) for that tech family.  
   - If none exists, **create a tech-appropriate runbook in the target repo** before finishing init.
3. Only after (1) and (2): apply fileset/layout, `.hath0r/`, `cfg/`, contracts pin, `AGENTS.md` identity, and bootstrap.

Layout scaffolding without a documented ops path is **incomplete initialization**.

Canonical playbook path:

```text
/Users/raybayly/Development/OpenSource/hath0r/docs/developers/hathor-playbook-001-repo-init-setup-20260919.md
```

Control tower / engine source:

```text
/Users/raybayly/Development/OpenSource/HATH0R-CLI
/Users/raybayly/Development/OpenSource/hath0r
```

## Scope

| Mode | When | Notes |
|------|------|-------|
| **Standalone** | App lives outside OpenSource group (e.g. Websites, 1-Nation) | Local `.hath0r/knowledgebase` stub; optional `HATH0R_GROUP_ROOT` for doctor/kb |
| **Member** | Git repo is a sibling under OpenSource | Stub KB → group hub; register in tower catalog when promoted |

Do **not** register private/product trees into OpenSource `cfg/products.yaml` unless explicitly promoted.

## Prerequisites

- Operator CLI installed: `hath0r` on `PATH` (`pipx install hath0r-cli` or checksummed Release binary). Current pin: **0.2.0**.
- Framework + CLI checkouts available under OpenSource (for contracts snapshot and docs).
- Secrets never committed; use `/Users/raybayly/Development/.credentials/<service>/.env` (or gitignored project `.env`).

## Same-technology runbook gate

| Tech family (examples) | Look for | If missing, create |
|------------------------|----------|--------------------|
| React + Vite UXP / marketing site | `docs/runbook.md` with install/dev/build/deploy/rollback | Target repo `docs/runbook.md` |
| Amplify-hosted static SPA | Deploy/rollback Amplify procedures | Extend runbook with branch→env map |
| Python CLI / control tower | Doctor, packaging, release | `docs/` operator runbook |
| Other stacks | Nearest same-stack Bayly-AI repo runbook | New `docs/runbook.md` for target |

Reference same-tech peers before inventing process (e.g. Bayly Consulting UXP ↔ 1 Nation UXP ↔ BaylyAI UXP for React+Vite).

## Universal Project Layout (minimum)

```text
<repo>/
  .hath0r/knowledgebase/   # stub/pointer only unless this IS a hub
  cfg/                     # suite.yaml, product.yaml, knowledge-tower.yaml
  bin/hath0r-bootstrap.sh  # post-init checks
  contracts/               # pinned CLI schemas + exit-codes
  MANIFEST.json            # fileset/cli/contracts versions
  VERSION                  # fileset pin
  NOTICE                   # fileset notice
  AGENTS.md                # identity + CR-HATH0R-INIT-001 + product rules
  src/ docs/ lib/          # app + docs + assets (create if absent)
  test/ or tests/          # tests home (or document vitest-in-src)
  dist/                    # build output (gitkeep if empty)
```

Hidden root rule (**cr-hath0r-root-001**): use **only** `.hath0r/`. Never create `.ai/`, `.aegis/`, or `.infraOS/` for framework metadata.

## Procedure

### A. Gate

1. Open this playbook.
2. Find or create same-tech `docs/runbook.md` for the target (or a peer).
3. Confirm `hath0r --version` works.

### B. Fileset / layout

Preferred: build and unpack OpenSource fileset, then merge into the existing app tree (do not clobber app source):

```sh
cd /Users/raybayly/Development/OpenSource/HATH0R-CLI
python3 scripts/build_fileset.py --product-id <product-id> \
  --framework-root /Users/raybayly/Development/OpenSource/hath0r
# merge stage contents into target repo; customize templates
```

Or hand-scaffold the minimum layout above and pin contracts:

```sh
cp /Users/raybayly/Development/OpenSource/hath0r/lib/schemas/* <repo>/contracts/
cp /Users/raybayly/Development/OpenSource/hath0r/lib/contracts/exit-codes.yaml <repo>/contracts/
```

### C. Product identity (`cfg/`)

Create non-secret:

- `cfg/product.yaml` — `product_id`, name, github, `layout: hathor-upl`, fileset/cli versions
- `cfg/suite.yaml` — `mode: standalone|member`, group pointers, control tower product id
- `cfg/knowledge-tower.yaml` — stub KB path, `operator_cli: hath0r`

### D. AGENTS.md

- Keep product-specific stack/commands.
- Add HATHOR identity block (product id, mode, hidden root, CLI).
- Include **CR-HATH0R-INIT-001** (this gate).
- Include org promotion path **CR-BAI-001** when applicable.

### E. Bootstrap

```sh
chmod +x bin/hath0r-bootstrap.sh
./bin/hath0r-bootstrap.sh
# optional suite doctor:
# export HATH0R_GROUP_ROOT=/Users/raybayly/Development/OpenSource
# hath0r doctor
```

### F. Runbook completion

Ensure target `docs/runbook.md` covers at least:

- Install / dev / quality / test / build
- Deploy & rollback for the host (e.g. Amplify)
- Hath0r bootstrap & doctor (standalone vs suite)
- Promotion path branches if used

### G. Done criteria

- [ ] Playbook followed (this doc)
- [ ] Same-tech runbook exists and is linked from `AGENTS.md`
- [ ] `.hath0r/` only (no legacy hidden roots)
- [ ] `cfg/*` + `MANIFEST.json` + contracts pin present
- [ ] `./bin/hath0r-bootstrap.sh` exits 0
- [ ] App still builds with its native toolchain

## Related

| Doc | Role |
|-----|------|
| `OpenSource/AGENTS.md` | Group control rules |
| `OpenSource/WARP.md` | Group policy |
| `HATH0R-CLI/docs/hathor-guide-047-install-and-release-20260918.md` | Install/release matrix |
| `HATH0R-CLI/README.md` | CLI commands v0.x |
| Framework `README.md` | UPL overview |

Updated: 2026-09-19
