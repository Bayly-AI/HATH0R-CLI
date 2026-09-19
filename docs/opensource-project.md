<p align="center">
  <img src="../lib/assets/images/hathor-logo-1.png" alt="HATHOR logo" width="280" />
</p>

# HATHOR OpenSource Project

The **HATHOR OpenSource Project** standardizes how agents interface with projects, knowledge, and secure host capabilities via a **framework (contracts)**, an **operator CLI (control tower)**, and optional consumers.

| Field | Value |
|-------|-------|
| Group | `hath0r-opensource` |
| Control tower | [HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) |
| Operator CLI | `hath0r` (`hath0r-cli`) |
| Production package | [hath0r-cli 0.2.0 on PyPI](https://pypi.org/project/hath0r-cli/0.2.0/) |
| License | Apache 2.0 |
| Milestone status | **Initial trio build-out complete** (2026-09-19) |

**Framework and CLI remain open products** and continue to version. The POC is a **completed, archived** integration milestone — not a required live checkout.

---

## Repositories

| Repository | Role | GitHub | Status |
|------------|------|--------|--------|
| **HATHOR Framework** | Canonical architecture, contracts, documentation corpus | [Bayly-AI/HATH0R-Agentic-Framework](https://github.com/Bayly-AI/HATH0R-Agentic-Framework) | **Open** — contracts on `development`; versions ongoing |
| **HATH0R CLI** | Control tower and operator CLI (`hath0r`) | [Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) | **Open / production** — `v0.2.0` on `master` + PyPI |
| **HATHOR POC** | React/TypeScript integration console (consumer evidence) | [Bayly-AI/HATH0R-Agentic-POC](https://github.com/Bayly-AI/HATH0R-Agentic-POC) | **Archived** — P1–P11 complete; read-only |

### How they relate

```text
Framework (defines contracts)     ← open, versions forward
    │
    ▼
CLI (implements contracts)        ← open, production entrypoint
    │
    ▼
Consumers (POC, apps, agents)     ← POC archived as first proof
```

A capability is production-ready when:

1. Framework defines the contract (schema, exit, security); and  
2. CLI implements, tests, and releases it.

Optional consumers (including the archived POC pattern) adapt via fixed operations — never free-form shell.

---

## Quick start (production)

### Prerequisites

- macOS or Linux  
- Python 3.10+  
- Git (for Framework docs/contracts checkout when needed)

### Install the CLI

```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli==0.2.0
hath0r --version
hath0r --output json --version
```

Developer editable install:

```sh
git clone https://github.com/Bayly-AI/HATH0R-CLI.git
cd HATH0R-CLI
python3 -m pip install -e ".[dev]"
```

### Clone the active group members

```sh
mkdir -p ~/Development/OpenSource && cd ~/Development/OpenSource
git clone https://github.com/Bayly-AI/HATH0R-Agentic-Framework.git hath0r
git clone https://github.com/Bayly-AI/HATH0R-CLI.git HATH0R-CLI
# POC is archived — clone only if you need historical reference:
# git clone https://github.com/Bayly-AI/HATH0R-Agentic-POC.git hath0r-poc
```

### Verify the suite

```sh
export HATH0R_GROUP_ROOT=~/Development/OpenSource   # if needed
hath0r doctor
hath0r kb path
hath0r kb products
```

`doctor` may report the archived POC member missing — expected when POC is not checked out.

---

## Milestone record (initial build-out)

| Phase | Repository | Delivered |
|-------|------------|-----------|
| 1 | Framework | F1–F4: cfg, schemas, exit contracts, CI |
| 2 | CLI | C1–C9: portable paths, JSON envelope, tests, fixtures, CI |
| 3 | POC | P1–P11: full adapter + UI + tests; then **archived** |
| Release | CLI | Packaging (#30), tag `v0.2.0`, PyPI publish, promote to `master` |

Session archive (Framework):

- `hath0r/docs/architect/sessions/2026-09-19-opensource-trio-milestone-session-log.md`
- `hath0r/docs/architect/sessions/2026-09-19-opensource-trio-milestone-summary-report.md`

CLI release notes: [CHANGELOG.md](../CHANGELOG.md) · [Install & release guide](hathor-guide-047-install-and-release-20260918.md)

---

## Branch model & promotion

```text
local → development → testing → staging → master (Production)
```

Canonical branches (locked — never delete): `development`, `testing`, `staging`, `master`.

Work branches: `<type>/<issue-number>-short-slug`  
Types: `feature`, `bugfix`, `enhancement`, `research`, `fix`, `chore`

Never skip promotion stages. Enforced by `.github/workflows/enforce-promotion-path.yml`.

---

## Contribution guidelines

1. **Issue first** — no issue → no branch.  
2. **Read docs** — Framework `docs/` is the group corpus; CLI `docs/` for operator surface.  
3. **Check open issues** across active repos:

```sh
gh search issues --state open \
  --repo Bayly-AI/HATH0R-Agentic-Framework \
  --repo Bayly-AI/HATH0R-CLI
```

4. PR base = `development` for feature work.  
5. Promote only along the path above.

---

## Architecture boundaries

| Product | Owns | Must not become |
|---------|------|-----------------|
| Framework | Architecture, schemas, contracts, docs | Runtime control plane |
| CLI | Control tower, operator entry, KB/catalog mediation | Browser backend or second KB store |
| POC (archived) | Historical consumer evidence | Required live dependency |

### Trust boundaries

| Boundary | Control |
|----------|---------|
| Consumer → CLI | Named ops, fixed argv, no shell, timeouts, redaction |
| CLI → filesystem/KB | Documented env + discovery only |
| Framework docs → code | Source + tests required before “implemented” claims |

---

## Project layout (active)

```text
OpenSource/
├── AGENTS.md                       # materialized hub copy (not git)
├── WARP.md                         # materialized hub copy (not git)
├── .hath0r/knowledgebase/          # group KB hub
├── HATH0R-CLI/                     # control tower + hath0r
│   └── cfg/group/                  # CANONICAL group AGENTS.md + WARP.md (git)
└── hath0r/                         # Framework contracts + docs
```

### Group hub versioning (P1)

| Layer | Path | Git? |
|-------|------|------|
| **Canonical** | `HATH0R-CLI/cfg/group/{AGENTS,WARP}.md` | **Yes** (this repo) |
| Materialized | `OpenSource/{AGENTS,WARP}.md` | No — workspace container |
| Sync | `./scripts/sync-group-hub.sh` | — |

Edit policy only under `cfg/group/`, PR to `development`, then run the sync script on each machine. `CR-HATH0R-INIT-001` and other group rules are recoverable from GitHub via the control tower.

POC is not required under the group root for day-to-day operator use.

---

## Links

| Resource | URL |
|----------|-----|
| CLI repo | https://github.com/Bayly-AI/HATH0R-CLI |
| CLI Release v0.2.0 | https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.2.0 |
| PyPI | https://pypi.org/project/hath0r-cli/ |
| Framework | https://github.com/Bayly-AI/HATH0R-Agentic-Framework |
| POC (archived) | https://github.com/Bayly-AI/HATH0R-Agentic-POC |
