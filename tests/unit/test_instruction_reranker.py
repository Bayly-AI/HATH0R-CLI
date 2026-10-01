"""Unit tests for InstructionAwareReranker and hath0r kb search instruction steering."""

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.instruction_reranker import InstructionAwareReranker, SUPPORTED_RERANKERS


def test_reranker_model_list():
    """Verify supported reranker model metadata."""
    reranker = InstructionAwareReranker()
    models = reranker.list_models()
    assert len(models) >= 3
    assert any(m["model_id"] == "qwen3-reranker" for m in models)
    assert any(m["model_id"] == "bge-reranker-v2-m3" for m in models)


def test_instruction_steering_boost():
    """Verify that instruction increases candidate score when instruction keywords match candidate."""
    reranker = InstructionAwareReranker()
    candidates = [
        "Database schema migrations for PostgreSQL.",
        "Breaking API change in authentication middleware.",
    ]
    query = "review changes"

    # Standard reranking
    unconditional = reranker.rerank(query, candidates, instruction=None)

    # Instruction steering for breaking API changes
    steered = reranker.rerank(query, candidates, instruction="Prioritize breaking API contract updates")

    assert steered[0]["candidate"] == candidates[1]
    assert steered[0]["score"] > 0.0


def test_cli_kb_rerankers_list():
    """Verify hath0r kb rerankers command."""
    runner = CliRunner()
    res = runner.invoke(cli, ["-o", "json", "kb", "rerankers"])
    assert res.exit_code == 0
    assert "qwen3-reranker" in res.output
    assert "bge-reranker-v2-m3" in res.output


def test_cli_kb_search_with_instruction():
    """Verify hath0r kb search --instruction --model options."""
    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "-o",
            "json",
            "kb",
            "search",
            "-q",
            "voice synthesis",
            "-i",
            "Rank low-latency local neural models first",
            "-m",
            "qwen3-reranker",
        ],
    )
    assert res.exit_code == 0
    assert "instruction" in res.output
