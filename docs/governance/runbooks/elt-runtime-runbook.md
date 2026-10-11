# Runbook: Embedded ELT Runtime Operations and Maintenance

> Artifact: **Runbook** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Identity: `elt-runtime-runbook`  
> Suite: `HATH0R-CLI` Control Tower  
> Issue Reference: Bayly-AI/HATH0R-CLI#431  
> Date: 2026-10-11

## 1. System Overview

The Embedded ELT runtime manages the lifecycle of staged raw payloads and asynchronous downstream projections. It provides zero-infrastructure data lake capabilities directly within the Hath0r CLI workspace.

---

## 2. Daily & Scheduled Maintenance

### Daily Synchronization Cadence
Include in automated CI/CD and developer workstation startup:
```bash
# Ingest updated documentation
hath0r elt extract --source docs/ --type docs

# Incrementally project to FTS5 and ColPali
hath0r elt transform --projection all
```

### Weekly Retention Pruning
Ensure historical staging records are pruned to maintain storage efficiency:
```bash
hath0r elt prune --retention 60
```

---

## 3. SLA & Metrics Targets

| Metric | Target | Warning Threshold | Critical Alert |
| :--- | :--- | :--- | :--- |
| **Ingestion Throughput** | > 200 docs/sec | < 50 docs/sec | Failure / Timeout |
| **FTS5 Projection Latency** | < 10ms / doc | > 50ms / doc | > 200ms / doc |
| **Queue Backlog** | 0 pending | > 100 pending | > 1,000 pending |
| **Database File Size** | < 100 MB | > 500 MB | > 1 GB |

---

## 4. Emergency Procedures

### Emergency Cache Flush & Re-Index
In the event of database corruption or major schema redesign:
```bash
# 1. Clear staging database
rm -rf .hath0r/cache/ingest/

# 2. Re-extract
hath0r elt extract --source docs/ --type docs

# 3. Synchronize projections
hath0r elt transform --projection all --rebuild
```
