# SuperCompress Query-Aware Context Compression Playbook

> Scope: **Developer & Operator Runbook for Context Pruning & FinOps Optimization**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-RAG-RETRIEVAL-001**  
> Issue: **#246**

---

## 1. Quick Start

### Compressing Context from String
```bash
hath0r context compress -q "How is voice synthesis configured?" -c "Long mixed document text..."
```

### Compressing Context from File
```bash
hath0r context compress -q "error handling logic" -f docs/architecture/runtime.md
```

### Pipeline Compression via Stdin
```bash
cat large_log.txt | hath0r context compress -q "database connection timeout"
```

---

## 2. Structured JSON Output
```bash
hath0r --output json context compress -q "voice models" -c "..."
```

Sample output:
```json
{
  "query": "voice models",
  "original_tokens": 340,
  "compressed_tokens": 160,
  "savings_pct": 52.94,
  "latency_ms": 48.2,
  "compressed_text": "...",
  "verifier": {
    "quality_score": 1.0,
    "entity_recall": 1.0,
    "keyword_recall": 1.0
  }
}
```
