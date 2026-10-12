# Procedure: Repository Orientation Operational Execution

> Canonical Operational Procedure · Hath0r Agentic Framework  
> Updated: 2026-10-12 · Issue: #275 / CLI #463

## 1. Scope & Prerequisites

This procedure outlines the deterministic 6-step operational procedure executed whenever an operator or agent triggers `"orient"`.

### Prerequisites
- Operator CLI installed (`hath0r`)
- Repository root containing `.hath0r/` metadata or `README.md`
- Active AgentGraph snapshot or capability to build one on demand

---

## 2. Step-by-Step Procedure

### Stage 1: Read Agents & Rules from AgentGraph
1. Locate `.hath0r/agentgraph/snapshot.json`. If missing, invoke `AgentGraphBot.sync()` to compile on the fly.
2. Filter nodes on `plane == "rules"` and `type == "agent_role"`:
   - Extract role name, ID, permitted tools, forbidden tools, and inherited roles.
3. Filter nodes on `plane == "rules"` and `type == "rule_policy"`:
   - Extract rule ID, label, priority, and restricted actions.
4. Tally active quad-graph topology statistics (Knowledge, Memory, Rules, Context).

### Stage 2: Read Project README
1. Locate `README.md` (fallback to `TECH_README.md`).
2. Extract project title, high-level description, ecosystem membership, and technology stack.
3. Extract core subsystem / component headings.

### Stage 3: Scan Code to Understand the Application
1. Scan source trees (`src/`, `lib/`, `contracts/`, `tests/`, etc.).
2. Count files per programming language extension.
3. Use structural AST parsing (`CodeParser`) to extract primary top-level classes, functions, and key entry points.
4. Formulate concise architectural topology summary.

### Stage 4: Run Agent Metrics
1. Invoke `AgentMetricsBot.generate_metrics_report()`.
2. Extract latency quantiles: P50, P90, P95, P99, mean, std dev.
3. Extract token ledger counts, inference spend USD, and token telemetry histogram.
4. Extract PMAT multi-dimensional stats: code churn, formal provability score, cyclomatic complexity, and top hotspot risk indices ($R$).

### Stage 5: Run Agent Calibration
1. Invoke `CICCCDBot.calibrate()`.
2. Verify parameter convergence and freshness.
3. Collect updated runtime hyperparameters:
   - `temperature`
   - `max_tokens`
   - `top_p`
   - `retry_count`
   - `guardrail_threshold`

### Stage 6: Render Report & Ingest into AgentGraph
1. Aggregate results into envelope conforming to `contracts/hath0r-orient-report-v1.schema.json`.
2. Check terminal interactivity:
   - If interactive terminal: render multi-panel rich TUI display.
   - If non-interactive / redirected / markdown requested: render GitHub-Flavored Markdown.
3. Ingest `bot_execution:orient-bot:<timestamp>` node into AgentGraph `ContextPlane`.
4. Output orientation report to operator.
