"""Drive every FastMCP tool in ``create_mcp_server`` with its bots replaced by mocks."""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("mcp")

import hath0r_cli.server.mcp_server as mcp_server  # noqa: E402

BOT_TARGETS = [
    ("hath0r_cli.bots.agentgraph_bot", "AgentGraphBot"),
    ("hath0r_cli.bots.antagonistic_review", "AntagonisticReviewBot"),
    ("hath0r_cli.bots.cag_rag_router", "HybridCAGRAGRouter"),
    ("hath0r_cli.bots.cicccd_bot", "CICCCDCTManagingBot"),
    ("hath0r_cli.bots.contracts_bot", "ContractsBot"),
    ("hath0r_cli.bots.iac_bot", "IaCManagingBot"),
    ("hath0r_cli.bots.issue_manager", "IssueManagerBot"),
    ("hath0r_cli.bots.paper_design_bot", "PaperDesignBot"),
    ("hath0r_cli.bots.redteam_engine", "MultiAgentRedTeamEngine"),
    ("hath0r_cli.bots.repo_clean", "CleanReposWorkflowBot"),
    ("hath0r_cli.bots.taguchi_bot", "TaguchiBot"),
    ("hath0r_cli.bots.token_check_bot", "TokenCheckWorkflowBot"),
    ("hath0r_cli.bots.token_telemetry_bot", "TokenTelemetryCLIBot"),
    ("hath0r_cli.bots.tokenizer_tax_bot", "TokenizerTaxBot"),
    ("hath0r_cli.bots.upgrade_bot", "UpgradeBot"),
    ("hath0r_cli.bots.upgrade_bot", "UpgradeVerifierBot"),
    ("hath0r_cli.bots.vision_bot", "VisionBot"),
    ("hath0r_cli.bots.voice_converse", "SpeechListenerBot"),
    ("hath0r_cli.bots.voice_converse", "VoiceSynthesizerBot"),
]

# Explicit arguments for tools whose required parameters are not plain strings,
# plus extra calls that walk alternate branches.
EXTRA_CALLS = {
    "hath0r_optimize_taguchi": [
        {"snr_values": [1.0, 2.0], "loss_k": 1.0, "target_m": 1.0, "measured_y": 1.2},
    ],
    "hath0r_upgrade": [{"action": "check"}, {"action": "run"}, {"action": "verify"}, {"action": "rollback"}],
    "hath0r_clean_repos": [{"dry_run": True}, {"dry_run": False, "repo_path": "."}],
    "hath0r_voice_listen": [{"prompt": "Say something", "simulated_transcript": "hello"}],
    "hath0r_pr_review_antagonistic": [{"pr_number": 1, "repo": "o/r"}],
    "hath0r_session_set": [{"key": "k", "value": {"a": 1}, "ttl_seconds": 30}],
    "hath0r_runbook_get_prompt": [{"runbook_name": "deploy", "variables": {"ENV": "dev"}}],
}


@pytest.fixture
def server(monkeypatch):
    import importlib

    mocks = {}
    for module_name, cls in BOT_TARGETS:
        module = importlib.import_module(module_name)
        mock = MagicMock(name=cls)
        monkeypatch.setattr(module, cls, mock)
        mocks[cls] = mock
    mocks["UpgradeVerifierBot"].return_value.verify.return_value = {"passed": True}

    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps({"results": []}), stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: completed)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: b"+except: pass\n")
    return mcp_server.create_mcp_server(), mocks


def _default_args(fn) -> dict:
    args = {}
    for name, param in inspect.signature(fn).parameters.items():
        if param.default is inspect.Parameter.empty:
            ann = str(param.annotation)
            args[name] = 1 if "int" in ann else ("x.png" if "path" in name else "probe")
    return args


def test_every_tool_runs_with_mocked_bots(server):
    mcp, _ = server
    tools = mcp._tool_manager._tools
    assert len(tools) >= 40
    for name, tool in tools.items():
        for kwargs in [_default_args(tool.fn)] + EXTRA_CALLS.get(name, []):
            call = {**_default_args(tool.fn), **kwargs}
            tool.fn(**call)  # must not raise


def test_upgrade_verify_reports_verification(server):
    mcp, mocks = server
    res = mcp._tool_manager._tools["hath0r_upgrade"].fn(action="verify", target_version="1.7.0")
    assert res["passed"] is True
    rollback = mcp._tool_manager._tools["hath0r_upgrade"].fn(action="rollback")
    assert rollback["success"] is False


def test_clean_repos_dry_run_makes_no_changes(server):
    mcp, mocks = server
    res = mcp._tool_manager._tools["hath0r_clean_repos"].fn(dry_run=True)
    assert res["dry_run"] is True
    mocks["CleanReposWorkflowBot"].assert_not_called()


def test_pr_review_reports_diff_errors(server, monkeypatch):
    mcp, _ = server

    def boom(*a, **k):
        raise subprocess.SubprocessError("gh missing")

    monkeypatch.setattr(subprocess, "check_output", boom)
    res = mcp._tool_manager._tools["hath0r_pr_review_antagonistic"].fn(pr_number=7)
    assert res["success"] is False and "gh missing" in res["error"]


class _RedirectPath:
    """Callable stand-in for ``Path`` that maps the hardcoded operator directories into a temp dir."""

    def __init__(self, target: Path) -> None:
        self._target = target

    def __call__(self, *args):
        raw = str(Path(*args)) if args else "."
        for prefix in ("/Users/raybayly/Development/Ray/mcp", "/Users/raybayly/Development/OpenSource/.hath0r"):
            if raw.startswith(prefix):
                raw = str(self._target) + raw[len(prefix):]
        return Path(raw)

    def __getattr__(self, name):
        return getattr(Path, name)


@pytest.fixture
def redirected(tmp_path, monkeypatch):
    monkeypatch.setattr(mcp_server, "Path", _RedirectPath(tmp_path))
    return tmp_path


def test_ray_index_search_and_get(redirected):
    assert mcp_server._search_ray_index("anything")["success"] is False
    assert mcp_server._get_ray_document("d1")["success"] is False

    index = redirected / "data" / "indices" / "knowledge_index.json"
    index.parent.mkdir(parents=True)
    docs = {
        "d1": {"id": "d1", "source": "notes", "title": "Deploy guide", "content": "deploy " * 60, "relative_path": "a.md"},
        "d2": {"id": "d2", "source": "other", "title": "Unrelated", "content": "nothing", "relative_path": "b.md"},
    }
    index.write_text(json.dumps({"documents": docs}), encoding="utf-8")

    hits = mcp_server._search_ray_index("deploy", source="notes")
    assert hits["count"] == 1 and hits["results"][0]["preview"].endswith("...")
    assert mcp_server._search_ray_index("!!!")["count"] == 0
    assert mcp_server._get_ray_document("b.md")["document"]["id"] == "d2"
    assert mcp_server._get_ray_document("zzz")["success"] is False

    index.write_text("{broken", encoding="utf-8")
    assert mcp_server._search_ray_index("deploy")["success"] is False
    assert mcp_server._get_ray_document("d1")["success"] is False


def test_runbooks(redirected):
    runbooks = redirected / "knowledgebase" / "canonical" / "runbooks"
    runbooks.mkdir(parents=True)
    (runbooks / "deploy-service.md").write_text("Deploy to ${ENV} then $ENV", encoding="utf-8")

    listed = mcp_server._list_runbooks()
    assert listed["count"] == 1
    exact = mcp_server._get_runbook_prompt("deploy-service", {"ENV": "prod"})
    assert exact["content"] == "Deploy to prod then prod"
    assert mcp_server._get_runbook_prompt("deploy")["success"] is True
    assert mcp_server._get_runbook_prompt("missing")["success"] is False


def test_session_memory_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("HATH0R_SESSION_BACKEND", "memory")
    written = mcp_server._set_session_memory("probe-key", {"v": 1})
    assert written["key"] == "probe-key"
    read = mcp_server._get_session_memory("probe-key")
    assert read["key"] == "probe-key"


def test_session_memory_errors(monkeypatch):
    import hath0r_cli.session_store as store

    def broken():
        raise store.SessionStoreError("down")

    monkeypatch.setattr(store, "get_session_store", broken)
    assert mcp_server._get_session_memory("k")["error"] == "down"
    assert mcp_server._set_session_memory("k", 1)["success"] is False
