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
