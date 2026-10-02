# Changelog

All notable changes to **HATH0R CLI** (`hath0r-cli`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.8.0] - 2026-10-02

### Added

- **AgentGraph Substrate & Dynamic Rule Architecture (`hath0r agentgraph`)** (#283, #287):
  - Added dynamic graph data structures (`GraphNode`, `GraphEdge`, `RuleNode`, `RoleNode`, `AgentGraphSubstrate`) under `src/hath0r_cli/agentgraph/`.
  - Implemented dynamic rule retrieval with deterministic caching and validation (`has_cycles()`, `detect_contradictions()`).
  - Implemented CLI surface: `hath0r agentgraph status`, `hath0r agentgraph validate`, `hath0r agentgraph sync`, `hath0r agentgraph rules`, `hath0r agentgraph roles`, and `hath0r agentgraph bot`.
- **Automated AgentGraph Bot (`AgentGraphBot`)** (#284, #288):
  - Added automated rule extraction and graph synchronization bot scanning repository markdown rules and code contexts.
  - Generates serializable graph snapshots at `.hath0r/agentgraph/snapshot.json`.
- **Workflow & Quality Gate Integrations** (#285, #289):
  - Integrated AgentGraph validation into clean-repo standard operating procedures, PR verification workflows, and SonarCloud quality gates.
- **Cross-Repo AgentGraph Migration Plane (`hath0r agentgraph migrate`)** (#286, #290):
  - Added `migrate_repo()` and `migrate_all()` supporting `--path` and `--all` across development workspaces.
  - Automatically converts markdown rules to AgentGraph snapshots and updates `AGENTS.md` with AgentGraph substrate pointers.

## [0.7.1] - 2026-10-02

### Fixed

- **Preflight Release Promotion Taxonomy** (#278, #279):
  - `hath0r preflight run` now accepts `release/<semver>` promotion branches when the branch version aligns with `VERSION`.
- **MCP Cloud Production Endpoint** (#279):
  - Updated default Hath0r MCP base URL across CLI server descriptors, connection registries, and documentation to `https://mcp.hath0r-cli.com`.
- **Typing & Linting Invariants**:
  - Resolved type annotations and schema repair return validations across cognitive engine modules for strict mypy compliance.

## [0.7.0] - 2026-10-02

### Added

- **MCP server and Claude Desktop connector (`hath0r mcp serve`)** (#267):
  - FastMCP stdio server exposing `hath0r_cli`, `hath0r_doctor`, `hath0r_optimize_taguchi`, `hath0r_finops_tokenizer_tax`, `hath0r_vision_parse_doc`, `hath0r_vision_ground`, and `hath0r_kb_search` tools.
  - `--transport`, `--install-claude`, and `--install-claude-only` flags to register the connector in Claude Desktop.
- **Claude plugin package** (#269, #271):
  - Plugin manifest at `.claude-plugin/plugin.json` with `.mcp.json`, plus a standalone lightweight `plugin/` package.
  - 1024x1024 listing icon and bundled MCP entrypoint at `scripts/mcp_server.py` resolved via `${CLAUDE_PLUGIN_ROOT}`.

### Changed

- **Bootstrap script relocated** from `bin/hath0r-bootstrap.sh` to `scripts/hath0r-bootstrap.sh`; the top-level `bin/` directory is removed so the plugin installs on Cowork and the Claude apps (#273).

### Fixed

- **Plugin validation file-size limit**: removed 32 MB pre-compiled `release/hath0r-darwin-*` binaries from git tracking; binaries now ship only as GitHub Release assets (#269).

## [0.6.0] - 2026-10-02

### Added

- **Taguchi Robust Parameter Optimization Engine (`hath0r optimize taguchi`)**:
  - Implemented `TaguchiBot` with built-in $L_4, L_8, L_9, L_{12}, L_{18}$ orthogonal array design matrix generation.
  - Added Signal-to-Noise Ratio (SNR) evaluation in decibels for `smaller_is_better`, `larger_is_better`, and `nominal_is_best` criteria.
  - Added Taguchi Quadratic Quality Loss Function ($L(y) = k(y-m)^2$) to quantify deviation costs.
  - Exposed via `hath0r optimize taguchi --array L9 -f <factor> --snr <values> --loss-k <k> --target-m <m> --measured-y <y>`.

- **FinOps Multilingual Tokenizer Tax Auditor (`hath0r finops tokenizer-tax`)**:
  - Implemented `TokenizerTaxBot` analyzing Unicode script distributions across 14 script families (Arabic, Devanagari, CJK, Cyrillic, Latin, etc.).
  - Computes script token expansion inflation ($\tau_{lang}$), baseline vs actual subword tokens, and incurred token penalties.
  - Calculates vocabulary serving VRAM overhead ($P_{vocab} = 2 \cdot V \cdot d_{model}$, e.g. 4.19 GB for 256k vocab).
  - Determines continuous visual patch budgets ($16\times 16$) for pixel-native vision models.
  - Exposed via `hath0r finops tokenizer-tax <text-or-path> [--vocab-size] [--hidden-dim] [--precision]`.

- **Pixel-Native 2D Document Parsing (`hath0r vision parse-doc --pixel-native`)**:
  - Added `--pixel-native` flag to `hath0r vision parse-doc` to parse tables and diagrams as continuous 2D visual patches without OCR licensing.
  - Added 2D spatial table cell matrix preservation (`table_id`, rows, columns, cell bounding boxes).

- **DOM-Independent Playwright UI Grounding (`hath0r vision ground --playwright`)**:
  - Added `--playwright` and `--action` options to `hath0r vision ground`.
  - Directly translates natural language element descriptions into Playwright-compliant coordinate steps (`coordinates: {"x": float, "y": float}`) bypassing brittle DOM selector trees.

## [0.5.1] - 2026-10-01

### Changed

- **Version Alignment & Ecosystem Promotion**: Canonical version bump to `0.5.1` across the suite promotion path (#257).
- **Cognitive Testing & UI Validation**: Updated test execution wrappers and preflight validation checks to support Playwright UI test automation and master test catalog synchronization.

## [0.5.0] - 2026-10-01

### Added

- **SuperCompress Query-Aware Prompt & Context Compression**: Integrated `SuperCompressBot` with REST API support, deterministic local semantic fallback, and `hath0r context compress -q <query> [-c <text> | -f <file>]` providing 30–60% token reduction (#246 / PR #248)
- **Dynamic MCP Server Manifest Generator & Sandbox Policy**: Built `DynamicMCPSecurity` with capability sandboxing, ephemeral manifest generation, and `hath0r mcp generate-manifest|check-policy` (#243 / PR #253)
- **Isolated Git Worktree Management**: Implemented `GitWorktreeBot` for subagent task isolation and concurrent branching with `hath0r branch worktree create|list|remove|prune` (#242 / PR #252)
- **Capability-Based WASM Micro-Runtime Sandboxing**: Integrated `WasmRuntimeBot` and Wasmtime execution engine with `hath0r wasm run|validate|audit` (#241 / PR #251)
- **DeepSeek-R1 CoT Reasoning Extraction & Local Adapters**: Enhanced `LocalModelBot` with `<think>` chain-of-thought parsing, token telemetry, and streaming inference with `hath0r local run --model deepseek-r1` (#240 / PR #250)
- **Instruction-Aware Neural Rerankers (Qwen3 & BGE-Reranker-v2-M3)**: Added instruction-steered cross-encoder reranking support to `KnowledgeIndexStore` and `hath0r kb search --instruction` (#239 / PR #249)
- **ColPali & ColQwen Vision Document Retrieval**: Integrated late-interaction vision embeddings for OCR-free multi-page document parsing and visual RAG via `hath0r vision parse-doc` (#238 / PR #247)
- **Kokoro-82M Ultra-Low Latency Neural TTS Engine**: Added `KokoroTTSEngine` with sub-50ms local voice synthesis and `hath0r voice speak --engine kokoro` (#237 / PR #245)
- **Tree-sitter AST Multi-Language Parser**: Added AST parser and syntax graph extractor for Python, TypeScript, Rust, and Go via `hath0r code parse|symbols|ast` (#236 / PR #244)

## [0.4.0] - 2026-10-01

### Added

- **Lazy Command Loading & Fast Startup**: Implemented `Hath0rLazyGroup` and deferred OpenTelemetry SDK initialization, reducing CLI cold-start latency from 663ms to 120ms ($5.5\times$ speedup) (#223 / PR #228)
- **Dynamic Tool Routing & Schema Pruning**: Token compression via `SchemaPruner` (up to 65% token savings) and BM25 tool relevance ranking via `DynamicToolRouter` (`hath0r mcp route`, `hath0r mcp prune`) (#224 / PR #229)
- **Vectorized Batch Tensor Operations & Dynamic Quantization**: Upgraded `PyTorchRuntime` with single-kernel 2D batch matrix multiplications (`torch.matmul`) and dynamic multi-precision support (`fp32`, `fp16` on MPS/CUDA, `int8` on CPU) with `hath0r vision rerank --precision` (#225 / PR #230)
- **Persistent SQLite FTS5 & Vector Index Cache**: Built `KnowledgeIndexStore` and `SQLiteIndexStore` (`.hath0r/cache/kb_index.sqlite`) with native SQLite FTS5 BM25 search ($<1\text{ms}$ query latency), incremental SHA-256 sync, and `hath0r kb index|search|status` (#226 / PR #231)
- **Programmatic Assertion & Schema Self-Repair Loops**: Added `SchemaRepairEngine` and `AssertionGuardrail` for automated in-flight JSON syntax sanitization, markdown fence removal, trailing comma repair, type coercion, and `hath0r quality repair` (#227 / PR #232)

## [0.3.0] - 2026-09-29

### Added

- Autonomous Background Voice Daemon Service: `hath0r voice service start|stop|status|restart` (#147)
- Intelligent Speech Sanitizer / Filter (`filter_speech_text`) stripping code blocks, diffs, tables, and markdown syntax for natural voice synthesis (#147)
- Registered `voice-service-daemon-bot` and `voice-daemon-service` workflow inside `cfg/factories/voice-converse-factory.yaml` (#147)
- Project closure report: suite multi-repo epics verification (`docs/governance/project-closure-suite-epics-2026-09-24.md`) (#112)
- Control-tower `docs/governance/SUITE_STANDARDS.md` index for member inheritance
- Suite standards: OpenTelemetry, OpenFeature, OpenObservation (#58–#60)
- CLI-first governance doc (#61); workflow documentation standard + inventory (#62)
- Docker group templates (hath0r/1-nation/bai) + workflow JSON (#63)
- Observability/feature-flag cfg stubs under `cfg/observability` and `cfg/feature-flags`
- Factory Manager bot CRUD: `hath0r factory create|update|delete` (#64)
- Preflight bot: `hath0r preflight run` (#67)
- Deploy test bot: `hath0r deploy pre|post` (#66)
- Quality gates bot: `hath0r quality check <pr>` with Sonar hard-stop aggregate (#68)
- Release bot: `hath0r release validate|notes|publish` (#69)
- Docs bots: `hath0r docs wiki` and `hath0r docs share` (#70, #71)
- `cfg/quality-gates.json`, `cfg/factories/quality-release-factory.yaml`, governance docs

## [0.2.0] — 2026-09-18

First public **OpenSource release train** for the operator CLI: structured machine JSON, packaging surfaces, GitHub Release assets, and PyPI publication.

### Highlights

- Package / binary version **0.2.0**
- Response envelope **`hath0r.cli.response/1`**
- PyPI: https://pypi.org/project/hath0r-cli/0.2.0/
- GitHub Release: https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.2.0
- Tracking epic: [#30](https://github.com/Bayly-AI/HATH0R-CLI/issues/30)

### Added

#### Machine interface

- Global `--output json|text|auto` and shared response envelope infrastructure
- Structured JSON for:
  - `hath0r --version`
  - `hath0r doctor`
  - `hath0r kb path`
  - `hath0r kb products`
- Portable group-root discovery (`HATH0R_GROUP_ROOT`, walk-up, soft fallback)
- Golden contract fixtures under `tests/contract/fixtures/`
- Pytest suite, mypy, ruff, and CI workflow on PRs to `development`

#### Release packaging (#30)

- **Fileset** builder: `scripts/build_fileset.py` → `hath0r-fileset-<ver>.tar.gz` + `.sha256`
- **Standalone binary** builder: `scripts/build_binary.py` (PyInstaller) → `hath0r-<ver>-<platform>` + `.sha256`
- **npm thin client**: `packaging/npm/hath0r-client` (`@bayly-ai/hath0r`) — fixed operations, `shell: false`, env allowlist
- **Release workflow**: `.github/workflows/release.yml` (tag `v*` and `workflow_dispatch`)
- Install / release guide: `docs/hathor-guide-047-install-and-release-20260918.md`
- PyPI Trusted Publisher documentation and GitHub environments `pypi` / `test-pypi`

### Changed

- `VERSION` lockstep with `pyproject.toml` at **0.2.0**
- README install section documents pipx/PyPI, editable monorepo, and packaging targets

### Fixed

- Release workflow OIDC `id-token: write` for PyPI publish path (#32)

### Release assets (`v0.2.0`)

| Asset | Notes |
|-------|--------|
| `hath0r_cli-0.2.0-py3-none-any.whl` / `.tar.gz` | Python package (also on PyPI) |
| `hath0r-0.2.0-linux-x64` (+ `.sha256`) | Standalone engine |
| `hath0r-0.2.0-darwin-arm64` (+ `.sha256`) | Standalone engine |
| `hath0r-fileset-0.2.0.tar.gz` (+ `.sha256`) | Drop-in OpenSource fileset |
| CLI JSON Schema snapshots | From Framework contracts pin |

### Install

```sh
pipx install hath0r-cli
# or
python3 -m pip install hath0r-cli==0.2.0
hath0r --version
hath0r --output json --version
```

### Related issues / PRs

- Packaging epic: #30 · PR #31
- OIDC publish fix: #32 · PR #33
- Trusted Publisher docs: #34 · PR #35
- Structured JSON / tests / CI: #10–#18

## [0.1.0] — 2026-09

Initial private/control-tower CLI surface (pre-structured-output):

- `hath0r doctor`, `hath0r kb path`, `hath0r kb products`, `hath0r --version`
- Control-tower cfg pointers and OpenSource group orientation
- Text-oriented operator UX (Rich)

[Unreleased]: https://github.com/Bayly-AI/HATH0R-CLI/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.2.0
[0.1.0]: https://github.com/Bayly-AI/HATH0R-CLI/commits/development
