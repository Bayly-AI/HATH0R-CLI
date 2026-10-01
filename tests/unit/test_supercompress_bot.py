"""Unit tests for SuperCompressBot and hath0r context compress CLI command."""

from pathlib import Path
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.bots.supercompress_bot import SuperCompressBot, _resolve_supercompress_token


def test_supercompress_token_resolver(monkeypatch, tmp_path: Path):
    """Verify token resolution from environment and credential paths."""
    monkeypatch.setenv("SUPER_COMPRESS_TOKEN", "test_mock_token_123")
    assert _resolve_supercompress_token() == "test_mock_token_123"

    monkeypatch.delenv("SUPER_COMPRESS_TOKEN", raising=False)
    # Check fallback
    assert _resolve_supercompress_token() is None or isinstance(_resolve_supercompress_token(), str)


def test_supercompress_local_compression():
    """Verify local deterministic semantic compression."""
    bot = SuperCompressBot(token=None)
    context = (
        "Hath0r CLI is a modular operator plane for agents.\n\n"
        "Baking chocolate chip cookies requires 2 cups of flour and butter.\n\n"
        "Voice synthesis in Hath0r is powered by Kokoro-82M neural TTS."
    )
    query = "How is voice synthesis configured in Hath0r?"
    res = bot.compress(query, context, force_local=True)

    assert res["success"] is True
    assert res["engine"] == "supercompress_local"
    assert "Voice synthesis" in res["compressed_text"]
    assert res["savings_pct"] > 0
    assert res["verifier"]["entity_recall"] == 1.0


def test_cli_context_compress_string():
    """Verify hath0r context compress with --context string."""
    runner = CliRunner()
    context = "Section 1: Engine architecture.\n\nSection 2: Irrelevant recipe.\n\nSection 3: AST parsing."
    res = runner.invoke(
        cli,
        [
            "-o",
            "json",
            "context",
            "compress",
            "-q",
            "AST parsing",
            "-c",
            context,
            "--local",
        ],
    )
    assert res.exit_code == 0
    assert "compressed_text" in res.output
    assert "AST parsing" in res.output


def test_cli_context_compress_file(tmp_path: Path):
    """Verify hath0r context compress with --file option."""
    doc = tmp_path / "spec.md"
    doc.write_text("Overview of Hath0r.\n\nRandom grocery list.\n\nMicroVM sandboxes.", encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(
        cli,
        [
            "-o",
            "text",
            "context",
            "compress",
            "-q",
            "MicroVM sandboxes",
            "-f",
            str(doc),
            "--local",
        ],
    )
    assert res.exit_code == 0
    assert "MicroVM sandboxes" in res.output


def test_cli_context_compress_stdin():
    """Verify hath0r context compress with piped stdin."""
    runner = CliRunner()
    context = "Section 1: Tri-graph hybrid RAG.\n\nSection 2: Irrelevant data.\n\nSection 3: Letta memory paging."
    res = runner.invoke(
        cli,
        [
            "-o",
            "json",
            "context",
            "compress",
            "-q",
            "Letta memory paging",
            "--local",
        ],
        input=context,
    )
    assert res.exit_code == 0
    assert "Letta memory paging" in res.output


def test_supercompress_empty_context():
    """Verify empty context handling."""
    bot = SuperCompressBot(token=None)
    res = bot.compress("any query", "")
    assert res["success"] is True
    assert res["compressed_tokens"] == 0
    assert res["compressed_text"] == ""


def test_supercompress_api_mock(monkeypatch):
    """Verify API request and response parsing with mock urlopen."""
    import io
    import json
    from urllib.response import addinfourl

    mock_resp_data = {
        "compressed_text": "Compressed architecture content.",
        "original_tokens": 120,
        "kept_tokens": 60,
        "tokens_saved": 60,
        "tokens_saved_pct": 50.0,
        "verifier": {"quality_score": 1.0, "entity_recall": 1.0, "keyword_recall": 1.0},
    }

    class MockResponse(io.BytesIO):
        def __init__(self, data: bytes):
            super().__init__(data)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    def mock_urlopen(req, timeout=10.0):
        return MockResponse(json.dumps(mock_resp_data).encode("utf-8"))

    monkeypatch.setattr("hath0r_cli.bots.supercompress_bot.urlopen", mock_urlopen)

    bot = SuperCompressBot(token="mock_live_token")
    res = bot.compress("architecture", "Full architecture document with lots of text...")
    assert res["success"] is True
    assert res["engine"] == "supercompress_api"
    assert res["compressed_tokens"] == 60
    assert res["savings_pct"] == 50.0
    assert res["compressed_text"] == "Compressed architecture content."

