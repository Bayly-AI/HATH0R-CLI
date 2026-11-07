"""Pluggable text-embedding backends for Hath0r knowledge retrieval (RAG/CAG routing and reranking).

Owning bot: ``cag-rag-router-bot`` (``kb`` service, ``cfg/factories/mcp-kb-retrieval-workflow.yaml``).

Backends are resolved in this order when ``HATH0R_EMBED_BACKEND=auto`` (the default):

1. ``sentence-transformers`` -- local trained model, only when the optional package is installed.
2. ``ollama`` -- local Ollama server (``/api/embed``), default model ``all-minilm`` (384-d).
3. ``hash`` -- deterministic, dependency-free n-gram projection (``hath0r_engine`` ``DenseBiEncoder``).

The hash backend is not a trained model; it exists so the CLI works offline and tests stay hermetic.

Environment variables:

* ``HATH0R_EMBED_BACKEND``: ``auto`` | ``sentence-transformers`` | ``ollama`` | ``hash``
* ``HATH0R_EMBED_MODEL``: model name for the selected backend
* ``HATH0R_OLLAMA_URL`` (or ``OLLAMA_HOST``): Ollama base URL, default ``http://127.0.0.1:11434``
"""

from __future__ import annotations

import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "all-minilm"
DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BACKEND_ENV = "HATH0R_EMBED_BACKEND"
MODEL_ENV = "HATH0R_EMBED_MODEL"
VALID_BACKENDS = ("auto", "sentence-transformers", "ollama", "hash")

_BACKEND_CACHE: Dict[str, Optional["EmbeddingBackend"]] = {}


class EmbeddingError(RuntimeError):
    """Raised when an embedding backend cannot produce vectors."""


def _normalize(vec: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return [0.0] * len(vec)
    return [float(x) / norm for x in vec]


def cosine_similarity(v1: Sequence[float], v2: Sequence[float]) -> float:
    """Cosine similarity of two vectors (does not assume pre-normalized input)."""
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


class EmbeddingBackend(ABC):
    """Interface for an embedding provider returning L2-normalized vectors."""

    name: str = "base"
    is_trained_model: bool = True

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Embed a batch of texts."""

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]

    def describe(self) -> Dict[str, Any]:
        return {"backend": self.name, "model": self.model, "trained_model": self.is_trained_model}


class HashEmbeddingBackend(EmbeddingBackend):
    """Deterministic n-gram projection from ``hath0r_engine.gateway.cache.DenseBiEncoder`` (not a trained model)."""

    name = "hash"
    is_trained_model = False

    def __init__(self, model: str = "dense-bi-encoder-384") -> None:
        super().__init__(model)
        from hath0r_engine.gateway.cache import DenseBiEncoder  # raises ImportError when framework is absent

        self._encoder = DenseBiEncoder(dimensions=384)

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        return [list(self._encoder.encode(t)) for t in texts]


def resolve_ollama_url() -> str:
    """Return the Ollama base URL (http/https only)."""
    raw = os.environ.get("HATH0R_OLLAMA_URL") or os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA_URL
    raw = raw.strip().rstrip("/")
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise EmbeddingError(f"Unsupported Ollama URL: {raw!r}")
    host = parsed.netloc.replace("0.0.0.0", "127.0.0.1")
    return f"{parsed.scheme}://{host}"


class OllamaEmbeddingBackend(EmbeddingBackend):
    """Embeddings from a local Ollama server via ``POST /api/embed``."""

    name = "ollama"

    def __init__(self, model: str = DEFAULT_OLLAMA_MODEL, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        super().__init__(model)
        self.base_url = base_url or resolve_ollama_url()
        self.timeout = timeout

    def _request(self, path: str, payload: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(  # noqa: S310 - scheme restricted to http/https in resolve_ollama_url
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise EmbeddingError(f"Ollama request to {url} failed: {exc}") from exc

    def is_available(self, timeout: float = 0.75) -> bool:
        """True when the server answers and the configured model is pulled."""
        try:
            tags = self._request("/api/tags", timeout=timeout)
        except EmbeddingError:
            return False
        names = {str(m.get("name", "")) for m in tags.get("models", [])}
        return self.model in names or f"{self.model}:latest" in names

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        body = self._request("/api/embed", {"model": self.model, "input": list(texts)})
        vectors = body.get("embeddings") if isinstance(body, dict) else None
        if not vectors or len(vectors) != len(texts):
            raise EmbeddingError(f"Ollama returned no embeddings for model {self.model!r}")
        return [_normalize(v) for v in vectors]


class SentenceTransformerBackend(EmbeddingBackend):
    """Local embeddings via the optional ``sentence-transformers`` package."""

    name = "sentence-transformers"

    def __init__(self, model: str = DEFAULT_ST_MODEL) -> None:
        super().__init__(model)
        from sentence_transformers import SentenceTransformer  # optional dependency

        self._model = SentenceTransformer(model)

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(x) for x in v] for v in vectors]


def sentence_transformers_installed() -> bool:
    import importlib.util

    return importlib.util.find_spec("sentence_transformers") is not None


def _build(name: str, model: Optional[str]) -> Optional[EmbeddingBackend]:
    try:
        if name == "hash":
            return HashEmbeddingBackend()
        if name == "ollama":
            backend = OllamaEmbeddingBackend(model=model or DEFAULT_OLLAMA_MODEL)
            return backend if backend.is_available() else None
        if name == "sentence-transformers":
            if not sentence_transformers_installed():
                return None
            return SentenceTransformerBackend(model=model or DEFAULT_ST_MODEL)
    except Exception:  # noqa: BLE001 - any backend failure means "unavailable"; caller falls through
        return None
    return None


def get_embedding_backend(preference: Optional[str] = None, model: Optional[str] = None) -> Optional[EmbeddingBackend]:
    """Resolve (and cache) the embedding backend; ``None`` when nothing is available."""
    pref = (preference or os.environ.get(BACKEND_ENV) or "auto").strip().lower()
    if pref not in VALID_BACKENDS:
        pref = "auto"
    model = model or os.environ.get(MODEL_ENV) or None
    key = f"{pref}|{model or ''}"
    if key in _BACKEND_CACHE:
        return _BACKEND_CACHE[key]

    order = ["sentence-transformers", "ollama", "hash"] if pref == "auto" else [pref, "hash"]
    resolved: Optional[EmbeddingBackend] = None
    for name in order:
        # A model override only applies to the explicitly requested backend (or auto's trained backends).
        resolved = _build(name, model if name != "hash" else None)
        if resolved is not None:
            break
    _BACKEND_CACHE[key] = resolved
    return resolved


def reset_backend_cache() -> None:
    """Forget resolved backends (used by tests and after configuration changes)."""
    _BACKEND_CACHE.clear()
