# Procedure: Embedded ELT Pipeline Execution Procedure

> Artifact: **Procedure** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `elt-pipeline-procedure`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#430, Bayly-AI/HATH0R-CLI#431  
> Date: 2026-10-11

## 1. Scope & Purpose

This standard operating procedure defines the required steps for executing raw ingestion and downstream index synchronization across the Hath0r suite using the `hath0r elt` command surface.

---

## 2. Ingestion & Staging (Extract & Load)

### Step 1: Extract Documentation
Stage raw markdown files into the local SQLite staging store without schema parsing:
```bash
hath0r elt extract --source docs/ --type docs --glob "**/*.md"
```

### Step 2: Extract External MCP Data
Extract and stage samples from declared MCP data sources:
```bash
hath0r elt extract --source mcp://1-nation-mcp/federal_votes --type mcp
```

### Step 3: Extract Repository History & Churn
Stage recent git commits and churn statistics:
```bash
hath0r elt extract --source git --type git --commits 50
```

---

## 3. Projection Synchronization (Transform)

### Step 4: Synchronize Downstream Indices
Execute decoupled projection handlers:
```bash
# Incremental synchronization of all projections
hath0r elt transform --projection all

# Or synchronize a specific index
hath0r elt transform --projection fts5
```

### Step 5: Force Full Rebuild (When Models or Rules Change)
When an embedding model or graph schema is updated, re-transform from raw ground truth without re-fetching:
```bash
hath0r elt transform --projection all --rebuild
```

---

## 4. Operational Verification

### Step 6: Verify Staging & Queue Health
Inspect total staged records, database file size, and projection backlog:
```bash
hath0r elt status
```
Ensure that `Pending / Dirty Queue` is 0 across all projections.
