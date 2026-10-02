<p align="center">
  <img src="lib/assets/images/hathor-logo-1.png" alt="HATHOR logo" width="280" />
</p>

# HATH0R CLI (v0.7.0)

**Autonomous Operator Control Plane & Enterprise Cognitive Engineering Gateway**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.7.0-green.svg)](https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.7.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)

HATH0R CLI is the globally installed operator interface, runtime execution gateway, and control tower for the Enterprise Agentic Ecosystem. It bridges autonomous agents, developer tooling, security mediation, parameter optimization, FinOps tokenomics, and zero-tribal-memory project governance.

> **Technical Reference:** See [TECH_README.md](TECH_README.md) for in-depth architecture, subsystem maps, and developer specifications.

---

## Executive Scorecard: Strategic & Operational ROI

| Capability | Legacy Approach | HATH0R CLI v0.7.0 | Enterprise Value |
|---|---|---|---|
| **Hyperparameter & Agent Tuning** | Full-factorial brute-force grid search | **Taguchi Robust DoE (`hath0r optimize taguchi`)** | **96% reduction** in trial runs; maximizes Signal-to-Noise Ratio (SNR) |
| **Multilingual AI Inference** | 3–5x token penalty for non-Latin scripts | **FinOps Tokenizer Tax Audit (`hath0r finops tokenizer-tax`)** | Up to **65% inference cost savings**; flags VRAM waste before scaling |
| **Document Understanding** | Fragile OCR licenses & regex parsers | **Pixel-Native 2D Parsing (`hath0r vision parse-doc --pixel-native`)** | Eliminates OCR runtime costs; preserves 2D cell matrices directly |
| **Enterprise UI Automation** | Flaky XPath / DOM selectors breaking on CSS changes | **DOM-Independent Grounding (`hath0r vision ground --playwright`)** | Self-healing coordinate action generation for SAP, Salesforce, and Workday |
| **Repository Onboarding** | Days of manual setup & config tribalism | **Autonomous Scaffolding (`hath0r init`)** | **1-command** compliance with Tri-Graph ingestion, test harness, & governance |

---

## 🌟 Feature Overview

- 🚀 **Universal Repository Onboarding (`hath0r init`):** Turn ANY repository (Python, Node/TypeScript, Go, Rust, polyglot) into a compliant Hath0r-enabled project.
- 📐 **Taguchi Robust Parameter Optimization (`hath0r optimize taguchi`):** Generate orthogonal array design matrices ($L_4, L_8, L_9, L_{12}, L_{18}$), calculate Signal-to-Noise Ratios, and quantify quality loss ($L(y) = k(y-m)^2$).
- 💰 **Multilingual FinOps Tokenizer Tax Auditor (`hath0r finops tokenizer-tax`):** Audit subword token inflation across 14 Unicode script families, compute serving VRAM overhead ($P_{vocab} = 2 \cdot V \cdot d_{model}$), and benchmark continuous patch budgets.
- 👁️ **Pixel-Native 2D Document Understanding (`hath0r vision parse-doc`):** Parse complex layouts, spreadsheets, balance sheets, and technical diagrams directly from visual patches without OCR licensing.
- 🎭 **DOM-Independent Playwright Grounding (`hath0r vision ground --playwright`):** Locate interactive UI controls by visual appearance and generate Playwright-compliant automation steps.
- 🛡️ **Zero-Trust Tool Execution (JEV Guard):** Cryptographically mediates mutating agent actions against security policies before execution.
- 🧠 **Tri-Graph Cognitive Substrate:** Native integration with KnowledgeGraph (code lineage), ContextGraph (agent topologies), and MemoryGraph (temporal entities).
- 🎙️ **Streaming Voice Interface & Daemon:** Low-latency conversational agents with Kokoro-82M sub-50ms synthesis and background daemon execution.

---

## Quick Install & Quick Start

### Installation
```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli
hath0r --version
hath0r doctor
```

### 1. Optimize Agent Parameters with Taguchi Design of Experiments
```sh
# Generate L9 orthogonal array and calculate Signal-to-Noise Ratio (SNR)
hath0r optimize taguchi --array L9 -f temperature -f top_p -f retrieval_k \
  --snr 120.5,118.2,125.0 --criterion smaller
```

### 2. Audit Tokenizer Tax and Serving VRAM Overhead
```sh
# Audit token inflation and VRAM cost for multilingual enterprise queries
hath0r finops tokenizer-tax "Enterprise audit across English and العربية" --vocab-size 256000
```

### 3. Parse Financial & Architecture Documents Without OCR
```sh
hath0r vision parse-doc docs/invoices/q3_balance_sheet.png --pixel-native
```

### 4. Locate UI Elements & Emit Playwright Action Steps
```sh
hath0r vision ground screenshot.png --target "Approve Purchase Order" --playwright --action click
```

---

## Core Command Reference

| Command | Purpose |
|---|---|
| `hath0r init` | Autonomous onboarding & alignment of any repository (Python, Node, Go, Rust) |
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r optimize taguchi` | Generate orthogonal design matrices ($L_4..L_{18}$), calculate SNR and quadratic quality loss |
| `hath0r finops tokenizer-tax` | Audit Unicode script token inflation, serving VRAM parameters, and ViT patch economics |
| `hath0r vision parse-doc` | Parse structured layouts, diagrams, tables; supports `--pixel-native` continuous patch mode |
| `hath0r vision ground` | Visual UI element localization; supports `--playwright` DOM-independent action emission |
| `hath0r memory init\|read\|update` | Manage local semantic MemoryGraph (`.hath0r/memory/graph.json`) |
| `hath0r kb path\|search\|index` | Group knowledgebase integration and SQLite FTS5 neural hybrid search |
| `hath0r factory list\|run` | Declarative autonomous multi-bot workflows (e.g. `repo-onboarding-factory`) |
| `hath0r playbook list\|read` | Interactive engineering, troubleshooting, and governance playbooks |
| `hath0r clean-repo` | Standard Operating Procedure (SOP) repository cleanup and branch hygiene |

---

## Environment & Configuration

| Variable | Default / Discovery | Purpose |
|---|---|---|
| `HATH0R_GROUP_ROOT` | Discovered by walking up cwd | OpenSource group root override |
| `HATH0R_KB_PATH` | `$HATH0R_GROUP_ROOT/.hath0r/knowledgebase` | Canonical KB override |

---

## Documentation & Governance

- [Technical Reference Guide](TECH_README.md)
- [Documentation Index](docs/INDEX.md)
- [Governance Rules & Policies](docs/governance/)
- [Release Changelog](CHANGELOG.md)

---

## Group Membership

This repo is the **control tower** of OpenSource HATHOR alongside:
- Framework: `../hath0r` (`HATH0R-Agentic-Framework`)
- POC: `../hath0r-poc` (`HATH0R-Agentic-POC`)

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).
