"""Instruction-Aware Reranker for Hath0r KnowledgeBase.

Owning bot: ``cag-rag-router-bot`` (``kb`` service).

Scoring backends (``HATH0R_RERANK_BACKEND``, default ``auto``):

* ``cross-encoder`` -- a real cross-encoder loaded with the optional ``sentence-transformers`` package
  (``pip install 'hath0r-cli[rerank]'``). Weights are downloaded from Hugging Face on first use.
* ``embedding`` -- bi-encoder cosine similarity using :mod:`hath0r_cli.embeddings` (for example Ollama
  ``all-minilm``). Only used when a trained embedding model is available.
* ``heuristic`` -- dependency-free lexical overlap with instruction boosting (no model).

``auto`` picks ``cross-encoder`` when ``sentence-transformers`` is installed, otherwise ``embedding`` when a
trained embedding model is reachable, otherwise ``heuristic``. Every result reports the backend that scored it.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

RERANK_BACKEND_ENV = "HATH0R_RERANK_BACKEND"
VALID_RERANK_BACKENDS = ("auto", "cross-encoder", "embedding", "heuristic")

_CROSS_ENCODER_CACHE: Dict[str, Any] = {}


@dataclass
class RerankerModelInfo:
    """Metadata describing a supported cross-encoder model."""

    model_id: str
    hf_repo: str
    dimensions: int
    context_length: int
    supports_instructions: bool
    description: str
    # Checkpoint loadable by ``sentence_transformers.CrossEncoder`` (may differ from the upstream repo).
    cross_encoder_repo: str = ""

    def loadable_repo(self) -> str:
        return self.cross_encoder_repo or self.hf_repo


SUPPORTED_RERANKERS: Dict[str, RerankerModelInfo] = {
    "qwen3-reranker": RerankerModelInfo(
        model_id="qwen3-reranker",
        hf_repo="Qwen/Qwen3-Reranker-0.6B",
        dimensions=1024,
        context_length=8192,
        supports_instructions=True,
        description="SOTA instruction-steered cross-encoder with 0.6B parameters.",
        # Upstream ships as a causal LM; this is its sequence-classification conversion for CrossEncoder.
        cross_encoder_repo="tomaarsen/Qwen3-Reranker-0.6B-seq-cls",
    ),
    "bge-reranker-v2-m3": RerankerModelInfo(
        model_id="bge-reranker-v2-m3",
        hf_repo="BAAI/bge-reranker-v2-m3",
        dimensions=1024,
        context_length=8192,
        supports_instructions=True,
        description="Multilingual 100+ language cross-encoder supporting instruction prefixes.",
    ),
    "minilm-l6-v2": RerankerModelInfo(
        model_id="minilm-l6-v2",
        hf_repo="cross-encoder/ms-marco-MiniLM-L-6-v2",
        dimensions=384,
        context_length=512,
        supports_instructions=False,
        description="Fast legacy cross-encoder baseline.",
    ),
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class InstructionAwareReranker:
    """Instruction-aware reranker with real model backends and a lexical fallback."""

    def __init__(self, default_model: str = "qwen3-reranker", backend: Optional[str] = None) -> None:
        self.default_model = default_model if default_model in SUPPORTED_RERANKERS else "qwen3-reranker"
        self.backend_preference = backend
        self.last_backend: Optional[str] = None
        self.last_fallback_reason: Optional[str] = None

    def list_models(self) -> List[Dict[str, Any]]:
        """List supported reranker models."""
        return [
            {
                "model_id": m.model_id,
                "hf_repo": m.hf_repo,
                "cross_encoder_repo": m.loadable_repo(),
                "context_length": m.context_length,
                "supports_instructions": m.supports_instructions,
                "description": m.description,
            }
            for m in SUPPORTED_RERANKERS.values()
        ]

    # ------------------------------------------------------------------ backend resolution
    def _preference(self) -> str:
        pref = (self.backend_preference or os.environ.get(RERANK_BACKEND_ENV) or "auto").strip().lower()
        return pref if pref in VALID_RERANK_BACKENDS else "auto"

    def resolve_backend(self) -> Dict[str, Any]:
        """Describe the backend ``rerank`` will try first (without loading cross-encoder weights)."""
        from hath0r_cli.embeddings import get_embedding_backend, sentence_transformers_installed

        pref = self._preference()
        if pref in ("auto", "cross-encoder") and sentence_transformers_installed():
            return {"backend": "cross-encoder", "preference": pref}
        if pref in ("auto", "cross-encoder", "embedding"):
            emb = get_embedding_backend()
            if emb is not None and emb.is_trained_model:
                return {"backend": "embedding", "preference": pref, "embedding": emb.describe()}
        return {"backend": "heuristic", "preference": pref}

    # ------------------------------------------------------------------ scorers
    @staticmethod
    def _query_text(query: str, instruction: Optional[str], info: RerankerModelInfo) -> str:
        if instruction and info.supports_instructions:
            return f"<Instruct>: {instruction}\n<Query>: {query}"
        if instruction:
            return f"{instruction} {query}"
        return query

    def _score_cross_encoder(
        self, query: str, candidates: List[str], instruction: Optional[str], info: RerankerModelInfo
    ) -> List[float]:
        repo = info.loadable_repo()
        model = _CROSS_ENCODER_CACHE.get(repo)
        if model is None:
            from sentence_transformers import CrossEncoder  # optional dependency

            model = CrossEncoder(repo, max_length=min(info.context_length, 2048))
            _CROSS_ENCODER_CACHE[repo] = model
        q_text = self._query_text(query, instruction, info)
        raw = model.predict([(q_text, c) for c in candidates])
        scores: List[float] = []
        for value in raw:
            v = float(value)
            scores.append(v if 0.0 <= v <= 1.0 else _sigmoid(v))
        return scores

    @staticmethod
    def _score_embedding(query: str, candidates: List[str], instruction: Optional[str]) -> List[float]:
        from hath0r_cli.embeddings import EmbeddingError, cosine_similarity, get_embedding_backend

        emb = get_embedding_backend()
        if emb is None or not emb.is_trained_model:
            raise EmbeddingError("No trained embedding model available")
        texts = [query] + ([instruction] if instruction else []) + list(candidates)
        vectors = emb.embed(texts)
        q_vec = vectors[0]
        i_vec = vectors[1] if instruction else None
        c_vecs = vectors[2:] if instruction else vectors[1:]
        scores: List[float] = []
        for c_vec in c_vecs:
            sim = cosine_similarity(q_vec, c_vec)
            if i_vec is not None:
                sim = 0.6 * sim + 0.4 * cosine_similarity(i_vec, c_vec)
            scores.append(max(0.0, min(1.0, sim)))
        return scores

    @staticmethod
    def _score_candidate(
        query: str,
        candidate: str,
        instruction: Optional[str] = None,
        model_id: str = "qwen3-reranker",  # noqa: ARG004 - kept for API compatibility
    ) -> float:
        """Lexical heuristic score in [0, 1]: query-term overlap plus instruction-term boost (no model)."""
        q_words = set(re.findall(r"\w+", query.lower()))
        c_words = set(re.findall(r"\w+", candidate.lower()))
        base_score = len(q_words & c_words) / max(1, len(q_words))

        inst_boost = 0.0
        if instruction:
            inst_words = set(re.findall(r"\w+", instruction.lower()))
            inst_boost = min(0.35, len(inst_words & c_words) * 0.1)

        raw_score = 0.4 * base_score + inst_boost + 0.35
        return round(1.0 / (1.0 + math.exp(-2.5 * (raw_score - 0.5))), 4)

    @staticmethod
    def _model_label(backend: str, target_model: str) -> str:
        """Name of the model that actually produced the scores."""
        if backend == "cross-encoder":
            return target_model
        if backend == "embedding":
            from hath0r_cli.embeddings import get_embedding_backend

            emb = get_embedding_backend()
            return emb.model if emb else "unknown-embedding"
        return "lexical-heuristic"

    # ------------------------------------------------------------------ public API
    def _score_with_fallback(
        self, query: str, candidates: List[str], instruction: Optional[str], info: RerankerModelInfo
    ) -> tuple[str, List[float]]:
        plan = self.resolve_backend()["backend"]
        order = {"cross-encoder": ["cross-encoder", "embedding"], "embedding": ["embedding"]}.get(plan, [])
        reasons: List[str] = []
        for backend in order:
            try:
                if backend == "cross-encoder":
                    return backend, self._score_cross_encoder(query, candidates, instruction, info)
                return backend, self._score_embedding(query, candidates, instruction)
            except Exception as exc:  # noqa: BLE001 - degrade to the next backend, record why
                reasons.append(f"{backend}: {exc}")
        self.last_fallback_reason = "; ".join(reasons) or None
        return "heuristic", [self._score_candidate(query, c, instruction) for c in candidates]

    def rerank(
        self,
        query: str,
        candidates: List[str],
        instruction: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Rerank candidate passages conditioned on optional instruction."""
        target_model = model_id or self.default_model
        if target_model not in SUPPORTED_RERANKERS:
            target_model = "qwen3-reranker"
        self.last_fallback_reason = None
        if not candidates:
            self.last_backend = None
            return []

        backend, scores = self._score_with_fallback(query, candidates, instruction, SUPPORTED_RERANKERS[target_model])
        self.last_backend = backend
        model_label = self._model_label(backend, target_model)

        scored = [
            {
                "index": idx,
                "candidate": cand,
                "score": round(score, 4),
                "model": model_label,
                "backend": backend,
                "instruction": instruction,
            }
            for idx, (cand, score) in enumerate(zip(candidates, scores))
        ]
        scored.sort(key=lambda x: (-x["score"], x["index"]))
        return scored
