# Playbook: PyTorch Vectorized Batching & Quantization Operations

> Operational Playbook for PyTorch Batch Reranking and Precision Management  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #225

---

## 📋 Overview

This playbook provides operational procedures for executing vectorized batch tensor reranking and configuring precision quantization in `HATH0R-CLI`.

---

## 🛠️ CLI Operations

### 1. Execute Batch Reranking with Precision Selection
To rerank candidates using half-precision (`fp16`) or `int8` quantization:

```bash
hath0r vision rerank \
  --query "Tri-Graph hybrid retrieval memory paging" \
  --candidates "KnowledgeGraph static rules;ContextGraph dynamic spans;MemoryGraph entities;Relational SQL database" \
  --device mps \
  --precision fp16
```

### 2. Batch Embedding Generation with Quantization
```bash
hath0r vision embed --image architecture.png --precision int8
```

---

## 💻 Programmatic Integration

```python
from hath0r_cli.bots.pytorch_runtime import PyTorchRuntime

runtime = PyTorchRuntime(device="mps", precision="fp16")
ranked = runtime.rerank_candidates(
    query="architecture diagrams",
    candidates=["docs/system_arch.png", "src/engine.py", "contracts/schema.json"],
)
```
