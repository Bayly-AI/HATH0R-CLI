"""Session store backends and their HAHP / L2WS / MCP integrations (#395)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from hath0r_cli import session_store as ss
from hath0r_cli.session_store import (
    LocalJSONSessionStore,
    RedisSessionStore,
    SessionStoreError,
    get_session_store,
)

# --------------------------------------------------------------------------- local backend


def test_local_set_get_delete_list(tmp_path: Path) -> None:
    store = LocalJSONSessionStore(tmp_path / "s.json")
    assert store.get("missing") is None and not store.exists("missing")
    store.set("hahp:a", {"x": 1})
    store.set("hahp:b", [1, 2])
    store.set("l2ws:t", {"temperature": 0.1})
    assert store.get("hahp:a") == {"x": 1}
    assert store.list_keys("hahp:") == ["hahp:a", "hahp:b"]
    assert store.delete("hahp:a") is True
    assert store.delete("hahp:a") is False
    assert store.list_keys() == ["hahp:b", "l2ws:t"]


def test_local_ttl_expires_and_is_purged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1_000.0]
    monkeypatch.setattr(ss.time, "time", lambda: now[0])
    store = LocalJSONSessionStore(tmp_path / "s.json")
    out = store.set("k", "v", ttl_seconds=10)
    assert out["expires_at"] == 1_010.0
    now[0] = 1_009.0
    assert store.get("k") == "v"
    now[0] = 1_011.0
    assert store.get("k") is None and store.list_keys() == []
    store.set("other", 1)  # write purges expired entries from disk
    assert "k" not in json.loads((tmp_path / "s.json").read_text())["entries"]


def test_local_rejects_bad_ttl_and_unserializable(tmp_path: Path) -> None:
    store = LocalJSONSessionStore(tmp_path / "s.json")
    with pytest.raises(ValueError):
        store.set("k", 1, ttl_seconds=0)
    with pytest.raises(SessionStoreError):
        store.set("k", object())
    assert not (tmp_path / "s.json").exists()


def test_local_reads_legacy_flat_format(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"a": 1, "a__ttl": 30, "b": {"y": 2}}), encoding="utf-8")
    store = LocalJSONSessionStore(p)
    assert store.list_keys() == ["a", "b"]
    assert store.get("b") == {"y": 2}


def test_local_corrupt_file_raises(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(SessionStoreError):
        LocalJSONSessionStore(p).get("k")


def test_local_store_is_shared_across_processes(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    LocalJSONSessionStore(p).set("hahp:x", {"from": "parent"})
    code = (
        "import json,sys; from hath0r_cli.session_store import LocalJSONSessionStore as S;"
        "s=S(sys.argv[1]); print(json.dumps(s.get('hahp:x'))); s.set('hahp:y', {'from': 'child'})"
    )
    out = subprocess.run([sys.executable, "-c", code, str(p)], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == {"from": "parent"}
    assert LocalJSONSessionStore(p).get("hahp:y") == {"from": "child"}


# --------------------------------------------------------------------------- backend selection


def test_default_backend_is_local_at_configured_path(_isolated_session_store: Path) -> None:
    store = get_session_store()
    assert isinstance(store, LocalJSONSessionStore)
    assert store.path == _isolated_session_store


def test_unknown_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_SESSION_BACKEND", "dynamo")
    with pytest.raises(SessionStoreError):
        get_session_store()


def test_redis_backend_without_package_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HATH0R_SESSION_BACKEND", "redis")
    monkeypatch.setitem(sys.modules, "redis", None)  # simulate not installed
    with pytest.raises(SessionStoreError, match="hath0r-cli\\[redis\\]"):
        get_session_store()


# --------------------------------------------------------------------------- redis backend (fake client)


class _FakeRedis:
    def __init__(self, fail: bool = False) -> None:
        self.data: Dict[str, Any] = {}
        self.ttl: Dict[str, Optional[int]] = {}
        self.fail = fail

    def _check(self) -> None:
        if self.fail:
            raise ConnectionError("connection refused")

    def get(self, k: str) -> Any:
        self._check()
        return self.data.get(k)

    def exists(self, k: str) -> int:
        self._check()
        return int(k in self.data)

    def set(self, k: str, v: str, ex: Optional[int] = None) -> bool:
        self._check()
        self.data[k] = v.encode("utf-8")
        self.ttl[k] = ex
        return True

    def delete(self, k: str) -> int:
        self._check()
        return int(self.data.pop(k, None) is not None)

    def scan_iter(self, match: str) -> Any:
        self._check()
        prefix = match.rstrip("*")
        return iter([k.encode("utf-8") for k in self.data if k.startswith(prefix)])


def test_redis_backend_roundtrip_with_prefix_and_ttl() -> None:
    fake = _FakeRedis()
    store = RedisSessionStore("redis://user:secret@localhost:6379/0", client=fake)
    store.set("hahp:a", {"x": 1}, ttl_seconds=60)
    assert "hath0r:hahp:a" in fake.data and fake.ttl["hath0r:hahp:a"] == 60
    assert store.get("hahp:a") == {"x": 1}
    assert store.list_keys("hahp:") == ["hahp:a"]
    assert store.delete("hahp:a") is True
    assert "secret" not in json.dumps(store.describe())


def test_redis_backend_unreachable_raises() -> None:
    store = RedisSessionStore("redis://localhost:6379/0", client=_FakeRedis(fail=True))
    with pytest.raises(SessionStoreError, match="unavailable"):
        store.get("k")


# --------------------------------------------------------------------------- integrations


def test_hahp_sync_and_read_back_via_mcp_session_tool() -> None:
    pytest.importorskip("mcp")
    from hath0r_cli.bots.hahp_protocol import HAHPProtocolManager
    from hath0r_cli.server.mcp_server import create_mcp_server

    mgr = HAHPProtocolManager()
    env = mgr.create_envelope("planner", "coder", state_variables={"step": 3})
    res = mgr.sync_to_session_store(env)
    assert res["status"] == "synced"
    assert res["session_backend"]["backend"] == "local"

    # A fresh manager (stand-in for another process) can load it back.
    loaded = HAHPProtocolManager().load_from_session_store(env.handoff_id)
    assert loaded is not None and loaded.state_variables == {"step": 3}

    get_tool = create_mcp_server()._tool_manager._tools["hath0r_session_get"].fn
    out = get_tool(key=f"hahp:{env.handoff_id}")
    assert out["exists"] is True and out["value"]["recipient_agent"] == "coder"


def test_hahp_sync_reports_backend_failure(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    from hath0r_cli.bots.hahp_protocol import HAHPProtocolManager

    monkeypatch.setenv("HATH0R_SESSION_BACKEND", "nope")
    mgr = HAHPProtocolManager()
    env = mgr.create_envelope("a", "b")  # creation still succeeds (journal)
    res = mgr.sync_to_session_store(env)
    assert res["status"] == "error" and "nope" in res["error"]
    assert any("not synced" in r.message for r in caplog.records)
    assert mgr.list_handoffs()[0]["handoff_id"] == env.handoff_id


def test_l2ws_warmstart_is_shared(tmp_path: Path) -> None:
    from hath0r_cli.cccd.l2ws_predictor import L2WSPredictor

    L2WSPredictor(storage_path=tmp_path / "w.json").save_warmstart("sig-1", {"temperature": 0.3})
    assert get_session_store().get("l2ws:sig-1") == {"temperature": 0.3}


def test_mcp_session_set_get_with_ttl() -> None:
    pytest.importorskip("mcp")
    from hath0r_cli.server.mcp_server import create_mcp_server

    tools = create_mcp_server()._tool_manager._tools
    out = tools["hath0r_session_set"].fn(key="k", value={"a": 1}, ttl_seconds=120)
    assert out["success"] is True and out["expires_at"] is not None
    assert tools["hath0r_session_get"].fn(key="k")["value"] == {"a": 1}
    bad = tools["hath0r_session_set"].fn(key="k", value=1, ttl_seconds=-5)
    assert bad["success"] is False
