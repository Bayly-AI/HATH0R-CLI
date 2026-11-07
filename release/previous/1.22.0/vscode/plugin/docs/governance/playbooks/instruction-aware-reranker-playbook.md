# Instruction-Aware Cross-Encoder Reranking Playbook

> Scope: **Developer & Operator Runbook for Instruction-Steered Retrieval**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-RAG-RETRIEVAL-001**  
> Issue: **#239**

---

## 1. Quick Start

### Hybrid Search with Qwen3-Reranker and Custom Instruction
```bash
hath0r kb search -q "voice engine" --instruction "Prioritize local neural models with low latency" --model qwen3-reranker
```

### Multilingual Reranking with BGE-M3
```bash
hath0r kb search -q "sandbox isolation" --instruction "Rank Linux namespaces and seccomp profiles highest" --model bge-reranker-v2-m3
```

---

## 2. Listing Supported Reranker Models
```bash
hath0r kb rerankers
```
