"""Unit tests for SQLite FTS5 KnowledgeBase cache and hybrid search."""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.kb_index import SQLiteIndexStore


def test_sqlite_index_sync_and_search():
    """Verify document indexing, incremental sync, and FTS5 search."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        db_file = tmp_path / "cache" / "kb.sqlite"

        # Create sample markdown documents
        doc1 = docs_dir / "governance_doc.md"
        doc1.write_text("# Dynamic Tool Routing\nExplains BM25 tool candidate ranking and schema pruning.", encoding="utf-8")

        doc2 = docs_dir / "pytorch_runtime.md"
        doc2.write_text("# PyTorch Hardware Runtime\nAccelerates tensor batch matrix multiplication and quantization.", encoding="utf-8")

        store = SQLiteIndexStore(db_path=db_file)

        # 1. Initial sync
        stats1 = store.sync_directory(docs_dir)
        assert stats1["indexed"] == 2
        assert stats1["skipped"] == 0

        # 2. Incremental sync without changes
        stats2 = store.sync_directory(docs_dir)
        assert stats2["indexed"] == 0
        assert stats2["skipped"] == 2

        # 3. Full-text search
        hits = store.search_fts("tensor batch")
        assert len(hits) >= 1
        assert "PyTorch" in hits[0].title or "pytorch" in hits[0].path.lower()

        # 4. Hybrid search
        hybrid_hits = store.search_hybrid("dynamic tool routing", limit=2)
        assert len(hybrid_hits) >= 1
        assert "Dynamic Tool Routing" in hybrid_hits[0].title

        # 5. Status stats
        status = store.get_stats()
        assert status["total_documents"] == 2


def test_kb_cli_commands():
    """Verify kb index, search, and status CLI subcommands."""
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        sample_doc = tmp_path / "test_doc.md"
        sample_doc.write_text("# Branch Promotion Rules\nCanonical promotion order is local development testing staging master.", encoding="utf-8")

        # Test kb index
        res_index = runner.invoke(cli, ["-o", "text", "kb", "index", "--target-dir", str(tmp_path), "--rebuild"])
        assert res_index.exit_code == 0
        assert "SQLite FTS5 Index Synchronized" in res_index.output

        # Test kb search
        res_search = runner.invoke(cli, ["-o", "text", "kb", "search", "--query", "Branch Promotion", "--limit", "2"])
        assert res_search.exit_code == 0
        assert "results for" in res_search.output

        # Test kb status
        res_status = runner.invoke(cli, ["-o", "text", "kb", "status"])
        assert res_status.exit_code == 0
        assert "KnowledgeBase Cache Status" in res_status.output
