"""Unit tests for PyTorch native acceleration runtime and batch tensor pipelines."""

from click.testing import CliRunner

from hath0r_cli.bots.pytorch_runtime import (
    PyTorchRuntime,
    detect_optimal_device,
)
from hath0r_cli.cli import main as cli


def test_detect_optimal_device():
    """Verify device selection logic for CPU, MPS, and CUDA."""
    dev_auto = detect_optimal_device("auto")
    assert dev_auto in ("mps", "cuda", "cpu")

    dev_cpu = detect_optimal_device("cpu")
    assert dev_cpu == "cpu"


def test_pytorch_diagnostics():
    """Verify diagnostics dictionary structure."""
    runtime = PyTorchRuntime(precision="fp16")
    diag = runtime.get_diagnostics()

    assert "available" in diag
    assert "device" in diag
    assert diag["precision"] == "fp16"
    assert "mps_available" in diag
    assert "cuda_available" in diag
    assert "device_name" in diag
    assert "memory_allocated_mb" in diag


def test_multimodal_embedding_computation():
    """Verify 512-d and custom dimension embedding calculation with precision modes."""
    runtime = PyTorchRuntime()
    sample_bytes = b"Hath0r PyTorch Acceleration Test Image Data"

    vec512 = runtime.compute_multimodal_embedding(sample_bytes, dim=512, precision="fp32")
    assert len(vec512) == 512
    assert isinstance(vec512[0], float)

    vec128_fp16 = runtime.compute_multimodal_embedding(sample_bytes, dim=128, precision="fp16")
    assert len(vec128_fp16) == 128

    vec128_int8 = runtime.compute_multimodal_embedding(sample_bytes, dim=128, precision="int8")
    assert len(vec128_int8) == 128


def test_vectorized_batch_reranking():
    """Verify query-candidate cross-modal 2D batch reranking across precision modes."""
    query = "How to deploy Hath0r agent swarm with docker"
    candidates = [
        "Docker containerization workflow and docker compose swarm orchestration",
        "Cooking chocolate chip cookies in an oven",
        "Hath0r CLI branch validation and GitHub pull request rules",
    ]

    for prec in ["fp32", "fp16", "int8"]:
        runtime = PyTorchRuntime(precision=prec)
        results = runtime.rerank_candidates(query, candidates, precision=prec)
        assert len(results) == 3
        assert results[0]["score"] >= results[1]["score"]
        assert "candidate" in results[0]
        assert "index" in results[0]

    # Verify empty candidates list handling
    assert runtime.rerank_candidates(query, []) == []


def test_ui_element_grounding():
    """Verify UI coordinate spatial grounding."""
    runtime = PyTorchRuntime()
    res = runtime.ground_ui_element(width=1920, height=1080, target="Deploy Cluster Button")

    assert res["found"] is True
    assert res["target"] == "Deploy Cluster Button"
    assert len(res["bounding_box"]) == 4
    assert 0 <= res["center_coordinates"]["x"] <= 1920
    assert 0 <= res["center_coordinates"]["y"] <= 1080


def test_vision_rerank_cli_with_precision():
    """Verify CLI execution of vision rerank with precision option."""
    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "-o",
            "text",
            "vision",
            "rerank",
            "-q",
            "Tri-Graph hybrid retrieval",
            "-c",
            "KnowledgeGraph static rules",
            "-c",
            "Relational database tables",
            "--precision",
            "fp16",
        ],
    )
    assert res.exit_code == 0
    assert "Neural Reranking Completed" in res.output
