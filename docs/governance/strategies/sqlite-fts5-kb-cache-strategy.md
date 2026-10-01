# Strategy: Persistent SQLite FTS5 & Vector Index Cache for Tri-Graph KnowledgeBase

> Canonical Strategy for High-Performance KnowledgeBase Caching and Hybrid Retrieval  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #226

---

## 🎯 Executive Summary & Objectives

In Hath0r's Tri-Graph RAG doctrine, the KnowledgeGraph (`lib.graph` / `docs/` / `contracts/`) holds static architectural invariants, rule definitions, and playbooks. Scanning and parsing dozens of markdown files on every CLI invocation or subagent step introduces unnecessary file I/O latency ($100\text{ms}+$).

This strategy establishes the **Persistent SQLite FTS5 & Vector Index Cache** in `HATH0R-CLI`. Using an abstract `KnowledgeIndexStore` interface backed by a high-speed local `SQLiteIndexStore` (`.hath0r/cache/kb_index.sqlite`), the CLI gains:
1. **Sub-millisecond Full-Text Search**: Native SQLite `FTS5` virtual tables with BM25 lexical ranking and porter stemming.
2. **Incremental SHA-256 Hashing**: Only modified documents are re-indexed during sync cycles.
3. **Hybrid Tri-Graph Integration**: Combined lexical scoring and vector similarity for sub-agent memory and playbook lookup.
4. **Zero-Config Offline Portability**: Native Python standard library `sqlite3` without external cloud infrastructure dependencies.

---

## 🏗️ Architecture: SQLite FTS5 & Vector Cache

```text
       Markdown Documents (docs/, .hath0r/knowledgebase/)
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                     Incremental Sync Engine                   │
├───────────────────────────────────────────────────────────────┤
│ • Evaluates file modification time (mtime) and SHA-256 hash   │
│ • Skips unchanged documents in < 2ms                          │
└───────────────────────────────┬───────────────────────────────┘
                                │ Parsed Token Chunks
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                      SQLiteIndexStore                         │
│              (.hath0r/cache/kb_index.sqlite)                  │
├───────────────────────────────────────────────────────────────┤
│ 1. `kb_documents`: (path, sha256, title, category, mtime)     │
│ 2. `kb_fts`: FTS5 Virtual Table (bm25(kb_fts), porter stemmer)│
│ 3. `kb_vectors`: Serialized PyTorch multimodal embedding blobs│
└───────────────────────────────┬───────────────────────────────┘
                                │ Sub-millisecond Hybrid Hits
                                ▼
┌───────────────────────────────────────────────────────────────┐
│               Hath0r CLI & Subagent Context                   │
└───────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Core Invariants

1. **Sub-Millisecond Query Response**: All FTS5 searches MUST execute in $<5\text{ms}$ on standard hardware.
2. **Deterministic Cache Invalidation**: Cached entries must be automatically invalidated whenever a document's SHA-256 digest changes.
3. **Pluggable Interface**: All storage interactions must implement `KnowledgeIndexStore` to allow future cloud/fleet adapters without refactoring callers.
