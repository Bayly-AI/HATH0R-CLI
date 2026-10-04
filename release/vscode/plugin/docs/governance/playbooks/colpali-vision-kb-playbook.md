# ColPali Visual Document Retrieval Playbook

> Scope: **Developer & Operator Runbook for OCR-Free Visual Document Search**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-RAG-RETRIEVAL-001**  
> Issue: **#238**

---

## 1. Quick Start

### Building the Visual Knowledge Index
```bash
hath0r kb index --vision
```

### Searching Documents with Visual MaxSim Ranking
```bash
hath0r kb search --vision "Architecture diagram showing microVM sandboxes"
```

### Inspecting Visual Index Status
```bash
hath0r kb status
```

---

## 2. Structured JSON Output
```bash
hath0r --output json kb search --vision "database schema"
```

Sample output:
```json
{
  "query": "database schema",
  "mode": "colpali_maxsim",
  "results": [
    {
      "path": "docs/architecture/schema.png",
      "score": 0.942,
      "page": 1,
      "patch_count": 64,
      "match_type": "visual_late_interaction"
    }
  ]
}
```
