# Runbook: Autonomous End-of-Task Daemon Operations

> Document Type: **Runbook** (`cr-workflow-doc-001`)  
> Product: **HATH0R-CLI** · Issue: #118 · SemVer: `minor`

## 1. Quick Operator Commands

### Run End of Task with Daemon Watch Mode
```bash
hath0r task finish --daemon --semver patch
```

### Dry Run Daemon Execution
```bash
hath0r task finish --daemon --dry-run
```

### Specify Custom Polling Interval and Timeout
```bash
hath0r task finish --daemon --poll-interval 15 --timeout 900
```

### Run Unit Tests for Daemon Bot
```bash
PYTHONPATH=. pytest tests/unit/test_daemon_bot.py
```
