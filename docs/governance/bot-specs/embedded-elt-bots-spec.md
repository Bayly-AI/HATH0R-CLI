# Bot Specification: Embedded ELT Managing Bots

> Artifact: **Bot Specification** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `embedded-elt-bots-spec`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#428, Bayly-AI/HATH0R-CLI#429, Bayly-AI/HATH0R-CLI#431  
> Date: 2026-10-11

## 1. Bots Overview

The Embedded ELT subsystem is governed by two complementary managing bots:
1. `EmbeddedELTBot` (`src/hath0r_cli/bots/embedded_elt_bot.py`): Ingestion, adapter orchestration, and raw staging management.
2. `TransformationPipelineBot` (`src/hath0r_cli/bots/transformation_pipeline_bot.py`): Projection lifecycle, dirty queue tracking, and downstream index synchronization.

---

## 2. Bot Specifications

### `EmbeddedELTBot`
- **Role**: Source Ingestion & Raw Staging Authority
- **Inputs**: File system paths, MCP server endpoints, git commit objects, OTel traces.
- **Invariants**:
  - Never mutates or truncates source payloads at ingestion time.
  - Generates immutable SHA-256 content hashes for idempotency and deduplication.
  - Persists provenance metadata (`source_uri`, `source_type`, `mtime`, `ingested_at`).

### `TransformationPipelineBot`
- **Role**: Projection Engine & Materialization Authority
- **Inputs**: Staged raw records from `RawStagingStore`.
- **Projections**:
  - `fts5`: SQLite FTS5 lexical full-text index for `hath0r kb search`.
  - `colpali`: Multi-vector late-interaction visual page index for diagrams and layouts.
  - `agentgraph`: RDF/OWL knowledge nodes and rules DAG.
  - `finops`: Token tax calculations and CCCD calibration metrics.
- **Invariants**:
  - Fully idempotent; supports `--rebuild` directly from raw staging without external calls.
  - Updates atomic projection states (`synced`, `dirty`, `error`) per record.
