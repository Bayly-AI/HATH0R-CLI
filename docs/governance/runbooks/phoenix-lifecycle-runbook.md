# Arize Phoenix Lifecycle & Incident Response Runbook

> Artifact: **Runbook** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Date: 2026-10-05

## 1. System Overview

Arize Phoenix runs as a lightweight, persistent container with an embedded SQLite database (`/data/phoenix.db`) on dedicated volumes:
- `hath0r_phoenix_data` (Hath0r)
- `1n_phoenix_data` (1-Nation)
- `bai_phoenix_data` (BaylyAI)

---

## 2. Emergency Operations

### Scenario A: Phoenix Container Crashed / Unhealthy
1. **Check Container Logs**:
   ```bash
   docker logs --tail 100 HATH0R-Phoenix
   ```
2. **Restart via CLI**:
   ```bash
   hath0r phoenix down --group hath0r
   hath0r phoenix up --group hath0r
   ```
3. **Verify Edge Reverse Proxy**:
   ```bash
   curl -I http://localhost:38000/phoenix/
   ```

---

## 3. Maintenance & Persistence

### SQLite Database Backup
```bash
docker exec HATH0R-Phoenix sqlite3 /data/phoenix.db ".backup '/data/phoenix_backup_$(date +%Y%m%d).db'"
```

### Database Pruning (Older than 30 Days)
```bash
docker exec HATH0R-Phoenix /usr/bin/python3.13 -c "
import sqlite3
con = sqlite3.connect('/data/phoenix.db')
cur = con.cursor()
cur.execute(\"DELETE FROM spans WHERE start_time < datetime('now', '-30 days')\")
con.commit()
print('Pruning completed. Remaining spans:', cur.execute('SELECT count(*) FROM spans').fetchone()[0])
"
```

### Upgrading Phoenix Image
```bash
docker pull arizephoenix/phoenix:latest
hath0r phoenix down --group hath0r
hath0r phoenix up --group hath0r
```
