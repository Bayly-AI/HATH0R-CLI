# Playbook: Embedded ELT Troubleshooting and Diagnostics

> Artifact: **Playbook** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `elt-troubleshooting-playbook`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#431  
> Date: 2026-10-11

## 1. Diagnostic Decision Tree

```
[Issue Encountered]
   ├── Dirty / Out-of-Sync Projections ──► Pattern 1: Force Re-Projection
   ├── SQLite Database Locked (WAL)   ──► Pattern 2: Clear WAL Lock & Checkpoint
   ├── Bloated Cache Database Size    ──► Pattern 3: Execute Prune & Vacuum
   └── Corrupted Raw Payloads         ──► Pattern 4: Purge Staging Store & Re-Extract
```

---

## 2. Remediation Patterns

### Pattern 1: Out-of-Sync Projections
- **Symptom**: `hath0r elt status` shows non-zero counts under `Pending / Dirty Queue`, or search results in `hath0r kb search` omit newly added documentation.
- **Remediation**:
  ```bash
  hath0r elt transform --projection all --rebuild
  hath0r elt status
  ```

### Pattern 2: SQLite WAL Lock Contention
- **Symptom**: `OperationalError: database is locked`.
- **Root Cause**: Unclosed reader process or crash leaving uncheckpointed WAL log.
- **Remediation**:
  1. Check for running background processes:
     ```bash
     ps aux | grep hath0r
     ```
  2. Run explicit database vacuum/checkpoint:
     ```bash
     sqlite3 .hath0r/cache/ingest/raw_staging.sqlite "PRAGMA wal_checkpoint(TRUNCATE);"
     ```

### Pattern 3: Cache Storage Growth
- **Symptom**: `.hath0r/cache/ingest/raw_staging.sqlite` exceeds storage thresholds (>500MB).
- **Remediation**:
  ```bash
  # Prune records older than 30 days and execute VACUUM
  hath0r elt prune --retention 30
  ```

### Pattern 4: Staged Content Inconsistency
- **Symptom**: Checksum mismatch or unparseable corrupted payload.
- **Remediation**:
  ```bash
  rm -f .hath0r/cache/ingest/raw_staging.sqlite*
  hath0r elt extract --source docs/ --type docs
  hath0r elt transform --projection all
  ```
