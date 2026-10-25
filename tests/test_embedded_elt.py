"""Unit tests for Hath0r Embedded ELT Subsystem."""

import json
from pathlib import Path

import pytest

from hath0r_cli.bots.embedded_elt_bot import EmbeddedELTBot
from hath0r_cli.bots.transformation_pipeline_bot import TransformationPipelineBot
from hath0r_cli.elt_store import RawStagingStore


@pytest.fixture
def temp_store(tmp_path: Path) -> RawStagingStore:
    """Fixture providing an isolated SQLite raw staging store."""
    db_file = tmp_path / "cache" / "raw_staging_test.sqlite"
    return RawStagingStore(db_path=db_file)


def test_raw_staging_store_crud(temp_store: RawStagingStore):
    """Test raw record staging, deduplication, retrieval, and status."""
    res1 = temp_store.stage_record(
        source_uri="docs/test.md",
        source_type="docs",
        raw_payload="# Test Title\nContent here",
        metadata={"author": "ray"},
    )
    assert res1["is_duplicate"] is False
    assert res1["record_id"] > 0
    rec_id = res1["record_id"]
    sha = res1["content_sha256"]

    # Duplicate insertion
    res2 = temp_store.stage_record(
        source_uri="docs/test_copy.md",
        source_type="docs",
        raw_payload="# Test Title\nContent here",
    )
    assert res2["is_duplicate"] is True
    assert res2["record_id"] == rec_id

    # Retrieve by ID and hash
    rec = temp_store.get_record(rec_id)
    assert rec is not None
    assert rec.source_uri == "docs/test.md"
    assert rec.metadata.get("author") == "ray"

    rec_by_hash = temp_store.get_record_by_hash(sha)
    assert rec_by_hash is not None
    assert rec_by_hash.id == rec_id

    # Listing records
    records = temp_store.list_records(source_type="docs")
    assert len(records) == 1


def test_projection_states_and_dirty_tracking(temp_store: RawStagingStore):
    """Test projection status updates, dirty marking, and unprojected queries."""
    res = temp_store.stage_record(
        source_uri="docs/alpha.md",
        source_type="docs",
        raw_payload="Content Alpha",
    )
    rec_id = res["record_id"]

    # Should be unprojected initially
    unprojected = temp_store.get_unprojected_records("fts5")
    assert any(r.id == rec_id for r in unprojected)

    # Mark projected
    temp_store.mark_projected(rec_id, "fts5", status="synced")
    unprojected_after = temp_store.get_unprojected_records("fts5")
    assert not any(r.id == rec_id for r in unprojected_after)

    # Mark dirty (rebuild simulation)
    dirty_count = temp_store.mark_all_dirty("fts5")
    assert dirty_count >= 1
    unprojected_dirty = temp_store.get_unprojected_records("fts5")
    assert any(r.id == rec_id for r in unprojected_dirty)


def test_embedded_elt_bot_doc_extraction(tmp_path: Path, temp_store: RawStagingStore):
    """Test EmbeddedELTBot extracting docs from directory."""
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()
    (doc_dir / "sample1.md").write_text("# Doc One\nBody one")
    (doc_dir / "sample2.md").write_text("# Doc Two\nBody two")

    bot = EmbeddedELTBot(cwd=tmp_path, store=temp_store)
    batch_res = bot.extract_and_stage_docs(target_dir=doc_dir)

    assert batch_res.total_scanned == 2
    assert batch_res.staged_new == 2
    assert batch_res.duplicates_skipped == 0

    # Re-scan checks idempotency
    batch_res_dup = bot.extract_and_stage_docs(target_dir=doc_dir)
    assert batch_res_dup.total_scanned == 2
    assert batch_res_dup.staged_new == 0
    assert batch_res_dup.duplicates_skipped == 2


def test_embedded_elt_bot_mcp_and_telemetry(temp_store: RawStagingStore):
    """Test EmbeddedELTBot MCP and telemetry ingestion adapters."""
    bot = EmbeddedELTBot(store=temp_store)

    mcp_res = bot.extract_and_stage_mcp(server_id="1-nation-mcp", source_id="federal_votes")
    assert mcp_res["is_duplicate"] is False
    assert "mcp://1-nation-mcp/federal_votes" == mcp_res["source_uri"]

    tel_res = bot.extract_and_stage_telemetry(
        payload={"trace_id": "tr-123", "tokens": 42},
        source_uri="otel/test-span",
    )
    assert tel_res["is_duplicate"] is False

    stats = bot.get_status()
    assert stats["total_records"] == 2
    assert "mcp" in stats["source_types"]
    assert "telemetry" in stats["source_types"]


def test_transformation_pipeline_projections(temp_store: RawStagingStore):
    """Test TransformationPipelineBot executing downstream projections."""
    temp_store.stage_record(
        source_uri="docs/governance/test-strat.md",
        source_type="docs",
        raw_payload="# Strategy Guide\nOperational strategy content",
    )
    temp_store.stage_record(
        source_uri="otel/span-1",
        source_type="telemetry",
        raw_payload=json.dumps({"tokens": 150, "model": "gemini"}),
    )

    pipe_bot = TransformationPipelineBot(store=temp_store)
    results = pipe_bot.transform_all()

    for proj in pipe_bot.SUPPORTED_PROJECTIONS:
        assert proj in results
        assert results[proj]["error_count"] == 0
        assert results[proj]["success_count"] >= 1

    status = pipe_bot.get_pipeline_status()
    for proj in pipe_bot.SUPPORTED_PROJECTIONS:
        assert status["projections"][proj]["pending_or_dirty"] == 0


def test_pruning_and_retention(temp_store: RawStagingStore):
    """Test pruning records based on retention days."""
    bot = EmbeddedELTBot(store=temp_store)
    bot.stage_raw("raw/data", "raw", "temporary content")

    # Prune with 0 days should purge all records
    prune_res = bot.prune(retention_days=0)
    assert prune_res["records_deleted"] == 1

    stats = bot.get_status()
    assert stats["total_records"] == 0
