<p align="center">
  <img src="lib/assets/images/hathor-logo-1.png" alt="HATHOR logo" width="280" />
</p>

# HATH0R CLI

**Operator & Developer Control Plane for the HATHOR Agentic Ecosystem**

HATH0R CLI is the globally installed operator interface, runtime execution gateway, and control tower for the Enterprise Agentic Platform. It defines the shared boundary between autonomous AI agents, developer tooling, security mediation, and project governance.

> **Technical Reference:** See [TECH_README.md](TECH_README.md) for in-depth architecture, subsystem maps, and developer specifications.

---

## 🌟 Sales & Feature Overview

The HATH0R CLI empowers engineering teams and autonomous agents to build, verify, and operate enterprise software with zero tribal memory and hardened governance:

- 🚀 **Universal Repository Onboarding (`hath0r init`):** Turn ANY repository (Python, Node/TypeScript, Go, Rust, polyglot) into a compliant Hath0r-enabled project with layout scaffolding, documentation refactoring, test harness provisioning, and Tri-Graph ingestion.
- 🛡️ **Zero-Trust Tool Execution (JEV Guard):** Cryptographically mediates mutating agent actions against security policies before execution.
- 🧠 **Tri-Graph Cognitive Substrate:** Native integration with:
  - **KnowledgeGraph:** Static codebase lineage, AST indexing, and documentation dependencies.
  - **ContextGraph:** Dynamic runtime multi-agent delegation topologies and audit logs.
  - **MemoryGraph:** Local semantic working memory space (`.hath0r/memory/graph.json`) persisting rules, architectural decisions, and playbooks.
- 🎙️ **Streaming Voice Interface & Background Daemon:** Low-latency conversational agents with real-time feedback and autonomous background daemon execution.
- ⚡ **Autonomous Factories & Micro-Bots:** Out-of-the-box declarative workflows (`repo-onboarding-factory`, `git-factory`, `voice-converse-factory`, `factory-manager-factory`) for automated git governance, PR lifecycle, test promotion, and repo hygiene.
- 🌐 **MCP Server Federation:** Seamless orchestration across Model Context Protocol servers for enterprise knowledge access.

---

## Quick Install & Quick Start

### Preferred Installation (Operators & Developers)
```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli
hath0r --version
hath0r doctor
```

### Initialize Any Repository
```sh
cd /path/to/my-project
hath0r init
```

---

## Core Commands Overview

| Command | Purpose |
|---|---|
| `hath0r init` | Autonomous onboarding & alignment of any repository (Python, Node, Go, Rust) |
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r memory init` | Initialize local semantic MemoryGraph (`.hath0r/memory/graph.json`) |
| `hath0r memory read <topic>` | Query semantic working memory (e.g. `core_rules`, `trigraph`) |
| `hath0r kb path` | Print canonical group knowledgebase path |
| `hath0r factory list` | List available declarative automation factories |
| `hath0r factory run <id>` | Execute an autonomous multi-bot workflow |
| `hath0r playbook list` | List available coding, troubleshooting, and governance playbooks |
| `hath0r playbook read <name>` | Render interactive playbook in the terminal |
| `hath0r voice service start` | Launch autonomous background voice daemon service |
| `hath0r context spread` | Distribute localized hyper-context (`AGENTS.md`, `rules.md`, `canonical.md`) |

> For comprehensive command lists and options, see [Current Command Reference](docs/hathor-guide-042-current-command-reference-20260916.md) and [TECH_README.md](TECH_README.md).

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
