# CICCCD Runbook

> Product: **HATH0R Control Tower** · Subsystem: **Governance & Calibration Engine**  
> Status: **Active Runbook** · Updated: 2026-10-04

---

## Operations & Incident Resolution

### Incident: Calibration File Corrupted or Missing

**Diagnostics**: `.hath0r/cccd_state.json` is missing or contains invalid JSON.

**Recovery Steps**:
1. Reset calibration state:
   ```bash
   rm -f .hath0r/cccd_state.json
   ```
2. Re-trigger full calibration:
   ```bash
   hath0r cicccd calibrate --iterations 3
   ```
3. Verify restored state:
   ```bash
   hath0r cicccd status
   ```

---

### Incident: Auto-Tune Daemon Deadlock / Memory Leak

**Diagnostics**: Background calibration process hanging or exceeding CPU limits.

**Recovery Steps**:
1. Check active processes and status:
   ```bash
   hath0r cicccd status
   ```
2. Disable auto-tune daemon mode:
   ```bash
   hath0r cicccd auto-tune --no-daemon
   ```
