# Playbook: SQLite FTS5 & Vector KB Cache Operations

> Operational Playbook for KnowledgeBase Indexing, Search, and Cache Management  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #226

---

## 📋 Overview

This playbook describes how to index, query, and maintain the SQLite FTS5 KnowledgeBase cache using `HATH0R-CLI`.

---

## 🛠️ CLI Operations

### 1. Incremental Indexing of KnowledgeBase
To index or re-index the documentation corpus and knowledgebase:

```bash
hath0r kb index
```

To force a full rebuild:

```bash
hath0r kb index --rebuild
```

### 2. High-Speed Full-Text Search (FTS5)
To search the indexed knowledgebase using BM25 ranking:

```bash
hath0r kb search --query "dynamic tool routing"
```

### 3. Check Cache Status & Diagnostics
```bash
hath0r kb status
```

---

## 💻 Programmatic Usage

```python
from hath0r_cli.kb_index import SQLiteIndexStore

store = SQLiteIndexStore()
store.sync_directory("docs/")

results = store.search_fts("branch promotion path", limit=5)
for r in results:
    print(r.title, r.path, r.score)
```
