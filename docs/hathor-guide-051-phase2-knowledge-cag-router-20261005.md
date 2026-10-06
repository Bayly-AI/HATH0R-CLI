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
