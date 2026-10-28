"""Sweep every BotRegistry dispatcher action with mocked bots.

Each dispatcher translates a factory step (bot id + action + args) into a bot
method call and wraps the result. The bots are replaced with mocks so the
sweep checks the translation layer only: every declared action must come back
as a StepExecutionResult, never raise.
"""

from __future__ import annotations

import inspect
import re
import subprocess
from unittest.mock import MagicMock

import pytest

from hath0r_cli import step_runner
from hath0r_cli.step_runner import BotRegistry, StepExecutionResult

_ACTION_RE = re.compile(r'action\s*(?:==\s*"([^"]+)"|in\s*\(([^)]*)\))')


class _Res(dict):
    """A bot result that reads as both a dict and an object."""

    def __getattr__(self, name):
        if name in self:
            return self[name]
        if name.startswith("__"):
            raise AttributeError(name)
        return MagicMock(name=name)


def _result(success: bool) -> _Res:
    return _Res(
        success=success,
        passed=success,
        error=None if success else "boom",
        issue_number=7,
        pr_number=9,
        number=9,
        url="https://example/9",
        current_branch="feature/7-demo",
        branch="feature/7-demo",
        blocked=not success,
        status="ok" if success else "failed",
        message="done",
        summary="summary",
        items=[],
        results=[],
        checks=[],
        text="hello",
        path="/tmp/x",
        version="1.0.0",
        outcome="upgraded" if success else "failed",
        exit_code=0 if success else 1,
    )


class _AutoBot:
    """Stands in for any bot: every method returns a result."""

    def __init__(self, success: bool) -> None:
        self._success = success
        self.cwd = None

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: _result(self._success)


def _dispatch_map() -> dict[str, list[str]]:
    """bot id -> actions named in its dispatcher, read from the source."""
    invoke_src = inspect.getsource(BotRegistry.invoke)
    mapping: dict[str, list[str]] = {}
    pending: list[str] = []
    for line in invoke_src.splitlines():
        ids = re.findall(r'"([a-z0-9-]+-bot)"', line)
        if "bot_id" in line and ids:
            pending = ids
        m = re.search(r"self\.(_dispatch_\w+)\(", line)
        if m and pending:
            src = inspect.getsource(getattr(BotRegistry, m.group(1)))
            actions: list[str] = []
            for eq, group in _ACTION_RE.findall(src):
                actions += [eq] if eq else re.findall(r'"([^"]+)"', group)
            for bot_id in pending:
                mapping[bot_id] = sorted(set(actions)) + ["no-such-action"]
            pending = []
    return mapping


DISPATCH = _dispatch_map()
CASES = [(bot_id, action) for bot_id, actions in DISPATCH.items() for action in actions]


@pytest.fixture(scope="module")
def registry(tmp_path_factory):
    return BotRegistry(cwd=tmp_path_factory.mktemp("sweep"))


def test_dispatch_map_covers_registry(registry):
    assert len(DISPATCH) >= 40
    assert set(DISPATCH) <= set(registry.registered_bot_ids())


@pytest.mark.parametrize("success", [True, False], ids=["ok", "fail"])
@pytest.mark.parametrize("dry_run", [True, False], ids=["dry", "live"])
def test_every_dispatch_action_returns_a_result(registry, monkeypatch, success, dry_run):
    for bot_id in DISPATCH:
        monkeypatch.setitem(registry._bots, bot_id, _AutoBot(success))
    # Some dispatchers shell out (the quality gate runs pytest); never recurse.
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, *a, **k: subprocess.CompletedProcess(cmd, 0 if success else 1, "out", "err")
    )
    args = {
        "repo": "o/r",
        "issue_number": 7,
        "pr_number": 9,
        "title": "t",
        "body": "b",
        "text": "hello",
        "branch": "feature/7-demo",
        "factory_id": "demo",
        "version": "1.0.0",
        "query": "q",
        "path": ".",
    }
    for bot_id, action in CASES:
        for step_args in (args, {}):
            res = registry.invoke(bot_id, action, step_args, repo="o/r", dry_run=dry_run, context={"issue_number": 7})
            assert isinstance(res, StepExecutionResult), (bot_id, action)
            assert isinstance(res.to_dict(), dict)


def test_unknown_bot_is_reported(registry):
    res = registry.invoke("ghost-bot", "run")
    assert not res.success and "not registered" in res.error
    assert step_runner.StepExecutionResult is StepExecutionResult
