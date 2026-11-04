"""Unit tests for real embedding / rerank backends (issue #570). All network and model calls are mocked."""

from __future__ import annotations

import json
import sys
import types
from typing import Any, Dict, List

import pytest
from click.testing import CliRunner

from hath0r_cli import embeddings as emb_mod
from hath0r_cli import instruction_reranker as rr_mod
from hath0r_cli.bots.cag_rag_router import NeuralIntentClassifier
from hath0r_cli.cli import main as cli
from hath0r_cli.embeddings import (
    EmbeddingBackend,
    EmbeddingError,
    OllamaEmbeddingBackend,
    cosine_similarity,
    get_embedding_backend,
    reset_backend_cache,
    resolve_ollama_url,
)
from hath0r_cli.instruction_reranker import InstructionAwareReranker

# ---------------------------------------------------------------- helpers


class _FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


def _keyword_vector(text: str) -> List[float]:
    """Tiny deterministic 'trained' embedding: one axis per topic keyword."""
    axes = ["api", "database", "breaking", "pdf", "code", "run"]
    lower = text.lower()
    vec = [1.0 if a in lower else 0.0 for a in axes] + [0.1]
    return emb_mod._normalize(vec)


class _FakeTrainedBackend(EmbeddingBackend):
    name = "ollama"
    is_trained_model = True

    def __init__(self) -> None:
        super().__init__("fake-minilm")
        self.calls = 0

    def embed(self, texts):  # type: ignore[override]
        self.calls += 1
        return [_keyword_vector(t) for t in texts]


@pytest.fixture
def fake_trained(monkeypatch: pytest.MonkeyPatch) -> _FakeTrainedBackend:
    backend = _FakeTrainedBackend()
    monkeypatch.setattr(emb_mod, "get_embedding_backend", lambda *a, **k: backend)
    monkeypatch.setattr(emb_mod, "sentence_transformers_installed", lambda: False)
    return backend


# ---------------------------------------------------------------- embeddings module


def test_cosine_similarity_handles_zero_vectors() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, "http://127.0.0.1:11434"),
        ({"OLLAMA_HOST": "0.0.0.0:11434"}, "http://127.0.0.1:11434"),
        ({"HATH0R_OLLAMA_URL": "https://ollama.internal:443/"}, "https://ollama.internal:443"),
    ],
)
def test_resolve_ollama_url(monkeypatch: pytest.MonkeyPatch, env: Dict[str, str], expected: str) -> None:
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("HATH0R_OLLAMA_URL", raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert resolve_ollama_url() == expected


def test_resolve_ollama_url_rejects_non_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_OLLAMA_URL", "file:///etc/passwd")
    with pytest.raises(EmbeddingError):
        resolve_ollama_url()


def test_ollama_backend_embeds_and_normalizes(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: List[Dict[str, Any]] = []

    def fake_urlopen(req, timeout=None):
        if req.full_url.endswith("/api/tags"):
            return _FakeResponse({"models": [{"name": "all-minilm:latest"}]})
        seen.append(json.loads(req.data.decode("utf-8")))
        return _FakeResponse({"embeddings": [[3.0, 4.0], [0.0, 2.0]]})

    monkeypatch.setattr(emb_mod.urllib.request, "urlopen", fake_urlopen)
    backend = OllamaEmbeddingBackend(base_url="http://127.0.0.1:11434")
    assert backend.is_available()
    vectors = backend.embed(["a", "b"])
    assert vectors[0] == pytest.approx([0.6, 0.8])
    assert vectors[1] == pytest.approx([0.0, 1.0])
    assert seen == [{"model": "all-minilm", "input": ["a", "b"]}]
    assert backend.embed([]) == []


def test_ollama_backend_unavailable_when_model_missing_or_server_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        emb_mod.urllib.request, "urlopen", lambda req, timeout=None: _FakeResponse({"models": [{"name": "llama3"}]})
    )
    assert not OllamaEmbeddingBackend(base_url="http://x:1").is_available()

    def boom(req, timeout=None):
        raise emb_mod.urllib.error.URLError("refused")

    monkeypatch.setattr(emb_mod.urllib.request, "urlopen", boom)
    backend = OllamaEmbeddingBackend(base_url="http://x:1")
    assert not backend.is_available()
    with pytest.raises(EmbeddingError):
        backend.embed(["q"])


def test_ollama_backend_rejects_mismatched_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(emb_mod.urllib.request, "urlopen", lambda req, timeout=None: _FakeResponse({"embeddings": []}))
    with pytest.raises(EmbeddingError):
        OllamaEmbeddingBackend(base_url="http://x:1").embed(["q"])


def test_get_embedding_backend_auto_prefers_ollama_then_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_EMBED_BACKEND", "auto")
    monkeypatch.setattr(emb_mod, "sentence_transformers_installed", lambda: False)
    probes: List[int] = []

    def fake_available(self, timeout: float = 0.75) -> bool:
        probes.append(1)
        return True

    monkeypatch.setattr(OllamaEmbeddingBackend, "is_available", fake_available)
    reset_backend_cache()
    first = get_embedding_backend()
    second = get_embedding_backend()
    assert first is second
    assert first is not None and first.name == "ollama" and first.model == "all-minilm"
    assert len(probes) == 1


def test_get_embedding_backend_auto_falls_back_to_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_EMBED_BACKEND", "auto")
    monkeypatch.setattr(emb_mod, "sentence_transformers_installed", lambda: False)
    monkeypatch.setattr(OllamaEmbeddingBackend, "is_available", lambda self, timeout=0.75: False)
    reset_backend_cache()
    backend = get_embedding_backend()
    assert backend is not None and backend.name == "hash" and backend.is_trained_model is False
    assert len(backend.embed_one("check the repo")) == 384


def test_get_embedding_backend_uses_sentence_transformers_when_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeST:
        def __init__(self, name: str) -> None:
            self.name = name

        def encode(self, texts, normalize_embeddings=True):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(SentenceTransformer=FakeST))
    monkeypatch.setattr(emb_mod, "sentence_transformers_installed", lambda: True)
    reset_backend_cache()
    backend = get_embedding_backend("sentence-transformers")
    assert backend is not None and backend.name == "sentence-transformers"
    assert backend.embed(["x"]) == [[1.0, 0.0]]
    assert backend.embed([]) == []


def test_invalid_preference_is_treated_as_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(emb_mod, "sentence_transformers_installed", lambda: False)
    monkeypatch.setattr(OllamaEmbeddingBackend, "is_available", lambda self, timeout=0.75: False)
    reset_backend_cache()
    backend = get_embedding_backend("bogus")
    assert backend is not None and backend.name == "hash"


# ---------------------------------------------------------------- reranker


def test_heuristic_backend_is_deterministic_and_labelled() -> None:
    reranker = InstructionAwareReranker()
    a = reranker.rerank("api change", ["Database notes", "Breaking API change"])
    b = reranker.rerank("api change", ["Database notes", "Breaking API change"])
    assert a == b
    assert a[0]["candidate"] == "Breaking API change"
    assert {r["backend"] for r in a} == {"heuristic"}
    assert a[0]["model"] == "lexical-heuristic"
    assert reranker.last_backend == "heuristic"
    assert reranker.rerank("q", []) == []


def test_embedding_backend_reranks_semantically(monkeypatch: pytest.MonkeyPatch, fake_trained) -> None:
    monkeypatch.setenv("HATH0R_RERANK_BACKEND", "auto")
    reranker = InstructionAwareReranker()
    assert reranker.resolve_backend()["backend"] == "embedding"
    out = reranker.rerank(
        "review changes",
        ["Database schema migrations.", "Breaking API change in auth."],
        instruction="Prioritize breaking api updates",
    )
    assert out[0]["candidate"] == "Breaking API change in auth."
    assert out[0]["backend"] == "embedding"
    assert out[0]["model"] == "fake-minilm"
    assert 0.0 <= out[1]["score"] <= out[0]["score"] <= 1.0


def test_embedding_failure_degrades_to_heuristic(monkeypatch: pytest.MonkeyPatch, fake_trained) -> None:
    monkeypatch.setenv("HATH0R_RERANK_BACKEND", "embedding")

    def broken(texts):
        raise EmbeddingError("ollama stopped")

    monkeypatch.setattr(fake_trained, "embed", broken)
    reranker = InstructionAwareReranker()
    out = reranker.rerank("api", ["api docs", "other"])
    assert out[0]["backend"] == "heuristic"
    assert "ollama stopped" in (reranker.last_fallback_reason or "")


def test_cross_encoder_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded: List[str] = []
    pairs_seen: List[Any] = []

    class FakeCrossEncoder:
        def __init__(self, repo: str, max_length: int = 512) -> None:
            loaded.append(repo)

        def predict(self, pairs):
            pairs_seen.extend(pairs)
            return [3.0 if "API" in c else -3.0 for _, c in pairs]  # logits -> sigmoid

    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(CrossEncoder=FakeCrossEncoder))
    monkeypatch.setattr(emb_mod, "sentence_transformers_installed", lambda: True)
    monkeypatch.setattr(rr_mod, "_CROSS_ENCODER_CACHE", {})
    monkeypatch.setenv("HATH0R_RERANK_BACKEND", "cross-encoder")

    reranker = InstructionAwareReranker()
    out = reranker.rerank("q", ["DB notes", "Breaking API"], instruction="api first")
    reranker.rerank("q", ["x"])  # second call reuses the cached model
    assert loaded == ["tomaarsen/Qwen3-Reranker-0.6B-seq-cls"]
    assert out[0]["candidate"] == "Breaking API" and out[0]["backend"] == "cross-encoder"
    assert out[0]["model"] == "qwen3-reranker"
    assert out[0]["score"] == pytest.approx(0.9526, abs=1e-4)
    assert pairs_seen[0][0].startswith("<Instruct>: api first")


def test_cross_encoder_query_text_without_instruction_support() -> None:
    info = rr_mod.SUPPORTED_RERANKERS["minilm-l6-v2"]
    assert InstructionAwareReranker._query_text("q", "inst", info) == "inst q"
    assert InstructionAwareReranker._query_text("q", None, info) == "q"


def test_list_models_exposes_loadable_repo() -> None:
    models = {m["model_id"]: m for m in InstructionAwareReranker().list_models()}
    assert models["qwen3-reranker"]["cross_encoder_repo"] == "tomaarsen/Qwen3-Reranker-0.6B-seq-cls"
    assert models["minilm-l6-v2"]["cross_encoder_repo"] == "cross-encoder/ms-marco-MiniLM-L-6-v2"


# ---------------------------------------------------------------- classifier + CLI


def test_classifier_uses_trained_embeddings(fake_trained) -> None:
    clf = NeuralIntentClassifier()
    res = clf.classify("find the old career pdf")
    assert res.intent == "RAG"
    assert res.classifier == "NeuralIntentClassifier"
    assert res.embedding_backend == "ollama:fake-minilm"
    assert clf.embedding_backend == "ollama:fake-minilm"


def test_classifier_keyword_fallback_when_embedding_fails(monkeypatch: pytest.MonkeyPatch, fake_trained) -> None:
    clf = NeuralIntentClassifier()
    clf.classify("warm up")

    def broken(text):
        raise EmbeddingError("down")

    monkeypatch.setattr(fake_trained, "embed_one", broken)
    res = clf.classify("old pdf archive")
    assert res.classifier == "KeywordFallback" and res.intent == "RAG"


def test_classifier_without_any_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(emb_mod, "get_embedding_backend", lambda *a, **k: None)
    clf = NeuralIntentClassifier()
    assert clf.embedding_backend == "none"
    assert clf.classify("where is the code").classifier == "KeywordFallback"


def test_cli_rerankers_reports_active_backend() -> None:
    res = CliRunner().invoke(cli, ["-o", "json", "kb", "rerankers"])
    assert res.exit_code == 0
    data = json.loads(res.output)["data"]
    assert data["active_backend"]["backend"] == "heuristic"
    assert data["embedding"]["backend"] == "hash"
