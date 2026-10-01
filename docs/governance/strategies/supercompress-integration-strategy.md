# SuperCompress Integration Strategy: Query-Aware Prompt & RAG Context Compression

> Scope: **HATH0R CLI Context Management, Prompt Pruning & RAG Pipeline**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-RAG-RETRIEVAL-001 (No Context Stuffing) / CR-SUBSTRATE-001 (FinOps)**  
> Issue: **#246**

---

## 1. Executive Summary

Standard RAG architectures frequently suffer from "context stuffing": concatenating extensive documentation, codebase outlines, and chat histories into LLM prompt contexts. This increases token costs (FinOps overhead), elevates inference latency (TTFT), and degrades LLM reasoning due to "lost in the middle" attention dissipation.

`SuperCompress` provides deterministic, query-conditioned context compression. Rather than relying on non-deterministic generative summarization (which risks hallucinating technical constants or code semantics), SuperCompress analyzes token-level relevance against the active query, pruning irrelevant paragraphs, docstrings, and boilerplate with high entity and keyword recall ($1.0$).

This strategy details the integration of `SuperCompressBot` and the `hath0r context compress` CLI command into the HATH0R ecosystem.

---

## 2. Architecture & Pipeline

```
                 ┌──────────────────────────────────────────────┐
                 │    Unbounded Multi-Document RAG Context      │
                 │ (KB Matches, Session History, Code Outlines) │
                 └──────────────────────┬───────────────────────┘
                                        │
                                        ▼
                 ┌──────────────────────────────────────────────┐
                 │              User Query String               │
                 └──────────────────────┬───────────────────────┘
                                        │
                                        ▼
                 ┌──────────────────────────────────────────────┐
                 │               SuperCompressBot               │
                 │  - Token credentials resolution (.credentials)│
                 │  - Query-aware block relevance ranking       │
                 │  - Deterministic pruning & entity verifier   │
                 └──────────────────────┬───────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             │                                                     │
             ▼                                                     ▼
┌─────────────────────────────┐                       ┌─────────────────────────────┐
│    Compressed Context       │                       │       FinOps Telemetry      │
│  (30-60% Token Reduction)   │                       │ (Saved Tokens, Cost Delta,  │
│  (Zero Semantic Halluc.)    │                       │     Compression Latency)    │
└─────────────────────────────┘                       └─────────────────────────────┘
```

---

## 3. Credential Resolution Doctrine

Conforming to org-wide doctrine:
1. First check `/Users/raybayly/Development/.credentials/supercompress/.env` for `SUPER_COMPRESS_TOKEN` / `SUPERCOMPRESS_API_KEY`.
2. Fallback to process environment variables `SUPER_COMPRESS_TOKEN` or `SUPERCOMPRESS_API_KEY`.
3. If no credential is configured or in offline/mock mode: utilize local heuristic semantic compression with zero network dependency.

---

## 4. CLI Surface

- `hath0r context compress --query "<query>" --context "<text>"`
- `hath0r context compress --query "<query>" --file <path>`
- `hath0r context compress --query "<query>" --stdin`
