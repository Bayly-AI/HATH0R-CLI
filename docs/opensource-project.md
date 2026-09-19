<p align="center">
  <img src="../lib/assets/images/hathor-logo-1.png" alt="HATHOR logo" width="280" />
</p>

# HATHOR OpenSource Project

The **HATHOR OpenSource Project** is an agentic application framework, operator CLI, and integration test bed — standardizing how agents interface with projects, knowledge, and secure host capabilities.

| Field | Value |
|-------|-------|
| Group | `hath0r-opensource` |
| Control tower | [HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) |
| Operator CLI | `hath0r` |
| License | Apache 2.0 |

---

## Repositories

| Repository | Role | GitHub | Status |
|------------|------|--------|--------|
| **HATHOR Framework** | Canonical architecture, contracts, and documentation corpus | [Bayly-AI/HATH0R-Agentic-Framework](https://github.com/Bayly-AI/HATH0R-Agentic-Framework) | Design + contracts |
| **HATH0R CLI** | Control tower and operator CLI (`hath0r`) | [Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) | v0.1 — 4 read-only commands |
| **HATHOR POC** | React/TypeScript integration console | [Bayly-AI/HATH0R-Agentic-POC](https://github.com/Bayly-AI/HATH0R-Agentic-POC) | Scaffolding |

### How they relate

```
Framework (defines contracts)
    │
    ▼
CLI (implements contracts)
    │
    ▼
POC (consumes CLI through a narrow adapter)
```

The **Framework** owns the canonical design, JSON Schemas, and exit code contracts. The **CLI** implements those contracts as versioned commands. The **POC** consumes the CLI through a fixed-argv server adapter — it never reads the filesystem, spawns arbitrary processes, or accesses credentials directly.

A capability enters the POC only after:

1. the Framework defines its contract (schema, exit, security);
2. the CLI implements and tests that contract; and
3. the POC adds a named operation and consumer fixtures.

---

## Quick start

### Prerequisites

- macOS or Linux
- Git
- Python 3.10+
- Node.js 18+ (for POC development)

### Clone the group

```sh
mkdir -p ~/Development/OpenSource && cd ~/Development/OpenSource
git clone git@github.com:Bayly-AI/HATH0R-Agentic-Framework.git hath0r
git clone git@github.com:Bayly-AI/HATH0R-CLI.git HATH0R-CLI
git clone git@github.com:Bayly-AI/HATH0R-Agentic-POC.git hath0r-poc
```

### Install the CLI

```sh
cd HATH0R-CLI
python3 -m pip install -e ".[dev]"
hath0r --version
```

### Verify the suite

```sh
hath0r doctor
hath0r kb path
hath0r kb products
```

All three commands should pass. If `doctor` reports failures, fix the named checks before proceeding.

---

## Development lifecycle

### 1. Build order

Work flows in one direction: **Framework → CLI → POC**.

| Phase | Repository | What ships |
|-------|-----------|------------|
| 1 | Framework | JSON Schemas, exit code contract, cfg/ pointers, CI |
| 2 | CLI | `--output json` flag, structured output for all commands, tests, golden fixtures, CI |
| 3 | POC | React/Vite/TS scaffold, server adapter, API endpoints, UI pages, test pyramid, CI |

Phases 2 and 3 have parallelizable work (POC scaffold can start while CLI implements structured output), but the **critical path** requires CLI fixtures to exist before the POC normalizer can be tested against them.

### 2. Branch model

Every repository uses the same branch model:

```
local → development → testing → staging → master (Production)
```

**Canonical branches** (locked — never delete, never use as work branches):

- `development` — default branch, target for all feature work
- `testing` — receives promotions from `development`
- `staging` — receives promotions from `testing`
- `master` — production; receives promotions from `staging`

**Work branches** follow this naming convention:

```
<type>/<issue-number>-short-slug
```

Types: `feature`, `bugfix`, `enhancement`, `research`, `fix`, `chore`

Examples:
- `feature/21-cli-response-json-schemas`
- `fix/10-portable-group-root`
- `chore/23-ci-quality-gate`

### 3. Promotion path

Never skip stages:

```
development → testing → staging → master
```

Each stage requires a successful deploy and validation before the next promotion PR. CI enforces this via `.github/workflows/enforce-promotion-path.yml` in every repository.

---

## Roadmap & backlog

The initial build-out is tracked as **24 GitHub issues** across the three repos, ordered **Framework → CLI → POC**. Every issue is self-contained with acceptance criteria, references, dependencies, and branch conventions.

### Framework — contracts & docs (Phase 1)

- F1 [#20](https://github.com/Bayly-AI/HATH0R-Agentic-Framework/issues/20) — add `cfg/` member pointers
- F2 [#21](https://github.com/Bayly-AI/HATH0R-Agentic-Framework/issues/21) — publish `hath0r.cli.response/1` JSON Schemas
- F3 [#22](https://github.com/Bayly-AI/HATH0R-Agentic-Framework/issues/22) — publish exit code contract
- F4 [#23](https://github.com/Bayly-AI/HATH0R-Agentic-Framework/issues/23) — CI quality gate (schemas + docs)

### CLI — structured output & tests (Phase 2)

- C1 [#10](https://github.com/Bayly-AI/HATH0R-CLI/issues/10) — portable group-root discovery
- C2 [#11](https://github.com/Bayly-AI/HATH0R-CLI/issues/11) — `--output` flag + envelope (includes v0.2.0 bump)
- C3–C6 [#12](https://github.com/Bayly-AI/HATH0R-CLI/issues/12) [#13](https://github.com/Bayly-AI/HATH0R-CLI/issues/13) [#14](https://github.com/Bayly-AI/HATH0R-CLI/issues/14) [#15](https://github.com/Bayly-AI/HATH0R-CLI/issues/15) — structured JSON for `--version`, `doctor`, `kb path`, `kb products`
- C7 [#16](https://github.com/Bayly-AI/HATH0R-CLI/issues/16) — pytest suite
- C8 [#17](https://github.com/Bayly-AI/HATH0R-CLI/issues/17) — golden contract fixtures
- C9 [#18](https://github.com/Bayly-AI/HATH0R-CLI/issues/18) — CI (pytest + lint + typecheck)

### POC — React/TS integration console (Phase 3)

- P1 [#9](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/9) — scaffold
- P2 [#10](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/10), P3 [#11](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/11), P4 [#12](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/12) — runner, normalizer/redaction, shared schemas
- P5–P7 [#13](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/13) [#14](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/14) [#15](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/15) — API endpoints (health, capabilities, status, products)
- P8–P9 [#16](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/16) [#17](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/17) — React pages
- P10 [#18](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/18) — test pyramid; P11 [#19](https://github.com/Bayly-AI/HATH0R-Agentic-POC/issues/19) — CI

### Cross-repo clarifications

- **Catalog source-of-truth**: `hath0r kb products` reads the group KB hub `suite-products.yaml`, and derives `control_tower_product_id` from the `is_control_tower: true` product (the hub file uses `control_tower_path`, not `control_tower.product_id`).
- **Versioning**: structured output bumps the CLI to `0.2.0`; `__init__.py` and `pyproject.toml` stay in lockstep.
- **Docs stay in sync**: each C3–C6 ticket flips the relevant capability table row to `Implemented` so docs never diverge from source.

Track all open issues at once:

```sh
gh search issues --state open \
  --repo Bayly-AI/HATH0R-Agentic-Framework \
  --repo Bayly-AI/HATH0R-Agentic-POC \
  --repo Bayly-AI/HATH0R-CLI
```

---

## Contribution guidelines

### Before you write code

1. **Create a GitHub issue first.** No issue → no branch. The CI enforces this — PRs from branches without a valid issue number in their name will be rejected.

2. **Read the relevant docs.** Each repo has a `docs/INDEX.md` with a reading order. The Framework `docs/` tree is the canonical documentation corpus for the entire project.

3. **Check existing issues** across all three repos:
   ```sh
   gh search issues --state open \
     --repo Bayly-AI/HATH0R-Agentic-Framework \
     --repo Bayly-AI/HATH0R-Agentic-POC \
     --repo Bayly-AI/HATH0R-CLI
   ```

### Making changes

1. **Branch from `development`:**
   ```sh
   git checkout development
   git pull origin development
   git checkout -b feature/<issue-number>-short-slug
   ```

2. **Follow the repo's quality gate:**

   | Repo | Gate command |
   |------|-------------|
   | Framework | Schemas + docs front matter validate (CI) |
   | CLI | `python3 -m pytest && ruff check src/ tests/` |
   | POC | `npm run check` |

3. **Test your changes.** Every repo has a defined test strategy. CLI tests use `pytest` with Click's `CliRunner` and temporary directories. POC tests use Vitest (unit), integration tests with a fake CLI runner, and Playwright for e2e. No test should depend on a live external service or mutate the developer's real group KB.

4. **Open a PR targeting `development`:**
   ```sh
   gh pr create --base development
   ```

5. **Owner approval required.** `@somesayray` reviews all PRs via CODEOWNERS.

### What not to do

- Do not target PRs at `testing`, `staging`, or `master` — those are promotion-only targets.
- Do not merge canonical branches sideways (e.g., `testing` into `development`).
- Do not commit secrets, credentials, or unredacted environment values.
- Do not create `.ai/`, `.aegis/`, or `.infraOS/` directories — use `.hath0r/` only.
- Do not claim a Framework design-stage feature is implemented unless the CLI has a versioned command with tests.

---

## Architecture boundaries

### Product responsibilities

| Product | Owns | Must not become |
|---------|------|-----------------|
| Framework | Architecture, schemas, contracts, principles, docs | Claims about unshipped code |
| CLI | Control tower config, operator entry point, KB/catalog mediation | Browser backend or second knowledge store |
| POC | React UI, server adapter, fixtures, consumer evidence | Shell, policy authority, deployment control, or direct KB client |

### Trust boundaries

| Boundary | Trust level | Control |
|----------|-------------|---------|
| Browser → POC API | Untrusted | Fixed routes, schema validation, no command input |
| POC API → CLI | Semi-trusted app code | Named operation map, direct spawn (no shell), timeouts, redaction |
| CLI → filesystem | CLI authority | Fixed suite paths, documented env vars only |
| CLI → KB | Group-governed | Hub path through CLI; member stubs are pointers only |
| Framework docs → implementation | Design input | Source and tests required before capability activation |

### Capability states

Every integration point has one of these states:

| State | Meaning |
|-------|---------|
| **Implemented** | Verified in current source with tests |
| **Planned** | Defined in docs; implementation required |
| **Unavailable** | Not exposed by the current CLI |
| **Out of scope** | Deliberately excluded from initial integration |

---

## Project layout

```
OpenSource/
├── AGENTS.md                    # group agent rules
├── WARP.md                      # group policy
├── .hath0r/
│   └── knowledgebase/           # canonical group KB hub
│       └── catalogs/
│           └── suite-products.yaml
├── HATH0R-CLI/                  # control tower + operator CLI
│   ├── AGENTS.md
│   ├── cfg/                     # suite governance configs
│   ├── src/hath0r_cli/          # Python CLI source
│   ├── tests/                   # pytest suite
│   └── docs/                    # CLI-specific docs
├── hath0r/                      # Framework
│   ├── AGENTS.md
│   ├── cfg/                     # member pointers
│   ├── lib/schemas/             # JSON Schema contracts
│   ├── lib/contracts/           # exit code + other contracts
│   └── docs/                    # canonical documentation corpus
│       ├── architect/
│       ├── business/
│       ├── developers/
│       └── sales/
└── hath0r-poc/                  # POC integration console
    ├── AGENTS.md
    ├── cfg/                     # member pointers
    ├── src/app/                 # React client
    ├── src/server/              # TypeScript adapter (DMZ)
    ├── src/shared/              # shared contracts/schemas
    ├── test/                    # unit, integration, e2e, smoke
    └── docs/                    # POC-specific docs
```

### Key files

| File | Purpose |
|------|---------|
| `AGENTS.md` (group + each repo) | Agent rules, group identity, governance |
| `WARP.md` (group) | Group policy, promotion path, secrets |
| `cfg/suite.yaml` | Suite/group orientation per product |
| `cfg/knowledge-tower.yaml` | Control tower pointer, KB mode |
| `cfg/control-tower.yaml` | Tower identity (CLI only) |
| `cfg/products.yaml` | Product catalog (CLI only) |

---

## Credentials

Credentials live at `/Users/raybayly/Development/.credentials/<service>/.env`.

- Never commit secrets to any repository.
- Never print secrets in CLI output, logs, browser bundles, or test fixtures.
- The CLI mediates credential access — agents request capability through `hath0r`, not by scraping the filesystem.

---

## Documentation

The Framework repo owns the canonical documentation corpus at `hath0r/docs/`:

| Tree | Audience | Entry point |
|------|----------|-------------|
| `architect/` | Architects, agents | `docs/architect/INDEX.md` |
| `business/` | Business stakeholders | `docs/business/INDEX.md` |
| `developers/` | Developers, agents | `docs/developers/INDEX.md` |
| `sales/` | Sales | `docs/sales/INDEX.md` |

All docs follow the `hathor-doc@1` standard (HATHOR-CANON-001): YAML front matter with globally unique IDs, Diataxis classification, review metadata, and staleness tracking.

CLI and POC repos have product-specific docs under their own `docs/` trees, but defer to the Framework for architecture, requirements, and principles.

---

## License

All three repositories are licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
