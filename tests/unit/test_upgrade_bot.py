"""Unit tests for the Upgrade Bot suite (UpgradeBot, UpgradeVerifierBot, UpgradeAnnouncerBot).

Test-doc for cfg/factories/upgrade-factory.yaml. Every external effect — GitHub API, downloads,
pip/pipx/git subprocesses — is replaced with fakes, so these tests never touch the network or
the real install. Live end-to-end verification is described in
docs/governance/checklists/upgrade.md.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli.bots.upgrade_bot import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_ROLLBACK_FAILED,
    InstallInfo,
    ReleaseInfo,
    UpgradeAnnouncerBot,
    UpgradeBot,
    UpgradeError,
    UpgradeVerifierBot,
    compare_versions,
    parse_version,
)

WHEEL_BYTES = b"fake-wheel-contents"
WHEEL_SHA = hashlib.sha256(WHEEL_BYTES).hexdigest()


def release_payload(version: str = "1.1.0", digest: str | None = None, sidecar: bool = False) -> Dict[str, Any]:
    wheel = {
        "name": f"hath0r_cli-{version}-py3-none-any.whl",
        "browser_download_url": f"https://example.test/{version}/wheel.whl",
        "size": len(WHEEL_BYTES),
        "digest": digest if digest is not None else f"sha256:{WHEEL_SHA}",
    }
    assets = [wheel]
    if sidecar:
        assets.append(
            {"name": wheel["name"] + ".sha256", "browser_download_url": f"https://example.test/{version}/sha"}
        )
    return {
        "tag_name": f"v{version}",
        "html_url": "https://example.test/rel",
        "published_at": "2026-10-03",
        "assets": assets,
    }


class FakeHttp:
    def __init__(self, releases: Dict[str, Dict[str, Any]], files: Dict[str, bytes] | None = None) -> None:
        self.releases = releases
        self.files = files or {}
        self.calls: List[str] = []

    def __call__(self, url: str, headers: Dict[str, str]) -> bytes:
        self.calls.append(url)
        if "api.github.com" in url:
            key = "latest" if url.endswith("/latest") else url.rsplit("/v", 1)[-1]
            if key not in self.releases:
                raise OSError(f"404 {url}")
            return json.dumps(self.releases[key]).encode()
        if url in self.files:
            return self.files[url]
        if url.endswith("wheel.whl"):
            return WHEEL_BYTES
        raise OSError(f"unexpected url {url}")


class FakeRunner:
    """Records commands; returns scripted results by matching a substring of the joined argv."""

    def __init__(self, rules: List[Tuple[str, Tuple[int, str, str]]] | None = None) -> None:
        self.rules = rules or []
        self.calls: List[List[str]] = []

    def __call__(self, args: List[str], cwd: Any = None, timeout: int = 0) -> Tuple[int, str, str]:
        self.calls.append(list(args))
        joined = " ".join(args)
        for needle, result in self.rules:
            if needle in joined:
                return result
        return 0, "", ""

    def ran(self, needle: str) -> bool:
        return any(needle in " ".join(c) for c in self.calls)


class FakeVerifier:
    def __init__(self, results: List[bool]) -> None:
        self.results = list(results)
        self.calls: List[str] = []

    def command_for(self, install: InstallInfo) -> List[str]:
        return ["python", "-m", "hath0r_cli"]

    def baseline(self, command: Any = None) -> Dict[str, Any]:
        return {"doctor_failed": 0}

    def verify(self, target_version: str, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(target_version)
        passed = self.results.pop(0) if self.results else True
        checks = [{"name": "version", "passed": passed, "required": True, "detail": "x"}]
        return {
            "passed": passed,
            "checks": checks,
            "summary": "1/1 checks passed" if passed else "0/1; failing: version",
        }


def make_bot(tmp_path: Path, install: InstallInfo, http: FakeHttp, runner: FakeRunner) -> UpgradeBot:
    bot = UpgradeBot(cwd=tmp_path, runner=runner, http_get=http, state_dir=tmp_path / "state", python="python")
    bot.detect_install = lambda: install  # type: ignore[method-assign]
    return bot


def pip_install(version: str = "1.0.0") -> InstallInfo:
    return InstallInfo(method="pip", version=version, python="python")


# ── versions ──────────────────────────────────────────────────────────────────


def test_version_parsing_and_ordering() -> None:
    assert parse_version("v0.9.0")[:3] == (0, 9, 0)
    assert compare_versions("0.10.0", "0.9.9") == 1
    assert compare_versions("1.0.0-rc.1", "1.0.0") == -1
    assert compare_versions("v1.2.3", "1.2.3") == 0
    with pytest.raises(ValueError):
        parse_version("latest")


# ── check ─────────────────────────────────────────────────────────────────────


def test_check_reports_update_available(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install("1.0.0"), FakeHttp({"latest": release_payload("1.1.0")}), FakeRunner())
    res = bot.check()
    assert res["success"] and res["update_available"] and res["latest_version"] == "1.1.0"


def test_check_up_to_date(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install("1.1.0"), FakeHttp({"latest": release_payload("1.1.0")}), FakeRunner())
    assert bot.check()["update_available"] is False


def test_check_falls_back_to_gh_and_reports_feed_failure(tmp_path: Path) -> None:
    runner = FakeRunner([("gh api", (1, "", "gh: not logged in"))])
    bot = make_bot(tmp_path, pip_install(), FakeHttp({}), runner)
    res = bot.check()
    assert res["success"] is False and res["failure"]["code"] == "RELEASE_FEED_UNAVAILABLE"
    assert runner.ran("gh api repos/Bayly-AI/HATH0R-CLI/releases/latest")


# ── checksum verification ─────────────────────────────────────────────────────


def test_download_verified_accepts_matching_digest(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install(), FakeHttp({}), FakeRunner())
    rel = ReleaseInfo(
        tag="v1.1.0",
        version="1.1.0",
        assets=[
            {"name": "hath0r_cli-1.1.0-py3-none-any.whl", "url": "https://x/wheel.whl", "digest": f"sha256:{WHEEL_SHA}"}
        ],
    )
    res = bot.download_verified(rel, rel.wheel() or {}, tmp_path / "dl")
    assert res["sha256"] == WHEEL_SHA and Path(res["path"]).read_bytes() == WHEEL_BYTES


def test_download_verified_rejects_mismatch_and_deletes_file(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install(), FakeHttp({}), FakeRunner())
    rel = ReleaseInfo(
        tag="v1.1.0",
        version="1.1.0",
        assets=[
            {"name": "hath0r_cli-1.1.0-py3-none-any.whl", "url": "https://x/wheel.whl", "digest": "sha256:" + "0" * 64}
        ],
    )
    with pytest.raises(UpgradeError) as exc:
        bot.download_verified(rel, rel.assets[0], tmp_path / "dl")
    assert exc.value.code == "CHECKSUM_MISMATCH"
    assert not (tmp_path / "dl" / rel.assets[0]["name"]).exists()


def test_download_uses_sidecar_then_refuses_when_no_checksum(tmp_path: Path) -> None:
    http = FakeHttp({}, files={"https://x/sha": f"{WHEEL_SHA}  hath0r_cli-1.1.0-py3-none-any.whl\n".encode()})
    bot = make_bot(tmp_path, pip_install(), http, FakeRunner())
    wheel = {"name": "hath0r_cli-1.1.0-py3-none-any.whl", "url": "https://x/wheel.whl", "digest": ""}
    with_sidecar = ReleaseInfo(
        "v1.1.0", "1.1.0", assets=[wheel, {"name": wheel["name"] + ".sha256", "url": "https://x/sha"}]
    )
    assert bot.download_verified(with_sidecar, wheel, tmp_path / "a")["sha256"] == WHEEL_SHA
    with pytest.raises(UpgradeError) as exc:
        bot.download_verified(ReleaseInfo("v1.1.0", "1.1.0", assets=[wheel]), wheel, tmp_path / "b")
    assert exc.value.code == "CHECKSUM_MISSING"


# ── run pipeline ──────────────────────────────────────────────────────────────


def test_run_noop_when_up_to_date(tmp_path: Path) -> None:
    runner = FakeRunner()
    bot = make_bot(tmp_path, pip_install("1.1.0"), FakeHttp({"latest": release_payload("1.1.0")}), runner)
    report = bot.run(verifier=FakeVerifier([]))  # type: ignore[arg-type]
    assert report["outcome"] == "up-to-date" and report["exit_code"] == EXIT_OK
    assert not runner.ran("pip install")


def test_run_dry_run_changes_nothing(tmp_path: Path) -> None:
    runner = FakeRunner()
    bot = make_bot(tmp_path, pip_install(), FakeHttp({"latest": release_payload()}), runner)
    report = bot.run(dry_run=True, verifier=FakeVerifier([]))  # type: ignore[arg-type]
    assert report["outcome"] == "dry-run" and "[DRY-RUN]" in report["message"]
    assert not runner.ran("pip install") and not bot.report_file.exists()


def test_run_pip_upgrade_success(tmp_path: Path) -> None:
    runner = FakeRunner()
    bot = make_bot(tmp_path, pip_install(), FakeHttp({"latest": release_payload()}), runner)
    report = bot.run(verifier=FakeVerifier([True]))  # type: ignore[arg-type]
    assert report["outcome"] == "upgraded", report.get("failure")
    assert report["exit_code"] == EXIT_OK
    assert runner.ran("pip install --upgrade --force-reinstall")
    saved = json.loads(bot.report_file.read_text())
    assert saved["outcome"] == "upgraded" and bot.history_file.read_text().count("\n") == 1
    assert not bot.lock_file.exists()


def test_run_verification_failure_rolls_back(tmp_path: Path) -> None:
    http = FakeHttp({"latest": release_payload("1.1.0"), "1.0.0": release_payload("1.0.0")})
    runner = FakeRunner()
    bot = make_bot(tmp_path, pip_install("1.0.0"), http, runner)
    verifier = FakeVerifier([False, True])  # new version fails, restored version passes
    report = bot.run(verifier=verifier)  # type: ignore[arg-type]
    assert report["outcome"] == "rolled-back"
    assert report["failure"]["code"] == "VERIFICATION_FAILED"
    assert report["rollback"]["success"] is True and report["rollback"]["restored_version"] == "1.0.0"
    assert report["exit_code"] == EXIT_FAILED
    assert verifier.calls == ["1.1.0", "1.0.0"]


def test_run_rollback_failure_is_critical(tmp_path: Path) -> None:
    http = FakeHttp({"latest": release_payload("1.1.0")})  # previous release missing → rollback fails
    bot = make_bot(tmp_path, pip_install("1.0.0"), http, FakeRunner())
    report = bot.run(verifier=FakeVerifier([False]))  # type: ignore[arg-type]
    assert report["outcome"] == "rollback-failed" and report["exit_code"] == EXIT_ROLLBACK_FAILED


def test_run_no_rollback_leaves_new_version(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install(), FakeHttp({"latest": release_payload()}), FakeRunner())
    report = bot.run(auto_rollback=False, verifier=FakeVerifier([False]))  # type: ignore[arg-type]
    assert report["outcome"] == "failed" and "rollback" not in report


def test_run_install_failure_rolls_back(tmp_path: Path) -> None:
    http = FakeHttp({"latest": release_payload("1.1.0"), "1.0.0": release_payload("1.0.0")})
    runner = FakeRunner([("1.1.0-py3-none-any.whl", (1, "", "ResolutionImpossible"))])
    bot = make_bot(tmp_path, pip_install("1.0.0"), http, runner)
    report = bot.run(verifier=FakeVerifier([True]))  # type: ignore[arg-type]
    assert report["failure"]["code"] == "PIP_INSTALL_FAILED"
    assert report["outcome"] == "rolled-back"


def test_source_preflight_refuses_dirty_tree(tmp_path: Path) -> None:
    install = InstallInfo(
        method="source", version="1.0.0", python="python", repo_root=str(tmp_path), branch="development", head_sha="abc"
    )
    runner = FakeRunner([("status --porcelain", (0, " M src/x.py", ""))])
    bot = make_bot(tmp_path, install, FakeHttp({"latest": release_payload()}), runner)
    report = bot.run(verifier=FakeVerifier([]))  # type: ignore[arg-type]
    assert report["failure"]["code"] == "SOURCE_TREE_DIRTY"
    assert "rollback" not in report and not runner.ran("git merge")


def test_source_preflight_refuses_feature_branch(tmp_path: Path) -> None:
    install = InstallInfo(
        method="source", version="1.0.0", python="python", repo_root=str(tmp_path), branch="feature/1-x", head_sha="abc"
    )
    bot = make_bot(tmp_path, install, FakeHttp({"latest": release_payload()}), FakeRunner())
    assert bot.run(verifier=FakeVerifier([]))["failure"]["code"] == "SOURCE_BRANCH_NOT_CANONICAL"  # type: ignore[arg-type]


def test_source_upgrade_fast_forwards_and_rolls_back_with_git_reset(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.1.0\n")
    install = InstallInfo(
        method="source",
        version="1.0.0",
        python="python",
        repo_root=str(tmp_path),
        branch="development",
        head_sha="abc123",
    )
    runner = FakeRunner([("rev-parse HEAD", (0, "def456", ""))])
    bot = make_bot(tmp_path, install, FakeHttp({"latest": release_payload()}), runner)
    report = bot.run(verifier=FakeVerifier([False, True]))  # type: ignore[arg-type]
    assert runner.ran("git merge --ff-only origin/development")
    assert runner.ran("git reset --hard abc123")
    assert report["outcome"] == "rolled-back"


def test_live_lock_blocks_second_run(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install(), FakeHttp({"latest": release_payload()}), FakeRunner())
    bot.state_dir.mkdir(parents=True)
    bot.lock_file.write_text(str(os.getpid()))
    report = bot.run(verifier=FakeVerifier([True]))  # type: ignore[arg-type]
    assert report["failure"]["code"] == "UPGRADE_IN_PROGRESS"
    assert bot.lock_file.exists()  # someone else's lock is left alone


def test_stale_lock_is_reclaimed(tmp_path: Path) -> None:
    bot = make_bot(tmp_path, pip_install(), FakeHttp({"latest": release_payload()}), FakeRunner())
    bot.state_dir.mkdir(parents=True)
    bot.lock_file.write_text("999999999")
    assert bot.run(verifier=FakeVerifier([True]))["outcome"] == "upgraded"  # type: ignore[arg-type]


# ── verifier ──────────────────────────────────────────────────────────────────


def _cli_runner(version: str = "1.1.0", doctor_failed: int = 0, broken: Dict[str, str] | None = None) -> FakeRunner:
    env = {"data": {"version": version}}
    doctor = {"state": "ok", "data": {"counts": {"ok": 5, "failed": doctor_failed}}}
    scan = {"version": version, "total": 3, "failed": broken or {}}
    return FakeRunner(
        [
            ("--version", (0, json.dumps(env), "")),
            (" doctor", (0, json.dumps(doctor), "")),
            ("factory validate", (0, json.dumps({"state": "ok"}), "")),
            (" -c", (0, json.dumps(scan), "")),
        ]
    )


def test_verifier_passes_healthy_install(tmp_path: Path) -> None:
    v = UpgradeVerifierBot(cwd=tmp_path, runner=_cli_runner(), python="python")
    res = v.verify("1.1.0", baseline={"doctor_failed": 0})
    assert res["passed"], res
    assert {c["name"] for c in res["checks"]} == {"version", "command-imports", "doctor", "factory-validate"}


def test_verifier_detects_version_import_and_doctor_regressions(tmp_path: Path) -> None:
    v = UpgradeVerifierBot(
        cwd=tmp_path, runner=_cli_runner("1.0.0", 2, {"vision": "ImportError: torch"}), python="python"
    )
    res = v.verify("1.1.0", baseline={"doctor_failed": 0})
    failing = {c["name"] for c in res["checks"] if not c["passed"]}
    assert not res["passed"] and failing >= {"version", "command-imports", "doctor"}
    assert "vision" in next(c for c in res["checks"] if c["name"] == "command-imports")["detail"]


def test_verifier_full_level_runs_unit_tests_for_source(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    runner = _cli_runner()
    runner.rules.insert(0, ("pytest", (1, "", "1 failed, 10 passed")))
    res = UpgradeVerifierBot(cwd=tmp_path, runner=runner, python="python").verify(
        "1.1.0", level="full", repo_root=str(tmp_path)
    )
    assert not res["passed"] and "unit-tests" in res["summary"]


# ── announcer ─────────────────────────────────────────────────────────────────


FAILED_REPORT = {
    "run_id": "upg_1",
    "outcome": "rolled-back",
    "success": False,
    "from_version": "1.0.0",
    "to_version": "1.1.0",
    "install": {"method": "pip"},
    "failure": {"stage": "verify", "code": "VERIFICATION_FAILED", "message": "0/1 checks", "hint": "Fix the import."},
    "verification": {"checks": [{"name": "version", "passed": False, "required": True, "detail": "reported 1.0.0"}]},
    "rollback": {"success": True, "restored_version": "1.0.0"},
    "message": "Upgrade failed at verify: 0/1 checks",
}


def test_announcer_success_skips_issue(tmp_path: Path) -> None:
    runner = FakeRunner()
    res = UpgradeAnnouncerBot(cwd=tmp_path, runner=runner).announce(
        {"success": True, "outcome": "upgraded", "message": "ok"}, file_issue=True, speak=False
    )
    assert res["success"] and res["severity"] == "info" and not runner.ran("gh issue")


def test_announcer_files_issue_with_fix_hint(tmp_path: Path) -> None:
    runner = FakeRunner(
        [("issue list", (0, "[]", "")), ("issue create", (0, "https://github.com/Bayly-AI/HATH0R-CLI/issues/412", ""))]
    )
    res = UpgradeAnnouncerBot(cwd=tmp_path, runner=runner).announce(FAILED_REPORT, file_issue=True, speak=False)
    assert res["severity"] == "error" and "Fix the import." in res["message"]
    assert res["issue"]["number"] == 412 and "github-issue" in res["channels"]
    create = next(c for c in runner.calls if "create" in c)
    body = create[create.index("--body") + 1]
    assert "VERIFICATION_FAILED" in body and "Suggested fix" in body and "| version | ❌ |" in body


def test_announcer_deduplicates_open_issue(tmp_path: Path) -> None:
    bot = UpgradeAnnouncerBot(cwd=tmp_path)
    title = bot.issue_title(FAILED_REPORT)
    bot.runner = FakeRunner([("issue list", (0, json.dumps([{"number": 7, "title": title, "url": "u"}]), ""))])
    res = bot.file_issue(FAILED_REPORT)
    assert res["deduplicated"] and res["number"] == 7
    assert bot.runner.ran("gh issue comment 7") and not bot.runner.ran("issue create")  # type: ignore[attr-defined]


def test_announcer_retries_without_missing_labels(tmp_path: Path) -> None:
    runner = FakeRunner(
        [
            ("issue list", (0, "[]", "")),
            ("--label", (1, "", "could not add label: 'upgrade-bot' not found")),
            ("issue create", (0, "https://github.com/o/r/issues/9", "")),
        ]
    )
    res = UpgradeAnnouncerBot(cwd=tmp_path, runner=runner).file_issue(FAILED_REPORT)
    assert res["success"] and res["number"] == 9


def test_announcer_flags_rollback_failure_as_critical(tmp_path: Path) -> None:
    report = {**FAILED_REPORT, "outcome": "rollback-failed"}
    res = UpgradeAnnouncerBot(cwd=tmp_path, runner=FakeRunner()).announce(report, speak=False)
    assert res["severity"] == "critical" and res["message"].startswith("CRITICAL")


# ── CLI, factory and registry wiring ──────────────────────────────────────────


def test_upgrade_command_registered() -> None:
    from hath0r_cli.lazy_group import COMMAND_REGISTRY

    assert COMMAND_REGISTRY["upgrade"] == ("hath0r_cli.commands.upgrade", "upgrade")


def test_cli_status_and_schedule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from hath0r_cli.cli import main as cli

    monkeypatch.setenv("HATH0R_UPGRADE_HOME", str(tmp_path / "state"))
    runner = CliRunner()
    res = runner.invoke(cli, ["-o", "json", "upgrade", "status"])
    assert res.exit_code == 0, res.output
    assert json.loads(res.output)["data"]["last_run"] is None

    res = runner.invoke(cli, ["-o", "json", "upgrade", "schedule", "--hour", "3", "--minute", "41"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)["data"]
    assert "<integer>3</integer>" in data["plist"] and data["cron"].startswith("41 3 * * *")
    assert "--file-issue" in data["args"]


def test_cli_check_emits_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    from hath0r_cli.cli import main as cli

    monkeypatch.setattr(
        UpgradeBot,
        "check",
        lambda self, version=None: {
            "success": True,
            "install": {"method": "pip", "version": "1.0.0"},
            "latest_version": "1.1.0",
            "update_available": True,
            "message": "Update available: 1.0.0 → 1.1.0 (pip install).",
        },
    )
    res = CliRunner().invoke(cli, ["-o", "json", "upgrade", "check"])
    assert res.exit_code == 0, res.output
    env = json.loads(res.output)
    assert env["command"] == "upgrade.check" and env["data"]["update_available"] is True


def test_cli_run_failure_exit_code_and_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    from hath0r_cli.cli import main as cli

    monkeypatch.setattr(UpgradeBot, "run", lambda self, **kw: {**FAILED_REPORT, "exit_code": EXIT_FAILED, "stages": []})
    seen: Dict[str, Any] = {}

    def fake_announce(self: Any, report: Any, **kw: Any) -> Dict[str, Any]:
        seen.update(kw)
        return {"success": False, "message": "announced", "issue": {"url": "https://x/1"}}

    monkeypatch.setattr(UpgradeAnnouncerBot, "announce", fake_announce)
    res = CliRunner().invoke(cli, ["-o", "json", "upgrade", "run", "--file-issue", "--no-speak"])
    assert res.exit_code == EXIT_FAILED
    env = json.loads(res.output)
    assert env["state"] == "error" and env["diagnostics"][0]["code"] == "VERIFICATION_FAILED"
    assert seen == {"file_issue": True, "speak": False, "dry_run": False}


def test_factory_manifest_matches_registry() -> None:
    from hath0r_cli.step_runner import BotRegistry

    path = Path(__file__).resolve().parents[2] / "cfg" / "factories" / "upgrade-factory.yaml"
    manifest = yaml.safe_load(path.read_text())
    bot_ids = {b["id"] for b in manifest["bots"]}
    registered = set(BotRegistry().registered_bot_ids())
    assert bot_ids <= registered
    for wf in manifest["workflows"]:
        for step in wf["steps"]:
            assert step["bot"] in bot_ids
    root = path.parents[2]
    for doc in manifest["documentation"].values():
        assert (root / doc).exists(), f"missing documentation file {doc}"


def test_factory_announcer_step_reads_context() -> None:
    from hath0r_cli.step_runner import BotRegistry

    reg = BotRegistry()
    ctx: Dict[str, Any] = {"upgrade_report": FAILED_REPORT}
    res = reg.invoke(
        "upgrade-announcer-bot", "announce", {"file_issue": True, "speak": False}, dry_run=True, context=ctx
    )
    assert res.success is False  # the upgrade failed, so the workflow must fail visibly
    assert res.data["issue"]["dry_run"] is True
    ok = reg.invoke("upgrade-announcer-bot", "announce", {}, context={})
    assert ok.success is True


def test_child_env_drops_pythonpath(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verification must exercise the installed package, not a source tree on PYTHONPATH."""
    from hath0r_cli.bots.upgrade_bot import _child_env

    monkeypatch.setenv("PYTHONPATH", "/some/source/tree")
    monkeypatch.setenv("PYTHONHOME", "/x")
    env = _child_env()
    assert "PYTHONPATH" not in env and "PYTHONHOME" not in env
    assert env["HATH0R_UPGRADE_CHILD"] == "1"
