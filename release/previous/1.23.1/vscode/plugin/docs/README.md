<p align="center">
  <img src="lib/assets/images/hathor-logo-1.png" alt="HATHOR logo" width="280" />
</p>

# HATH0R CLI (v0.8.0)

**Autonomous Operator Control Plane & Enterprise Cognitive Engineering Gateway**

[![VS Code Marketplace](https://img.shields.io/badge/VS%20Marketplace-Hath0r-blue.svg)](https://marketplace.visualstudio.com/items?itemName=BaylyAI.hath0r-vscode)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v0.9.0-green.svg)](https://github.com/Bayly-AI/HATH0R-CLI/releases/tag/v0.9.0)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)

HATH0R CLI is the globally installed operator interface, runtime execution gateway, and control tower for the Enterprise Agentic Ecosystem. It bridges autonomous agents, developer tooling, security mediation, parameter optimization, FinOps tokenomics, and zero-tribal-memory project governance.

> **Technical Reference:** See [TECH_README.md](TECH_README.md) for in-depth architecture, subsystem maps, and developer specifications.

---

## Executive Scorecard: Strategic & Operational ROI

| Capability | Legacy Approach | HATH0R CLI v0.8.0 | Enterprise Value |
|---|---|---|---|
| **Dynamic Policy & Rule Graph** | Static markdown rules & tribal prompt engineering | **AgentGraph Substrate (`hath0r agentgraph`)** | **Zero cyclic dependencies & zero contradictions**; sub-millisecond dynamic rule & role resolution |
| **Hyperparameter & Agent Tuning** | Full-factorial brute-force grid search | **Taguchi Robust DoE (`hath0r optimize taguchi`)** | **96% reduction** in trial runs; maximizes Signal-to-Noise Ratio (SNR) |
| **Multilingual AI Inference** | 3–5x token penalty for non-Latin scripts | **FinOps Tokenizer Tax Audit (`hath0r finops tokenizer-tax`)** | Up to **65% inference cost savings**; flags VRAM waste before scaling |
| **Document Understanding** | Fragile OCR licenses & regex parsers | **Pixel-Native 2D Parsing (`hath0r vision parse-doc --pixel-native`)** | Eliminates OCR runtime costs; preserves 2D cell matrices directly |
| **Enterprise UI Automation** | Flaky XPath / DOM selectors breaking on CSS changes | **DOM-Independent Grounding (`hath0r vision ground --playwright`)** | Self-healing coordinate action generation for SAP, Salesforce, and Workday |
| **Repository Onboarding** | Days of manual setup & config tribalism | **Autonomous Scaffolding (`hath0r init`)** | **1-command** compliance with Tri-Graph ingestion, test harness, & governance |

---

- 🤖 **Agentic Substrate & KV Pre-Warming (`hath0r agent`):** Execute zero-token KV pre-warming gates, run topological multi-agent DAG execution trees, and serialize state via HAHP envelopes.
- 🕸️ **W3C OWL Reasoning & SPARQL Engine (`hath0r agentgraph`, `hath0r kb sparql`):** Export policy graphs to W3C Turtle RDF (`.ttl`), perform Description Logic OWL reasoner conflict validation, and query ontologies via SPARQL.
- ⚡ **Context-Augmented Generation & Smart Router (`hath0r context`, `hath0r kb smart-query`):** Full-context workspace prompt caching (CAG) for 100% recall and dynamic hybrid routing between CAG and RAG.
- 🛡️ **FinOps Token Tree Circuit Breaker (`hath0r finops budget`):** Enforce tree-level token ($0.25 / 50k token) budget caps on subagent recursion loops.
- 🎯 **Adversarial Evals & Antagonistic Review (`hath0r evals`, `hath0r pr review`):** Multi-agent consensus evaluator gates, Red-Team vs Blue-Team stress testing, and adversarial diff review with automated tech debt extraction.

---

## 🌐 Ecosystem Synergy: Hath0r CLI & Hath0r MCP Server

`HATH0R-CLI` and **`Hath0r-MCP`** (`Ray-MCP`) are engineered as a paired, high-performance agentic cognitive suite. While `HATH0R-CLI` acts as the command-line control plane and local developer gateway, `Hath0r-MCP` exposes Model Context Protocol semantic search tools, session memory management, and external knowledge ingestion endpoints.

### Flexible MCP Hosting Models

Users and enterprise operators can deploy `Hath0r-MCP` in two supported modes:

1. **Enterprise AWS-Hosted Edge Endpoint (Managed)**:
   - Connect directly to the production AWS CloudFront edge deployment (`pad.raybayly.net`).
   - Zero infrastructure setup required; ideal for desktop IDE integration (VS Code, Cursor, Antigravity) and remote agent tools.
   - Command: `hath0r mcp check --endpoint https://pad.raybayly.net/mcp/`

2. **Self-Hosted Local / Private Cloud (Autonomous)**:
   - Host your own isolated MCP server by cloning the [`somesayray/Ray-AI`](https://github.com/somesayray/Ray-AI) repository.
   - Run locally inside the `Ray-MCP` container group on Docker network `ray-net` (port `28083`).
   - Command: `hath0r docker up` or `docker compose up -d Ray-MCP`

---

## Quick Install & Quick Start

### Installation
```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli
hath0r --version
hath0r doctor
```

### 1. Execute Princeton KV Cache Pre-Warming & Multi-Agent DAG Execution
```sh
# Pre-warm prompt cache anchors to eliminate prefill latency spikes
hath0r agent prewarm --model claude-3-7-sonnet

# Execute topological multi-agent execution tree
hath0r agent dag --plan workflow_dag.json
```

### 2. Export W3C Turtle RDF Ontology & Run Description Logic Reasoning
```sh
# Export AgentGraph topology to W3C Turtle syntax
hath0r agentgraph export --format turtle

# Validate policy graph using Description Logic OWL reasoner
hath0r agentgraph validate --owl

# Execute SPARQL graph query over AgentGraph ontology
hath0r kb sparql "SELECT ?s ?label WHERE { ?s rdfs:label ?label }"
```

### 3. Pack Context-Augmented Generation (CAG) & Route Queries Dynamically
```sh
# Pack 100% full-context workspace files into prompt-cached CAG envelope
hath0r context pack --cag

# Route query dynamically between CAG (workspace) and RAG (documents)
hath0r kb smart-query "What rules govern CLI commands?"
```

### 4. Enforce Token Budget Circuit Breakers & Adversarial Evals
```sh
# Inspect subagent tree token & USD budget consumption
hath0r finops budget check --tree-id default_tree

# Evaluate multi-agent consensus gate across peer node outputs
hath0r evals consensus --threshold 0.70

# Run Antagonistic adversarial code review on git diffs
hath0r pr review --antagonistic

# Execute Red-Team vs Blue-Team adversarial stress testing
hath0r evals redteam --component agent_subsystem
```

---

## Core Command Reference

| Command | Purpose |
|---|---|
| `hath0r init` | Autonomous onboarding & alignment of any repository (Python, Node, Go, Rust) |
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r agent prewarm\|dag\|hahp\|status` | Subagent KV pre-warming, topological DAG runner, and HAHP handoff serialization |
| `hath0r agentgraph export\|validate` | W3C Turtle RDF (`.ttl`) exporter and Description Logic OWL reasoner policy validator |
| `hath0r kb sparql\|smart-query` | W3C SPARQL graph query engine and Hybrid CAG + RAG knowledge query router |
| `hath0r context pack --cag` | Pack full-context workspace files into prompt-cached CAG context envelopes |
| `hath0r finops budget check` | Subagent execution tree token & USD budget inspection and circuit breaker gate |
| `hath0r evals consensus\|redteam` | Multi-agent GAIN mesh consensus evaluator gate and Red-Team adversarial stress tester |
| `hath0r pr review --antagonistic` | Antagonistic diff review for swallowed exceptions & auto-created tech debt issues |
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
