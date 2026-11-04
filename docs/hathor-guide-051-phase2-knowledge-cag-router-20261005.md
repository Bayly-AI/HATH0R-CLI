# HATH0R-GUIDE-051: Phase 2 Knowledge Graph, CAG & Semantic Router Foundations

## Overview
This document serves as the canonical technical guide for **Phase 2: Knowledge Graph, CAG & Semantic Router Foundations** in `HATH0R-CLI` and the Ray Suite.

Phase 2 delivers five foundational knowledge and semantic router capabilities:
1. **W3C OWL/RDF Turtle Exporter** (`AgentGraphOWLExporter` / `hath0r agentgraph export --format turtle`)
2. **Description Logic OWL Reasoner** (`AgentGraphOWLReasoner` / `hath0r agentgraph validate --owl`)
3. **SPARQL Graph Query Engine** (`SPARQLEngine` / `hath0r kb sparql`)
4. **Context-Augmented Generation (CAG) Engine** (`CAGEngine` / `hath0r context pack --cag`)
5. **Hybrid CAG + RAG Knowledge Query Router** (`HybridCAGRAGRouter` / `hath0r kb smart-query`)

---

## Strategy & Architecture
- **Semantic OWL/RDF Ontology**: Maps AgentGraph planes (`rules`, `knowledge`, `context`, `memory`) and relations (`governs`, `informs`, `defines_role`) into an RDF graph using `http://hath0r.dev/ontology/v1#`.
- **Automated Description Logic Reasoning**: Uses RDFLib SPARQL graph reasoning to prove formal semantic consistency, detecting policy contradictions and cyclic governance rules.
- **CAG Prompt Caching**: Aggregates full workspace files, `AGENTS.md`, and AgentGraph topology into single-token prompt caching anchors (`cache_control: {"type": "ephemeral"}`), achieving 100% recall with zero chunking loss.
- **Hybrid Query Router**: Dynamic intent classifier routing code/workspace queries to CAG and deep document archival searches to RAG.

---

## Command Reference

### `hath0r agentgraph export`
Exports active AgentGraph topology to W3C Turtle RDF syntax or JSON.
```bash
hath0r agentgraph export --format turtle
```

### `hath0r agentgraph validate --owl`
Performs Description Logic OWL reasoner consistency checks.
```bash
hath0r agentgraph validate --owl
```

### `hath0r kb sparql`
Executes SPARQL graph queries over the AgentGraph OWL ontology.
```bash
hath0r kb sparql "SELECT ?s ?label WHERE { ?s rdfs:label ?label }"
```

### `hath0r context pack --cag`
Packs full workspace source code into a prompt-cached CAG context envelope.
```bash
hath0r context pack --cag
```

### `hath0r kb smart-query`
Routes agent queries dynamically to CAG or RAG engines.
```bash
hath0r kb smart-query "What rules govern CLI commands?"
```

---

## Verification & Testing
Run unit and integration tests:
```bash
pytest tests/test_phase2_knowledge_cag.py
```

---

## Retrieval Model Backends (v1.24.0, #570)

The router's intent classifier and the `kb search --hybrid` reranker use real models when available and say which
backend produced each score.

| Component | Backend order (`auto`) | Env override |
|---|---|---|
| Embeddings (`hath0r_cli.embeddings`) | `sentence-transformers` (if installed) → Ollama `all-minilm` → `hash` | `HATH0R_EMBED_BACKEND`, `HATH0R_EMBED_MODEL`, `HATH0R_OLLAMA_URL` |
| Reranker (`InstructionAwareReranker`) | `cross-encoder` (if `sentence-transformers` installed) → `embedding` (trained model only) → `heuristic` | `HATH0R_RERANK_BACKEND` |

`hash` and `heuristic` are deterministic, dependency-free fallbacks, not trained models.

### Operator runbook

```bash
# Zero-install path: local Ollama embeddings
ollama pull all-minilm
hath0r kb rerankers            # expect: Active rerank backend: embedding / Embedding backend: ollama:all-minilm
hath0r kb search -q "sign in users securely" --hybrid -o json   # data.rerank_backend == "embedding"

# Real cross-encoder (downloads weights from Hugging Face on first use)
pip install 'hath0r-cli[rerank]'
hath0r kb search -q "..." --hybrid -m qwen3-reranker   # tomaarsen/Qwen3-Reranker-0.6B-seq-cls
hath0r kb search -q "..." --hybrid -m minilm-l6-v2     # small/fast cross-encoder

# Force deterministic behaviour (CI, offline)
export HATH0R_EMBED_BACKEND=hash HATH0R_RERANK_BACKEND=heuristic
```

Rollback: set the two env vars above; no data migration is involved. Any backend error at query time degrades to
the next backend and is recorded in `InstructionAwareReranker.last_fallback_reason`.

Latency (local Ollama, Intel Mac): ~45 ms per classified query, ~80 ms to rerank 3 candidates after warm-up
(first call ~0.9 s while the model loads). The `hash` backend stays under 5 ms.
