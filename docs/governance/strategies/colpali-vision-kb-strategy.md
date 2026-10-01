# ColPali Late-Interaction Visual Document Retrieval Strategy

> Scope: **Hath0r CLI Knowledge Base & Multimodal Document Retrieval Subsystem**  
> Rule Reference: **CR-CLI-ENTRY-001 / CR-RAG-RETRIEVAL-001 / CR-SUBSTRATE-001**  
> Issue: **#238**

---

## 1. Executive Summary

Traditional Retrieval-Augmented Generation (RAG) relies on Optical Character Recognition (OCR) or naive text extractors (e.g. PyPDF) to convert documents into flat strings. In dense technical manuals, architecture blueprints, system architecture flowcharts, and financial tables, text extraction destroys structural geometry, layout hierarchy, and non-text visual elements.

`ColPali` (and `ColQwen`) introduces an **OCR-free visual document retrieval** paradigm. Instead of flattening documents into strings, ColPali feeds entire document pages into a vision-language backbone to generate multi-vector token embeddings per image patch, ranking candidate pages via token-level **MaxSim** late interaction.

This strategy establishes a PyTorch-vectorized ColPali indexing and retrieval engine in `hath0r_cli`.

---

## 2. Architecture & Design

```
                     ┌──────────────────────────────┐
                     │    Raw Document / PDF Page   │
                     │  (Images, Tables, Flowcharts)│
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │     ColPali Vision Embedder  │
                     │   (Multi-Vector Patch Tensor)│
                     │      Shape: [N_patches, D]   │
                     └──────────────┬───────────────┘
                                    │
     ┌──────────────────────────────┴──────────────────────────────┐
     │                                                             │
     ▼                                                             ▼
┌───────────────────────────┐                        ┌───────────────────────────┐
│     User Text Query       │                        │   Document Visual Store   │
│  "Explain Token Pruning"  │                        │  (.hath0r/cache/colpali)  │
└────────────┬──────────────┘                        └─────────────┬─────────────┘
             │                                                     │
             ▼                                                     ▼
     ┌─────────────────────────────────────────────────────────────────────┐
     │                     Vectorized MaxSim Scoring                       │
     │            Score = Sum_q max_p (Query_q · Patch_p)                  │
     └──────────────────────────────────┬──────────────────────────────────┘
                                        │
                                        ▼
                     ┌──────────────────────────────────────┐
                     │     Ranked Document Page Matches     │
                     └──────────────────────────────────────┘
```

1. **Multi-Vector Representation**:
   - Each page is represented as a collection of 128-dimensional embedding vectors corresponding to image patches and structural tokens.
2. **PyTorch Batch MaxSim Acceleration**:
   - Computes query token to image patch dot products:
     $$S(Q, D) = \sum_{i=1}^{|Q|} \max_{j=1}^{|D|} \left( \mathbf{q}_i \cdot \mathbf{d}_j^\top \right)$$
   - Accelerated via single-kernel matrix multiplication on Metal (MPS), CUDA, and CPU.
3. **Hybrid Tri-Graph Integration**:
   - Complements the SQLite FTS5 lexical index and vector dense index with a visual late-interaction graph.

---

## 3. CLI Interfaces

- `hath0r kb index --vision`: Indexes PDF pages and diagram images using multi-vector patch embeddings.
- `hath0r kb search --vision "<query>"`: Performs late-interaction MaxSim visual document search.
