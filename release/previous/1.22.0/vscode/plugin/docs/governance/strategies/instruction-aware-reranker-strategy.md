# Instruction-Aware Cross-Encoder Reranking Strategy (Qwen3 & BGE-M3)

> Scope: **Hath0r CLI KnowledgeBase & Neural Retrieval Subsystem**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-RAG-RETRIEVAL-001 / CR-SUBSTRATE-001**  
> Issue: **#239**

---

## 1. Executive Summary

Standard neural cross-encoders compute relevance scores between pairs $(q, d)$ without situational steering. In complex enterprise codebases and operational triage, an operator's retrieval intent depends heavily on instructions (e.g. *"Rank documents prioritizing breaking API changes"*, or *"Focus on Linux sandbox isolation rules"*).

This strategy integrates `Qwen3-Reranker-0.6B` and `BAAI/bge-reranker-v2-m3` instruction-aware cross-encoders into the `hath0r` CLI and hybrid knowledgebase retrieval engine.

---

## 2. Architecture & Formulation

Given an operator instruction $I$, a search query $Q$, and candidate passages $D_1, D_2, \dots, D_k$:

$$\text{Input Pair}_i = \left( \text{Instruction: } I \parallel \text{Query: } Q, \; D_i \right)$$

$$\text{Score}(I, Q, D_i) = \sigma\left( \text{CrossEncoder}(\text{Input Pair}_i) \right)$$

1. **Instruction-Steered Conditioning**: Modulates cross-attention weights according to operator directives.
2. **Supported SOTA Architectures**:
   - `qwen3-reranker` (`Qwen/Qwen3-Reranker-0.6B`): Ultra-fast, 0.6B parameters, instruction-tuned.
   - `bge-reranker-v2-m3` (`BAAI/bge-reranker-v2-m3`): Multilingual 100+ languages, 8192 context window.
   - `minilm-l6-v2`: Legacy lightweight fallback.

---

## 3. CLI Interfaces

- `hath0r kb search -q "<query>" --instruction "<prompt>" --model qwen3-reranker`
- `hath0r vision rerank --query "<query>" --instruction "<prompt>" --model bge-reranker-v2-m3`
