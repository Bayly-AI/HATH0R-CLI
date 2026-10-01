# Changelog

All notable changes to **HATH0R CLI** (`hath0r-cli`) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
