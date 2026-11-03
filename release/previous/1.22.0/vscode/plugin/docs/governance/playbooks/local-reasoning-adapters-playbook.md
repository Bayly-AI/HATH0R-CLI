# Local Reasoning & Code Adapters Playbook

> Scope: **Developer & Operator Runbook for Local Offline Agent Inference**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001**  
> Issue: **#240**

---

## 1. Quick Start

### Running Local Reasoning with DeepSeek-R1
```bash
hath0r local reason "Analyze deadlock conditions in asyncio event loops" --show-cot
```

### Running Local Code Generation with Qwen2.5-Coder
```bash
hath0r local code "Write a Python context manager for temporary directory isolation"
```

### Listing Supported Local Model Templates
```bash
hath0r local models
```
