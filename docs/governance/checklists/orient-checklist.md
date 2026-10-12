# Checklist: Repository Orientation Verification Checklist

> Canonical Verification Checklist · Hath0r Agentic Framework  
> Updated: 2026-10-12 · Issue: #275 / CLI #463

This checklist must be satisfied before completing any repository orientation task.

- [ ] **Stage 1: AgentGraph Reading**
  - [ ] AgentGraph snapshot loaded or synchronized from `.hath0r/agentgraph/snapshot.json`.
  - [ ] Agent roles extracted with permitted and forbidden tool sets.
  - [ ] Governing rules extracted with priority and restricted actions.
- [ ] **Stage 2: Project README Reading**
  - [ ] Root `README.md` or `TECH_README.md` discovered and parsed.
  - [ ] Project title, mission statement, and core components summarized.
- [ ] **Stage 3: Application Code Scan**
  - [ ] Codebase files scanned across source folders (`src/`, `lib/`, `contracts/`).
  - [ ] Primary programming languages identified with file distribution.
  - [ ] Key AST symbols and entry points outlined.
- [ ] **Stage 4: Agent Metrics**
  - [ ] Observability latency quantiles (P50, P90, P99) extracted.
  - [ ] Token telemetry histogram distribution generated.
  - [ ] PMAT code churn, provability, complexity, and hotspot count evaluated.
- [ ] **Stage 5: Agent Calibration**
  - [ ] CCCD calibration freshness evaluated.
  - [ ] Calibration loop executed and updated parameters retrieved.
- [ ] **Stage 6: Findings Report & Ingestion**
  - [ ] Output rendered via dual-mode TUI or Markdown.
  - [ ] Report conforms to `contracts/hath0r-orient-report-v1.schema.json`.
  - [ ] Execution record ingested into AgentGraph ContextPlane.
