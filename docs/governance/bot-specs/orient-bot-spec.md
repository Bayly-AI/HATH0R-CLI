# Bot Specification: OrientBot

> Canonical Bot Specification · Hath0r Agentic Framework  
> Updated: 2026-10-12 · Issue: #275 / CLI #463

## 1. Role & Identity

- **Bot Name**: `orient-bot`
- **Class Name**: `OrientBot`
- **Subsystem**: `HATH0R-CLI` (`src/hath0r_cli/bots/orient_bot.py`)
- **CLI Command**: `hath0r orient`
- **Primary Function**: Autonomous micro-bot servicing operator and agent requests for repository orientation, multi-plane AgentGraph reading, README summarization, AST code scanning, agent metrics retrieval, and continuous calibration.

---

## 2. Supported Conversational Intents

1. `"orient"`
2. `"hath0r orient"`
3. `"run orient"`
4. `"orient repository"`
5. `"orientation report"`
6. `"system orientation"`
7. `"repo orient"`

---

## 3. Subsystem Integrations & RBAC

- `AgentGraphBot`: Reads Agent Roles, Rules & Invariants, and Topology from `.hath0r/agentgraph/snapshot.json`.
- `CodeParser`: Scans codebase files and parses AST symbols (classes, methods, functions).
- `AgentMetricsBot`: Pulls observability metrics, token histogram, and PMAT multi-dimensional stats.
- `CICCCDBot`: Evaluates and executes Continuous Calibration (CCCD) loop.
- `AgentGraphEngine`: Ingests `bot_execution:orient-bot:<timestamp>` node into `ContextPlane`.
