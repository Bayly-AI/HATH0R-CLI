# WASM Micro-Runtime Sandboxing Playbook

> Scope: **Developer & Operator Runbook for WASM Agent Tool Execution**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-SUBSTRATE-001**  
> Issue: **#241**

---

## 1. Quick Start

### Executing an Isolated WASM Tool
```bash
hath0r wasm run tool.wasm --allow-read ./data --memory-mb 32
```

### Validating a WASM Binary Header & Capability Requirements
```bash
hath0r wasm validate module.wasm
```

### Inspecting Host WASM Runtime Engine
```bash
hath0r wasm status
```
