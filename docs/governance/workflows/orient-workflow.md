# Workflow: Repository Orientation Workflow

> Canonical Workflow Definition · Hath0r Agentic Framework  
> Updated: 2026-10-12 · Issue: #275 / CLI #463

```mermaid
flowchart TD
    A["Operator / Agent Trigger: 'orient' (or 'hath0r orient')"] --> B["Step 1: Read Agents & Rules from AgentGraph"]
    B --> C["Step 2: Read Project README & Architecture Summary"]
    C --> D["Step 3: Scan Codebase AST & Application Structure"]
    D --> E["Step 4: Run Agent Metrics (Observability, Telemetry & PMAT)"]
    E --> F["Step 5: Run Agent Calibration (CCCD Parameter Loop)"]
    F --> G["Aggregate into hath0r-orient-report-v1 Schema Contract"]
    G --> H{"Terminal UI (TUI) Supported?"}
    H -- Yes --> I["Render Rich TUI Scorecards, Topology & Panels"]
    H -- No / Fallback --> J["Render Comprehensive GitHub-Flavored Markdown Report"]
    I & J --> K["Ingest Orientation Execution Node into AgentGraph ContextPlane"]
    K --> L["Return Orientation Report & Verdict to Operator"]
```

## Supported Intent Triggers
1. `"orient"`
2. `"hath0r orient"`
3. `"run orient"`
4. `"orient repository"`
5. `"orientation report"`
6. `"system orientation"`

## Six Core Execution Stages
1. **AgentGraph Retrieval**: Ingest and extract active agents, roles, permissions (RBAC), and governing rule policies from the unified quad-graph substrate (`.hath0r/agentgraph/snapshot.json`).
2. **Project README Analysis**: Ingest repository root `README.md` / `TECH_README.md` to extract high-level mission, ecosystem membership, tech stack, and primary capabilities.
3. **Application Code Scanning**: Perform AST and structural inspection across codebase directories (`src/`, `lib/`, `contracts/`, `tests/`), capturing language distributions, symbol outlines, and entry points.
4. **Agent Observability Metrics**: Execute `AgentMetricsBot` to extract latency quantiles (P50/P90/P99), total inference spend/tokens, histogram distributions, and PMAT hotspot risk indices ($R$).
5. **Agent Calibration**: Execute `CICCCDBot.calibrate()` to re-tune hyper-parameters (temperature, max_tokens, top_p, retry_count, guardrail_threshold) and verify freshness ($\le 24\text{h}$).
6. **Unified Findings Report**: Synthesize findings into dual-mode TUI / Markdown report and record audit node into AgentGraph `ContextPlane`.
