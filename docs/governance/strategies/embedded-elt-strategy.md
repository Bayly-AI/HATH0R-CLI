# Strategy: Embedded ELT Pipeline Architecture Strategy

> Artifact: **Strategy** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `embedded-elt-strategy`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#428, Bayly-AI/HATH0R-CLI#429, Bayly-AI/HATH0R-CLI#430, Bayly-AI/HATH0R-CLI#431  
> Date: 2026-10-11

## 1. Executive Summary

The **Embedded ELT (Extract, Load, Transform)** Subsystem establishes a decoupled, non-destructive data ingestion and projection architecture within the Hath0r CLI and cognitive agentic substrate.

Traditional ETL approaches transform and parse data upfront before discarding raw source texts, forcing expensive external re-extractions whenever embedding models, tokenizer vocabularies, or chunking strategies evolve. Embedded ELT resolves this by staging raw, unmodified source payloads (markdown documentation, MCP feeds, git history, telemetry spans) into a high-speed local SQLite cache, followed by independent, asynchronous projection transformations into downstream indices (FTS5, ColPali, AgentGraph, and FinOps telemetry).

```
┌────────────────────────────────────────────────────────┐
│                   Data Sources                         │
│  (Markdown Docs, MCP Feeds, Git Commits, OTel Spans)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
             [1. EXTRACT & LOAD: RawStagingStore]
               SQLite: .hath0r/cache/ingest/
               - SHA-256 Provenance & Deduplication
               - Preserves Raw Ground Truth
                           │
           ┌───────────────┼───────────────┬───────────────┐
           ▼               ▼               ▼               ▼
      [FTS5 Lexical]   [ColPali Visual] [AgentGraph]  [FinOps Telemetry]
     hath0r kb index   Late Interaction  Ontology &     Token Tax & SNR
                                          Rules DAG       Calibration
```

---

## 2. Strategic Objectives

- **Zero Re-Extraction Penalty**: Switching vector representations or chunking boundary rules requires only local re-transformation (`hath0r elt transform --rebuild`) rather than querying remote APIs or re-scanning external systems.
- **Strict Content Deduplication & Idempotency**: Content-addressed SHA-256 hashing guarantees that unchanged assets are ingested with zero duplication.
- **Embedded, Zero-Infra Footprint**: Operates entirely within local SQLite WAL databases without external daemon, broker, or container dependencies.
- **Multi-Consumer Synergy**: A single staged raw document simultaneously feeds lexical FTS5 indexes, visual ColPali vectors, and AgentGraph ontological triples.

---

## 3. Organizational Alignment

- **CR-CLI-ENTRY-001**: Feature implementation lives in `HATH0R-CLI` control tower and exports standardized CLI commands (`hath0r elt extract|load|transform|status|prune`).
- **CR-AGENTGRAPH-001**: Raw data serves as the ground truth feed for populating the AgentGraph knowledge and rules planes.
- **CR-CICCCD-001**: Raw telemetry trace ingestion enables offline calibration drift analysis and FinOps token consumption monitoring.
