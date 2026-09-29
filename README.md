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

- 🛡️ **Zero-Trust Tool Execution (JEV Guard):** Cryptographically mediates mutating agent actions against security policies before execution.
- 🧠 **Dual-Layer Graph Substrate:** Native integration with **KnowledgeGraph** (static repository lineage and dependency tracking) and **ContextGraph** (dynamic runtime subagent delegation topologies).
- 🎙️ **Streaming Voice Interface:** Low-latency speculative routing and push-to-talk conversational agents with real-time feedback.
- ⚡ **Autonomous Factories & Micro-Bots:** Out-of-the-box workflows for automated git governance, PR lifecycle, Dependabot triage, and repo hygiene.
- 🌐 **MCP Server Federation:** Seamless orchestration across Model Context Protocol servers for enterprise knowledge access.

---

## Quick Install & Doctor

### Preferred Installation (Operators)
```sh
pipx install hath0r-cli
# or: python3 -m pip install hath0r-cli
hath0r --version
hath0r doctor
```

### Developer Installation (Editable Monorepo)
```sh
cd /path/to/OpenSource/HATH0R-CLI
python3 -m pip install -e ".[dev]"
hath0r --version
hath0r doctor
hath0r kb path
```

---

## Core Commands Overview

| Command | Purpose |
|---|---|
| `hath0r doctor` | Verify control tower, group root/AGENTS/WARP, member pointers, and KB hub |
| `hath0r kb path` | Print canonical group knowledgebase path |
| `hath0r factory list` | List available declarative automation factories |
| `hath0r factory run <id>` | Execute an autonomous multi-bot workflow |
| `hath0r playbook list` | List available coding, troubleshooting, and governance playbooks |
| `hath0r playbook read <name>` | Render interactive playbook in the terminal |
| `hath0r voice start` | Launch streaming voice engine and conversational interface |
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
