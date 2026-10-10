"""Unit tests for ColPali visual document indexer and kb CLI commands."""

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.colpali_engine import ColPaliEngine


def test_colpali_engine_indexing_and_maxsim(tmp_path: Path):
    """Verify document indexing and MaxSim search scoring."""
    sample_doc1 = tmp_path / "diagram1.png"
    sample_doc1.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"demo_patch_data_123")

    sample_doc2 = tmp_path / "spec_table.png"
    sample_doc2.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"spec_table_bytes_456")

    engine = ColPaliEngine(cache_dir=tmp_path / "cache")
    page1 = engine.index_document(sample_doc1, page_number=1)
    page2 = engine.index_document(sample_doc2, page_number=2)

    assert len(engine.pages) == 2
    assert page1.patch_count == 32
    assert page2.patch_count == 32

    # Query search
    results = engine.search("architecture diagram", top_k=2)
    assert len(results) == 2
    assert results[0]["match_type"] == "colpali_maxsim"
    assert results[0]["score"] > -1.0


def test_colpali_cli_commands(tmp_path: Path, monkeypatch):
    """Verify hath0r kb index --vision and hath0r kb search --vision."""
    # Isolated cwd: keep the SQLite and ColPali indexes out of the developer's real group/repo cache.
    monkeypatch.chdir(tmp_path)
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir(parents=True)
    img_file = kb_dir / "system_flow.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"system_flow_data")

    runner = CliRunner()
    res_index = runner.invoke(cli, ["-o", "json", "kb", "index", "-d", str(kb_dir), "--vision"])
    assert res_index.exit_code == 0
    assert "colpali_indexed" in res_index.output

    res_search = runner.invoke(cli, ["-o", "text", "kb", "search", "--vision", "-q", "system flow"])
    assert res_search.exit_code == 0
    assert "system_flow.png" in res_search.output or "visual document matches" in res_search.output

    res_status = runner.invoke(cli, ["-o", "json", "kb", "status"])
    assert res_status.exit_code == 0
    assert "colpali_pages" in res_status.output
