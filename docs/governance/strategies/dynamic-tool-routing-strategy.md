# Strategy: Dynamic Tool Routing & Schema Pruning for Zero-Hallucination Agent Execution

> Canonical Strategy for Cognitive Tool Routing and Parameter Schema Compression  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #224

---

## 🎯 Executive Summary & Objectives

When orchestrating autonomous agents, passing dozens of unbounded tool schemas into model prompt windows creates severe cognitive overhead, token bloat, and parameter hallucinations (inverted arguments, missing required fields, or phantom tool calls).

This strategy establishes the **Dynamic Tool Routing & Schema Pruning Engine** in `HATH0R-CLI`. By coupling hybrid lexical (BM25) and semantic vector relevance ranking (`DynamicToolRouter`) with parameter schema compression (`SchemaPruner`), the CLI prunes irrelevant tool declarations per turn, reducing tool context token consumption by $\ge 50\%$ and cutting tool call hallucinations.

---

## 🏗️ Architecture: Hybrid Tool Selection & Pruning Pipeline

```text
                  Agent Intent / Task Description
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                   DynamicToolRouter                           │
├───────────────────────────────────────────────────────────────┤
│ 1. BM25 Lexical Keyword Ranking                               │
│ 2. Semantic Similarity Score (Cosine Vector Distance)         │
│ 3. Score Normalization & Top-K Tool Candidate Selection       │
└───────────────────────────────┬───────────────────────────────┘
                                │ Top-K Relevant Tools
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                      SchemaPruner                             │
├───────────────────────────────────────────────────────────────┤
│ • Strips redundant metadata & excessive docstrings            │
│ • Preserves strict parameter types, defaults & required fields│
│ • Compresses tool JSON footprint by up to 65%                 │
└───────────────────────────────┬───────────────────────────────┘
                                │ Compressed Active Tool Set
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                Agent Prompt Context Envelope                  │
└───────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Core Invariants

1. **Top-K Bounded Surface**: For any single agent step, no more than $K$ (default $K=5$) active tool declarations are injected into context.
2. **Contract Preservation**: Schema pruning MUST never remove required argument keys, data types, or enum validation constraints.
3. **Zero-Dependency Fallback**: The router must gracefully operate using token frequency matching if local vector embeddings or PyTorch runtime are unavailable.
4. **Deterministic Auditing**: All tool routing decisions and similarity scores are logged into the telemetry event stream.
