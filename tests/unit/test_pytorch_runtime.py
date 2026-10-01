"""Unit tests for PyTorch native acceleration runtime and tensor pipelines."""

import pytest
from hath0r_cli.bots.pytorch_runtime import (
    PyTorchRuntime,
    detect_optimal_device,
    is_pytorch_available,
)


def test_detect_optimal_device():
    """Verify device selection logic for CPU, MPS, and CUDA."""
    dev_auto = detect_optimal_device("auto")
    assert dev_auto in ("mps", "cuda", "cpu")

    dev_cpu = detect_optimal_device("cpu")
    assert dev_cpu == "cpu"


def test_pytorch_diagnostics():
    """Verify diagnostics dictionary structure."""
    runtime = PyTorchRuntime()
    diag = runtime.get_diagnostics()

    assert "available" in diag
    assert "device" in diag
    assert "mps_available" in diag
    assert "cuda_available" in diag
    assert "device_name" in diag
    assert "memory_allocated_mb" in diag


def test_multimodal_embedding_computation():
    """Verify 512-d and custom dimension embedding calculation."""
    runtime = PyTorchRuntime()
    sample_bytes = b"Hath0r PyTorch Acceleration Test Image Data"

    vec512 = runtime.compute_multimodal_embedding(sample_bytes, dim=512)
    assert len(vec512) == 512
    assert isinstance(vec512[0], float)

    vec128 = runtime.compute_multimodal_embedding(sample_bytes, dim=128)
    assert len(vec128) == 128


def test_neural_reranking():
    """Verify query-candidate cross-modal reranking."""
    runtime = PyTorchRuntime()
    query = "How to deploy Hath0r agent swarm with docker"
    candidates = [
        "Docker containerization workflow and docker compose swarm orchestration",
        "Cooking chocolate chip cookies in an oven",
        "Hath0r CLI branch validation and GitHub pull request rules",
    ]

    results = runtime.rerank_candidates(query, candidates)
    assert len(results) == 3
    assert results[0]["score"] >= results[1]["score"]
    assert "candidate" in results[0]
    assert "index" in results[0]


def test_ui_element_grounding():
    """Verify UI coordinate spatial grounding."""
    runtime = PyTorchRuntime()
    res = runtime.ground_ui_element(width=1920, height=1080, target="Deploy Cluster Button")

    assert res["found"] is True
    assert res["target"] == "Deploy Cluster Button"
    assert len(res["bounding_box"]) == 4
    assert 0 <= res["center_coordinates"]["x"] <= 1920
    assert 0 <= res["center_coordinates"]["y"] <= 1080
