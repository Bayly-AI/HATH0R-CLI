"""RAG retrieval backend for the hybrid CAG/RAG router (#394)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.cag_rag_router import HybridCAGRAGRouter
from hath0r_cli.cli import main
from hath0r_cli.kb_index import SQLiteIndexStore

RAG_QUERY = "archive onboarding runbook"  # "archive" routes to RAG


@pytest.fixture
def kb_index(tmp_path: Path) -> Path:
    docs = tmp_path / "kb"
    docs.mkdir()
    (docs / "onboarding.md").write_text(
        "# Onboarding Runbook\n\nSteps to onboard a new member repository into the suite.\n", encoding="utf-8"
    )
    (docs / "release.md").write_text("# Release Playbook\n\nPromote release branches to master.\n", encoding="utf-8")
    db = tmp_path / "cache" / "kb_index.sqlite"
    store = SQLiteIndexStore(db_path=db)
    store.sync_directory(docs)
    return db


def test_query_is_routed_to_rag() -> None:
    assert HybridCAGRAGRouter().classify_query(RAG_QUERY) == "RAG"


def test_rag_returns_ranked_matches(kb_index: Path) -> None:
    res = HybridCAGRAGRouter().route_query(RAG_QUERY, top_k=5, index_path=kb_index)
    assert res["route"] == "RAG"
    assert res["status"] == "success"
    assert res["rag_backend"] == "sqlite_fts5"
    assert res["matches_count"] == len(res["matches"]) >= 1
    top = res["matches"][0]
    assert top["title"] == "Onboarding Runbook"
    assert {"path", "title", "snippet", "score"} <= set(top)
    scores = [m["score"] for m in res["matches"]]
    assert scores == sorted(scores, reverse=True)


def test_rag_respects_top_k(kb_index: Path) -> None:
    res = HybridCAGRAGRouter().route_query("archive playbook runbook", top_k=1, index_path=kb_index)
    assert res["matches_count"] == 1


def test_rag_no_match_is_success_with_empty_matches(kb_index: Path) -> None:
    res = HybridCAGRAGRouter().route_query("archive zzqxnonexistent", index_path=kb_index)
    assert res["status"] == "success"
    assert res["matches"] == []


def test_rag_missing_index_is_reported_and_not_created(tmp_path: Path) -> None:
    db = tmp_path / "missing" / "kb_index.sqlite"
    res = HybridCAGRAGRouter().route_query(RAG_QUERY, index_path=db)
    assert res["status"] == "no_index"
    assert "hath0r kb index" in res["message"]
    assert not db.exists()


def test_rag_empty_index_is_reported(tmp_path: Path) -> None:
    db = tmp_path / "kb_index.sqlite"
    SQLiteIndexStore(db_path=db)  # schema only, no documents
    res = HybridCAGRAGRouter().route_query(RAG_QUERY, index_path=db)
    assert res["status"] == "empty_index"


def test_cli_smart_query_prints_matches(kb_index: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(HybridCAGRAGRouter, "default_index_path", staticmethod(lambda: kb_index))
    result = CliRunner().invoke(main, ["-o", "text", "kb", "smart-query", RAG_QUERY, "--limit", "2"])
    assert result.exit_code == 0, result.output
    assert "Onboarding Runbook" in result.output
    assert "Matches (" in result.output


def test_cli_smart_query_json_degraded_without_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(HybridCAGRAGRouter, "default_index_path", staticmethod(lambda: tmp_path / "none.sqlite"))
    result = CliRunner().invoke(main, ["-o", "json", "kb", "smart-query", RAG_QUERY])
    payload = json.loads(result.output)
    assert payload["state"] == "degraded"
    assert payload["data"]["status"] == "no_index"
