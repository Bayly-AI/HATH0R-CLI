"""Text-mode CLI tests for `hath0r memory` with MemoryManagerBot mocked."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

import hath0r_cli.bots.memory_manager as memory_manager
from hath0r_cli.cli import main
from tests.fakebot import Seq, patch_bot

SESSION = {
    "session_id": "sess-1",
    "active_focus": "coverage",
    "prior_summary": "last time",
    "read_count": 1,
    "write_count": 2,
    "recalled_nodes": [{"id": "n1", "type": "episode", "label": "L"}],
    "entries": [{"kind": "note", "summary": "s"}],
    "micro_entries": [{"kind": "note", "summary": "s"}],
}

CASES = [
    (["memory", "init", "--dry-run"], [{"success": True, "message": "Initialized", "files": ["a"]},
                                       {"success": False, "error": "no repo"}], ["Initialized", "no repo"]),
    (["memory", "read", "core"], [{"success": True, "content": "# Core"}, {"success": False, "error": "missing"}],
     ["Core", "missing"]),
    (["memory", "compound", "-l", "Label", "-c", "Content", "--tags", "a,b", "--relates-to", "n1",
      "--source-file", "x.py", "--no-sync", "--dry-run"],
     [{"success": True, "message": "Compounded", "node": {"id": "n2", "type": "episode"}, "content_hash": "h",
       "edges_added": [1], "reflection": {"insights_generated": 1}, "agentgraph_synced": False},
      {"success": False, "error": "hash conflict"}], ["Compounded", "hash conflict"]),
    (["memory", "reflect", "--dry-run"], [{"success": True, "insights_generated": 1,
                                           "insights": [{"id": "i1", "label": "Insight"}]}], ["Insight"]),
    (["memory", "dream"], [{"success": True, "insights_generated": 0, "insights": []},
                           {"success": True, "insights_generated": 1,
                            "insights": [{"id": "i1", "label": "Dream", "content": "c"}]}],
     ["already synthesized", "Dream"]),
    (["memory", "verify", "--task", "493"],
     [{"compounded": True, "latest_node": {"id": "n1", "label": "L"}, "session": {"session_id": "s"},
       "hash_status": {"revision": 1}, "hashes_verified": True}, {"compounded": False, "error": "not compounded"}],
     ["Gate PASSED", "not compounded"]),
    (["memory", "hash", "--check"],
     [{"verified": True, "revision": 2}, {"verified": False, "error": "drift", "mismatched_files": ["a"],
                                          "missing_files": ["b"], "stale_source_files": ["c"]}],
     ["Hashes Verified", "Stale Source File"]),
    (["memory", "hash", "--sync", "--dry-run"], [{"success": True, "revision": 3}, {"success": False, "error": "locked"}],
     ["Synchronized", "locked"]),
    (["memory", "ensure-all", "--dry-run", "--no-sync"],
     [{"success": True, "repos_count": 1, "repos": [{"repo": "r", "compounded": True, "session_read_verified": True,
                                                     "session_write_verified": True, "hashes_verified": True,
                                                     "agentgraph_synced": True}, {"repo": "q"}]}],
     ["Provisioning"]),
    (["memory", "session", "start", "-f", "coverage", "--dry-run"],
     [{"success": True, "message": "Session started", "session": SESSION, "byte_size": 100}], ["Session started"]),
    (["memory", "session", "read", "-f", "coverage", "--dry-run"],
     [{"success": True, "message": "Session read", "session": SESSION, "recalled_nodes": SESSION["recalled_nodes"]}],
     ["Session read"]),
    (["memory", "session", "write", "found a thing", "--tag", "a", "--tags", "b,c", "--next-step", "n", "--dry-run"],
     [{"success": True, "message": "Wrote"}, {"success": False, "error": "too big"}], ["Wrote", "too big"]),
    (["memory", "session", "end", "-m", "done", "--next-step", "n", "--no-sync", "--dry-run"],
     [{"success": True, "message": "Ended", "session": SESSION}], ["Ended"]),
    (["memory", "session", "status"],
     [{"success": True, "status": "active", "read_verified": True, "write_verified": True, "session": SESSION},
      {"success": True, "status": "stale"}], ["active", "stale"]),
]


@pytest.mark.parametrize("args, results, fragments", CASES, ids=[" ".join(c[0][1:3]) for c in CASES])
def test_memory_commands_text(monkeypatch, args, results, fragments):
    for result, fragment in zip(results, fragments):
        patch_bot(monkeypatch, memory_manager, "MemoryManagerBot", result)
        res = CliRunner().invoke(main, ["-o", "text", *args])
        assert res.exception is None or isinstance(res.exception, SystemExit), res.output
        assert fragment in res.output, (args, result, res.output)


def test_memory_session_write_requires_summary():
    res = CliRunner().invoke(main, ["-o", "text", "memory", "session", "write"])
    assert res.exit_code == 2


def test_memory_hash_sync_verifies_after_write(monkeypatch):
    patch_bot(monkeypatch, memory_manager, "MemoryManagerBot", Seq([{"success": True, "revision": 4}, {"verified": True}]))
    res = CliRunner().invoke(main, ["-o", "json", "memory", "hash", "--track-file", "x.md"])
    assert res.exit_code == 0, res.output
