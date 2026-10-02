# HATH0R CLI — Technical Reference & Developer Guide

Operator and developer **control plane** for the HATHOR OpenSource agentic stack.

| Field | Value |
|-------|-------|
| Package | `hath0r-cli` |
| Binary | `hath0r` |
| Group | `hath0r-opensource` |
| Canonical KB | `$HATH0R_GROUP_ROOT/.hath0r/knowledgebase` (discovered; see Environment) |
| GitHub | [Bayly-AI/HATH0R-CLI](https://github.com/Bayly-AI/HATH0R-CLI) |

---

## Technical Overview & Installation

### Preferred Installation (Operators)

```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli
hath0r --version
hath0r doctor
```

### Developer Installation (Editable Monorepo)

```sh
cd /path/to/OpenSource/HATH0R-CLI   # or set HATH0R_GROUP_ROOT
python3 -m pip install -e ".[dev]"
hath0r --version
hath0r doctor
hath0r kb path
```

### Release Packaging Matrix

See [Install and release matrix](docs/hathor-guide-047-install-and-release-20260918.md) and issue [#30](https://github.com/Bayly-AI/HATH0R-CLI/issues/30).

```sh
make fileset
make wheel
# optional engine binary:
# pip install -e ".[release]" && make binary
```

---

## Command Reference (v0.8.0)

| Command | Purpose |
|---------|---------|
| `hath0r init` | Autonomous onboarding & alignment of any repository (Python, Node/TS, Go, Rust, polyglot) |
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r agentgraph` | Dynamic rule retrieval, role RBAC, topological cycle validation, and workspace migration |
| `hath0r optimize taguchi` | Generate orthogonal design matrices ($L_4..L_{18}$), calculate SNR and quadratic quality loss |
| `hath0r finops tokenizer-tax` | Audit Unicode script token inflation, serving VRAM parameters, and ViT patch economics |
| `hath0r vision parse-doc` | Parse structured layouts, diagrams, tables; supports `--pixel-native` continuous patch mode |
| `hath0r vision ground` | Visual UI element localization; supports `--playwright` DOM-independent action emission |
| `hath0r memory init` | Initialize local semantic working MemoryGraph (`.hath0r/memory/graph.json`) |
| `hath0r memory read <topic>` | Query semantic memory space topics (`core_rules`, `trigraph`, etc.) |
| `hath0r memory update <topic> <content>` | Update working memory space |
| `hath0r factory list` | List registered declarative automation factories |
| `hath0r factory run <id>` | Execute autonomous multi-bot workflows (e.g. `repo-onboard`, `git-branch-create`) |
| `hath0r kb path` | Print canonical group knowledgebase path |
| `hath0r kb search --instruction` | Neural reranked hybrid search using SQLite FTS5 BM25 + Qwen3/BGE |
| `hath0r voice service start\|stop\|status` | Manage background streaming voice synthesis daemon |
| `hath0r wasm run\|validate\|audit` | Capability-based sandboxed WASM micro-runtime execution |
| `hath0r clean-repo` | 13-step Clean Repos SOP execution and branch hygiene |
| `hath0r --version` | Package version |
| `hath0r planes` | ADR-003 domain status map (shipped/partial/planned) |
| `hath0r schema` | Bounded surface schema + forbidden legacy roots |
| `hath0r mcp sources list` | List 1-Nation federal vote-source inventory through MCP |

---

## Technical Specifications & Formulas

### 1. Taguchi Robust Parameter Design (`TaguchiBot`)
- **Orthogonal Array Reduction:** Evaluates high-dimensional parameter spaces ($L_4, L_8, L_9, L_{12}, L_{18}$) in balanced fractional factorial runs.
- **Signal-to-Noise Ratio (SNR):**
  - **Smaller-the-better (Latency, Loss, Memory):** $\eta = -10 \log_{10}\left(\frac{1}{n}\sum_{i=1}^{n} y_i^2\right)$
  - **Larger-the-better (Throughput, Accuracy):** $\eta = -10 \log_{10}\left(\frac{1}{n}\sum_{i=1}^{n} \frac{1}{y_i^2}\right)$
  - **Nominal-the-best (Target Alignment):** $\eta = 10 \log_{10}\left(\frac{\mu^2}{\sigma^2}\right)$
- **Taguchi Quality Loss Function:** $L(y) = k(y - m)^2$ where $m$ is the nominal target and $k$ is the sensitivity constant.

### 2. Tokenizer Tax Auditor (`TokenizerTaxBot`)
- **Script Token Inflation Factor:** $\tau_{lang} = \frac{\text{Tokens}(text)}{\text{Tokens}_{Latin}(text)}$.
- **Serving VRAM Memory Overhead:** $P_{vocab} = 2 \cdot V \cdot d_{model}$, consuming $4.19\text{ GB}$ of idle VRAM at $V = 256,000$ and $d_{model} = 4096$ in FP16 precision.
- **Continuous 2D Patch Budget:** $N_{patches} = \left\lceil\frac{H}{P}\right\rceil \times \left\lceil\frac{W}{P}\right\rceil$, eliminating token dictionary dependencies.

### 3. Pixel-Native 2D Document Understanding & UI Grounding
- **Spatial Matrix Preservation:** Extracts tabular structures as normalized bounding coordinates without intermediate OCR translation layers.
- **Playwright Grounding:** Generates DOM-independent coordinates:
  ```json
  {
    "action": "click",
    "coordinates": {"x": 450.0, "y": 320.0},
    "description": "Click on 'Submit Button' via visual pixel coordinates"
  }
  ```

---

## Architectural Map: Tri-Graph & Autonomous Execution

```text
                                  hath0r CLI
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
     Tri-Graph Substrate       Declarative Factories       Zero-Trust Execution
            │                          │                          │
   • KnowledgeGraph (AST/Lineage) • repo-onboarding-factory  • JEV Guard Mediation
   • ContextGraph (Agent Topology)• git-factory              • Preflight Verification
   • MemoryGraph (Working Memory) • voice-converse-factory   • Promotion Path Gate
```

---

## Environment & Configuration

| Variable | Default / Discovery | Purpose |
|----------|---------------------|---------|
| `HATH0R_GROUP_ROOT` | See discovery order below | OpenSource group root override |
| `HATH0R_KB_PATH` | `$HATH0R_GROUP_ROOT/.hath0r/knowledgebase` | Canonical KB override |

### Group Root Discovery Order

1. **`HATH0R_GROUP_ROOT`** — if set, use it (expanded/resolved).
2. **Walk-up from cwd** — find a directory with `AGENTS.md` containing `hath0r-opensource` and a `.hath0r/` directory.
3. **Soft fallback** — `~/Development/OpenSource` only if it looks like a real group root (same markers).
4. **Error** — clear message with remediation if nothing matches.

`HATH0R_KB_PATH` always wins for the knowledgebase path when set; otherwise KB is `$group_root/.hath0r/knowledgebase`.

---

## Architecture & Documentation

- [Documentation Index](docs/INDEX.md)
- [Current v0.2 Command Reference](docs/hathor-guide-042-current-command-reference-20260916.md)
- [CLI, Control-Tower, and POC Architecture](docs/hathor-arch-004-cli-control-tower-integration-20260916.md)
- [Proposed POC Machine Interface](docs/hathor-ts-005-poc-machine-interface-20260916.md)
- [POC Adapter Integration Guide](docs/hathor-guide-043-poc-adapter-integration-20260916.md)

---

## Group Membership & Policy Sync

This repo is a **canonical** member of OpenSource HATHOR alongside:

- Framework: `../hath0r` (`HATH0R-Agentic-Framework`)
- POC: `../hath0r-poc` (`HATH0R-Agentic-POC`)

See `AGENTS.md`, `cfg/suite.yaml`, and the group hub `../AGENTS.md`.

Canonical OpenSource group `AGENTS.md` / `WARP.md` live in `cfg/group/`. Materialize to the group root with `./scripts/sync-group-hub.sh` (see `cfg/group/README.md`).

---

## License

Apache License 2.0 — see `LICENSE`.
