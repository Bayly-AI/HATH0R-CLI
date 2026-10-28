"""CLI tests for `hath0r upgrade`, with the upgrade bots replaced by fakes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from hath0r_cli.bots import upgrade_bot
from hath0r_cli.cli import main

INSTALL = {"version": "1.0.0", "method": "pipx", "repo_root": ""}
CHECKS = [
    {"name": "version", "passed": True, "required": True, "detail": "1.0.0\nmore"},
    {"name": "smoke", "passed": False, "required": True, "detail": "boom"},
    {"name": "optional", "passed": False, "required": False, "detail": ""},
]


class FakeUpgradeBot:
    check_result: dict = {}
    run_result: dict = {}
    snapshot = None
    rollback_result: dict = {"success": True}

    def __init__(self, *a, **k):
        pass

    def check(self, version=None):
        return self.check_result

    def run(self, **kwargs):
        return dict(self.run_result)

    def detect_install(self):
        return SimpleNamespace(**INSTALL, to_dict=lambda: dict(INSTALL))

    def last_snapshot(self):
        return self.snapshot

    def rollback(self, snap):
        return dict(self.rollback_result)

    def status(self, limit=10):
        return {
            "message": "1 run",
            "history": [
                {"finished_at": "t", "outcome": "ok", "from_version": "1", "to_version": "2"},
                {"finished_at": "t", "outcome": "failed", "from_version": "1", "to_version": "2", "failure": "x"},
            ],
        }

    def schedule_spec(self, hour, minute, file_issue):
        return {"plist": "<plist/>", "cron": "17 4 * * * hath0r upgrade run", "plist_path": self.plist_path}


class FakeVerifier:
    passed = True

    def __init__(self, *a, **k):
        pass

    def command_for(self, install):
        return ["hath0r"]

    def verify(self, version, level, command, repo_root):
        return {"passed": self.passed, "summary": "2/3 passed", "checks": CHECKS}


class FakeAnnouncer:
    def __init__(self, *a, **k):
        pass

    def announce(self, report, **kwargs):
        return {"success": False, "message": "voice queue offline", "issue": {"url": "https://example/1"}}


@pytest.fixture
def bots(monkeypatch, tmp_path):
    FakeUpgradeBot.plist_path = str(tmp_path / "LaunchAgents" / "x.plist")
    monkeypatch.setattr(upgrade_bot, "UpgradeBot", FakeUpgradeBot)
    monkeypatch.setattr(upgrade_bot, "UpgradeVerifierBot", FakeVerifier)
    monkeypatch.setattr(upgrade_bot, "UpgradeAnnouncerBot", FakeAnnouncer)
    return FakeUpgradeBot


def _run(fmt, *args):
    res = CliRunner().invoke(main, ["-o", fmt, "upgrade", *args])
    assert res.exception is None or isinstance(res.exception, SystemExit), res.output
    return res


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
def test_upgrade_check(bots, fmt):
    bots.check_result = {"success": True, "install": INSTALL, "latest_version": "1.1.0", "message": "update available"}
    assert _run(fmt, "check").exit_code == 0
    bots.check_result = {"success": False, "install": INSTALL, "error": "offline", "failure": {"code": "NET"}}
    assert _run(fmt, "check", "--version", "9.9.9").exit_code == 1


RUN_CASES = [
    ({"success": True, "outcome": "up-to-date", "message": "current"}, 0),
    ({"success": True, "outcome": "dry-run", "message": "plan", "stages": [{"stage": "plan", "status": "ok"}]}, 0),
    (
        {
            "success": True,
            "outcome": "upgraded",
            "message": "done",
            "stages": [{"stage": "install", "status": "ok"}, {"stage": "verify", "status": "failed"}],
            "verification": {"checks": CHECKS},
        },
        0,
    ),
    (
        {
            "success": False,
            "outcome": "rolled-back",
            "message": "failed",
            "failure": {"code": "VERIFY", "message": "bad", "hint": "retry"},
            "rollback": {"success": True},
            "exit_code": 1,
        },
        1,
    ),
    ({"success": False, "outcome": "rollback-failed", "rollback": {"success": False}, "exit_code": 6}, 6),
]


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
@pytest.mark.parametrize("result,code", RUN_CASES, ids=["current", "dry", "ok", "rolled", "rbfail"])
def test_upgrade_run(bots, fmt, result, code):
    bots.run_result = result
    assert _run(fmt, "run", "--force", "--file-issue", "--no-speak").exit_code == code


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
def test_upgrade_verify(bots, monkeypatch, fmt):
    monkeypatch.setattr(FakeVerifier, "passed", True)
    assert _run(fmt, "verify").exit_code == 0
    monkeypatch.setattr(FakeVerifier, "passed", False)
    assert _run(fmt, "verify", "--tests", "full", "--announce", "--expect-version", "2.0").exit_code == 1


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
def test_upgrade_rollback(bots, fmt):
    bots.snapshot = None
    assert _run(fmt, "rollback").exit_code == 1
    bots.snapshot = {"method": "pipx", "version": "0.9.0"}
    assert _run(fmt, "rollback", "--dry-run").exit_code == 0
    bots.rollback_result = {"success": True}
    assert _run(fmt, "rollback").exit_code == 0
    bots.rollback_result = {"success": False, "error": "pipx missing"}
    assert _run(fmt, "rollback").exit_code == 1


@pytest.mark.parametrize("fmt", ["text", "json"], ids=["text", "json"])
def test_upgrade_status_and_schedule(bots, fmt):
    assert "1 run" in _run("text", "status").output or fmt == "json"
    _run(fmt, "status", "--limit", "2")
    assert "crontab" in _run("text", "schedule").output
    res = _run(fmt, "schedule", "--hour", "3", "--minute", "5", "--no-file-issue", "--write")
    assert res.exit_code == 0
