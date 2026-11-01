"""Unit tests for InstallWizardBot, hath0r install-wizard CLI commands, and scripts/install_hath0r.py."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from hath0r_cli.bots.install_wizard_bot import (
    DEFAULT_MCP_CONTAINER,
    DEFAULT_MCP_PORT,
    DEFAULT_NETWORK_NAME,
    EMBEDDED_MCP_COMPOSE,
    EMBEDDED_MCP_DOCKERFILE,
    InstallWizardBot,
    InstallWizardError,
    default_bin_dir,
    install_home,
)
from hath0r_cli.cli import main as cli
from hath0r_cli.step_runner import BotRegistry


def _make_runner(responses: List[Tuple[int, str, str]] | None = None) -> Any:
    queue = list(responses or [])
    calls: List[List[str]] = []

    def _runner(cmd: List[str], **kwargs: Any) -> Tuple[int, str, str]:
        calls.append(list(cmd))
        if queue:
            return queue.pop(0)
        return (0, "ok", "")

    _runner.calls = calls  # type: ignore[attr-defined]
    return _runner


class TestInstallWizardBotHelpersAndDependencies:
    def test_install_home_and_default_bin_dir_overrides(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        custom_home = tmp_path / "custom-hath0r"
        custom_bin = tmp_path / "custom-bin"
        monkeypatch.setenv("HATH0R_INSTALL_HOME", str(custom_home))
        monkeypatch.setenv("HATH0R_BIN_DIR", str(custom_bin))
        assert install_home() == custom_home.resolve()
        assert default_bin_dir() == custom_bin.resolve()

    def test_check_dependencies_all_present(self, tmp_path: Path) -> None:
        runner = _make_runner(
            [
                (0, "Docker Compose version v2.27.0\n", ""),
                (0, "Server Version: 26.1.0\n", ""),
            ]
        )
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path, bin_dir=tmp_path / "bin", runner=runner)
        with patch("shutil.which", side_effect=lambda name: f"/usr/local/bin/{name}"):
            deps = bot.check_dependencies()

        assert deps["python"]["ok"] is True
        assert deps["pipx"]["ok"] is True
        assert deps["git"]["ok"] is True
        assert deps["curl"]["ok"] is True
        assert deps["docker"]["ok"] is True
        assert deps["docker_compose"]["ok"] is True
        assert deps["docker_daemon"]["ok"] is True
        assert deps["missing"] == []
        assert deps["all_ready"] is True

    def test_check_dependencies_missing_docker_and_git(self, tmp_path: Path) -> None:
        runner = _make_runner([])
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path, bin_dir=tmp_path / "bin", runner=runner)
        with patch("shutil.which", side_effect=lambda name: None if name in ("git", "docker") else f"/usr/bin/{name}"):
            deps = bot.check_dependencies()

        assert "git" in deps["missing"]
        assert "docker" in deps["missing"]
        assert deps["all_ready"] is False

    def test_install_dependencies_dry_run(self, tmp_path: Path) -> None:
        runner = _make_runner([])
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path, bin_dir=tmp_path / "bin", runner=runner)
        fake_before: Dict[str, Any] = {
            "os": "darwin",
            "arch": "arm64",
            "platform_tag": "darwin-arm64",
            "package_manager": "brew",
            "python": {"ok": True, "version": "3.11.9", "executable": "python3"},
            "pipx": {"ok": False, "path": ""},
            "git": {"ok": False, "path": ""},
            "curl": {"ok": False, "path": ""},
            "docker": {"ok": False, "path": ""},
            "docker_compose": {"ok": False, "version": ""},
            "docker_daemon": {"ok": False, "detail": "not running"},
            "missing": ["git", "curl", "docker"],
            "all_ready": False,
        }
        with patch.object(bot, "check_dependencies", return_value=fake_before):
            res = bot.install_dependencies(need_pipx=True, need_docker=True, start_daemon=True, dry_run=True)

        assert res["success"] is True
        steps = [a["step"] for a in res["actions"]]
        assert "install-git" in steps
        assert "install-curl" in steps
        assert "install-pipx" in steps
        assert "install-docker" in steps
        assert "start-docker-daemon" in steps

    def test_install_dependencies_python_too_old_raises(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path, bin_dir=tmp_path / "bin")
        fake_before: Dict[str, Any] = {
            "os": "darwin",
            "package_manager": "brew",
            "python": {"ok": False, "version": "3.9.1", "executable": "python3"},
        }
        with patch.object(bot, "check_dependencies", return_value=fake_before):
            with pytest.raises(InstallWizardError) as exc_info:
                bot.install_dependencies(dry_run=False)
            assert exc_info.value.code == "PYTHON_TOO_OLD"

    def test_install_dependencies_executes_apt_and_daemon_start(self, tmp_path: Path) -> None:
        runner = _make_runner(
            [
                (0, "installed git", ""),
                (0, "installed pipx", ""),
                (0, "ensurepath ok", ""),
                (0, "installed docker", ""),
                (0, "started docker", ""),
                (0, "docker info ok", ""),
            ]
        )
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path, bin_dir=tmp_path / "bin", runner=runner)
        before_state: Dict[str, Any] = {
            "os": "linux",
            "arch": "x86_64",
            "platform_tag": "linux-x86_64",
            "package_manager": "apt",
            "python": {"ok": True, "version": "3.11.9", "executable": "python3"},
            "pipx": {"ok": False, "path": ""},
            "git": {"ok": False, "path": ""},
            "curl": {"ok": True, "path": "/usr/bin/curl"},
            "docker": {"ok": False, "path": ""},
            "docker_compose": {"ok": False, "version": ""},
            "docker_daemon": {"ok": False, "detail": "stopped"},
            "missing": ["git", "docker"],
            "all_ready": False,
        }
        after_state: Dict[str, Any] = {
            **before_state,
            "pipx": {"ok": True, "path": "/usr/bin/pipx"},
            "git": {"ok": True, "path": "/usr/bin/git"},
            "docker": {"ok": True, "path": "/usr/bin/docker"},
            "docker_compose": {"ok": True, "version": "v2.27.0"},
            "docker_daemon": {"ok": True, "detail": "running"},
            "missing": [],
            "all_ready": True,
        }
        with patch.object(bot, "check_dependencies", side_effect=[before_state, after_state]):
            res = bot.install_dependencies(need_pipx=True, need_docker=True, start_daemon=True, dry_run=False)

        assert res["success"] is True
        assert res["after"]["all_ready"] is True

    def test_install_dependencies_daemon_unavailable_raises(self, tmp_path: Path) -> None:
        runner = _make_runner([(1, "", "cannot start")])
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path, bin_dir=tmp_path / "bin", runner=runner)
        state: Dict[str, Any] = {
            "os": "darwin",
            "package_manager": "brew",
            "python": {"ok": True, "version": "3.11.9", "executable": "python3"},
            "pipx": {"ok": True, "path": "/opt/homebrew/bin/pipx"},
            "git": {"ok": True, "path": "/usr/bin/git"},
            "curl": {"ok": True, "path": "/usr/bin/curl"},
            "docker": {"ok": True, "path": "/usr/local/bin/docker"},
            "docker_compose": {"ok": True, "version": "v2.27.0"},
            "docker_daemon": {"ok": False, "detail": "Cannot connect to the Docker daemon"},
            "missing": [],
            "all_ready": False,
        }
        with (
            patch.object(bot, "check_dependencies", side_effect=[state, state]),
            patch("time.sleep"),
        ):
            with pytest.raises(InstallWizardError) as exc_info:
                bot.install_dependencies(need_pipx=False, need_docker=True, start_daemon=True, dry_run=False)
            assert exc_info.value.code == "DOCKER_DAEMON_UNAVAILABLE"


class TestInstallWizardBotGlobalCliInstall:
    def test_ensure_bin_on_path_updates_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("SHELL", "/bin/zsh")
        zshrc = tmp_path / ".zshrc"
        zshrc.write_text("# test zshrc\n", encoding="utf-8")
        bin_dir = tmp_path / "my-bin"
        bin_dir.mkdir(parents=True)

        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=bin_dir)
        res = bot.ensure_bin_on_path(bin_dir, dry_run=False)
        assert res["bin_dir"] == str(bin_dir.resolve())
        assert res["updated_profile"] == str(zshrc)
        assert str(bin_dir.resolve()) in zshrc.read_text(encoding="utf-8")

    def test_install_cli_global_invalid_method_raises(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        with pytest.raises(InstallWizardError) as exc_info:
            bot.install_cli_global(method="unknown-method")
        assert exc_info.value.code == "INVALID_INSTALL_METHOD"

    def test_install_cli_global_dry_run(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        res = bot.install_cli_global(method="pipx", dry_run=True)
        assert res["success"] is True
        assert res["dry_run"] is True
        assert res["method"] == "pipx"

    def test_install_cli_global_binary_from_local_release(self, tmp_path: Path) -> None:
        rel_dir = tmp_path / "release"
        rel_dir.mkdir(parents=True)
        sys_name = platform.system().lower()
        mach = platform.machine().lower()
        arch_x86 = "arm64" if mach in ("arm64", "aarch64") else "x86_64"
        local_bin_name = f"hath0r-{sys_name}-{arch_x86}"

        bin_file = rel_dir / local_bin_name
        payload = b"#!/bin/sh\necho 'hath0r 1.22.0'\n"
        bin_file.write_bytes(payload)
        bin_file.chmod(0o755)
        digest = hashlib.sha256(payload).hexdigest()
        (rel_dir / "CHECKSUMS.sha256").write_text(f"{digest}  {local_bin_name}\n", encoding="utf-8")

        target_bin_dir = tmp_path / "bin"
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=target_bin_dir)
        res = bot.install_cli_global(method="binary", version="1.22.0", dry_run=False)

        assert res["success"] is True
        assert res["method"] == "binary"
        assert res["source"] == "local_release"
        assert res["sha256"] == digest
        assert (target_bin_dir / "hath0r").is_file()

    def test_install_cli_global_binary_checksum_mismatch_raises(self, tmp_path: Path) -> None:
        rel_dir = tmp_path / "release"
        rel_dir.mkdir(parents=True)
        sys_name = platform.system().lower()
        mach = platform.machine().lower()
        arch_x86 = "arm64" if mach in ("arm64", "aarch64") else "x86_64"
        local_bin_name = f"hath0r-{sys_name}-{arch_x86}"

        bin_file = rel_dir / local_bin_name
        bin_file.write_bytes(b"corrupted-binary")
        (rel_dir / "CHECKSUMS.sha256").write_text(f"{'a' * 64}  {local_bin_name}\n", encoding="utf-8")

        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        with pytest.raises(InstallWizardError) as exc_info:
            bot.install_cli_global(method="binary", dry_run=False)
        assert exc_info.value.code == "CHECKSUM_MISMATCH"

    def test_install_cli_global_pipx_fallback_to_local_source(self, tmp_path: Path) -> None:
        runner = _make_runner([(0, "installed package hath0r-cli", "")])
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner)
        res = bot.install_cli_global(method="pipx", dry_run=False)
        assert res["success"] is True
        assert res["method"] == "pipx"


class TestInstallWizardBotMcpStagingAndLaunch:
    def test_stage_mcp_docker_embedded_fallback(self, tmp_path: Path) -> None:
        runner = _make_runner(
            [
                (1, "", "git clone failed"),  # git clone
                (0, "", ""),  # docker compose config --quiet
            ]
        )
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner)
        target_mcp = tmp_path / "mcp-staged"

        with patch.object(bot, "_locate_local_mcp_source", return_value=None):
            res = bot.stage_mcp_docker(mcp_dir=target_mcp, mcp_port=38083, dry_run=False)

        assert res["success"] is True
        assert res["source"] == "embedded_template"
        assert (target_mcp / "Dockerfile").read_text(encoding="utf-8") == EMBEDDED_MCP_DOCKERFILE
        assert (target_mcp / "docker-compose.yml").read_text(encoding="utf-8") == EMBEDDED_MCP_COMPOSE
        assert (target_mcp / "src" / "knowledgebase" / "server.py").is_file()
        assert (target_mcp / "knowledgebase" / "canonical" / "00-suite-overview.md").is_file()
        assert (target_mcp / ".env").is_file()

    def test_stage_mcp_docker_from_local_sibling_copy(self, tmp_path: Path) -> None:
        sibling = tmp_path / "hath0r-mcp"
        (sibling / "src" / "knowledgebase").mkdir(parents=True)
        (sibling / "knowledgebase" / "canonical").mkdir(parents=True)
        (sibling / "Dockerfile").write_text(EMBEDDED_MCP_DOCKERFILE, encoding="utf-8")
        (sibling / "docker-compose.yml").write_text(EMBEDDED_MCP_COMPOSE, encoding="utf-8")
        (sibling / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        (sibling / "src" / "knowledgebase" / "server.py").write_text("# server\n", encoding="utf-8")
        (sibling / "knowledgebase" / "canonical" / "doc.md").write_text("# doc\n", encoding="utf-8")

        runner = _make_runner([(0, "", "")])
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner)
        target_mcp = tmp_path / "custom-mcp"

        with patch.object(bot, "_locate_local_mcp_source", return_value=sibling):
            res = bot.stage_mcp_docker(mcp_dir=target_mcp, mcp_port=38083, dry_run=False)

        assert res["success"] is True
        assert res["source"] == "local_sibling_copy"
        assert (target_mcp / "Dockerfile").is_file()
        assert (target_mcp / "knowledgebase" / "canonical" / "doc.md").is_file()

    def test_ensure_docker_network_creates_when_missing(self, tmp_path: Path) -> None:
        runner = _make_runner(
            [
                (1, "", "No such network: hath0r-net"),
                (0, "net-id-123\n", ""),
            ]
        )
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner)
        res = bot.ensure_docker_network(DEFAULT_NETWORK_NAME, dry_run=False)
        assert res["success"] is True
        assert res["created"] is True
        assert res["network"] == DEFAULT_NETWORK_NAME

    def test_launch_mcp_container_local_build_and_image_pull(self, tmp_path: Path) -> None:
        mcp_dir = tmp_path / "mcp"
        mcp_dir.mkdir(parents=True)
        (mcp_dir / "docker-compose.yml").write_text(EMBEDDED_MCP_COMPOSE, encoding="utf-8")

        runner = _make_runner(
            [
                (0, "network exists", ""),  # docker network inspect
                (0, "Container Hath0r-MCP Started", ""),  # docker compose up
                (0, "health=healthy status=running\n", ""),  # docker inspect
            ]
        )
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner)
        res = bot.launch_mcp_container(mcp_dir, mcp_port=38083, dry_run=False)
        assert res["success"] is True
        assert res["container_name"] == DEFAULT_MCP_CONTAINER
        assert "health=healthy" in res["container_status"]

        runner_pull = _make_runner(
            [
                (0, "network exists", ""),  # docker network inspect
                (0, "pulled image", ""),  # docker pull
                (0, "tagged image", ""),  # docker tag
                (0, "Container Hath0r-MCP Started", ""),  # docker compose up
                (0, "health=healthy status=running\n", ""),  # docker inspect
            ]
        )
        bot_pull = InstallWizardBot(
            cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner_pull
        )
        res_pull = bot_pull.launch_mcp_container(
            mcp_dir, mcp_port=38083, image_url="ghcr.io/bayly-ai/hath0r-mcp:latest", dry_run=False
        )
        assert res_pull["success"] is True
        assert res_pull["image"] == "ghcr.io/bayly-ai/hath0r-mcp:latest"

    def test_probe_mcp_ready_and_configure_client_files(self, tmp_path: Path) -> None:
        def fake_http(url: str, headers: Dict[str, str]) -> bytes:
            if url.endswith("/health"):
                return json.dumps({"status": "healthy", "service": "hath0r-mcp"}).encode("utf-8")
            return json.dumps({"status": "ready", "documents_loaded": 12}).encode("utf-8")

        bot = InstallWizardBot(
            cwd=tmp_path,
            home_dir=tmp_path / ".hath0r",
            bin_dir=tmp_path / "bin",
            http_get=fake_http,
        )
        probe = bot.probe_mcp_ready(port=38083, retries=2, delay_s=0.01)
        assert probe["passed"] is True
        assert probe["health"]["status"] == "healthy"
        assert probe["ready"]["status"] == "ready"

        cfg = bot.configure_mcp_client_files(mcp_port=38083, mcp_dir=tmp_path / "mcp", dry_run=False)
        user_mcp = Path(cfg["user_mcp_file"])
        assert user_mcp.is_file()
        parsed = json.loads(user_mcp.read_text(encoding="utf-8"))
        assert parsed["default_server"] == "hath0r-mcp"
        assert parsed["servers"][0]["base_url"] == "http://127.0.0.1:38083"


class TestInstallWizardBotOrchestrationAndLifecycle:
    def test_run_wizard_dry_run(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        report = bot.run_wizard(
            method="pipx",
            mcp_dir=tmp_path / "mcp",
            mcp_port=DEFAULT_MCP_PORT,
            skip_docker=False,
            dry_run=True,
        )
        assert report["success"] is True
        assert report["outcome"] == "dry-run"
        assert len(report["stages"]) == 5

    def test_run_wizard_skip_docker_persists_receipt_and_status(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        with (
            patch.object(
                bot,
                "install_dependencies",
                return_value={"success": True, "before": {}, "after": {"all_ready": True}, "actions": []},
            ),
            patch.object(
                bot,
                "install_cli_global",
                return_value={
                    "success": True,
                    "method": "pipx",
                    "version": "1.22.0",
                    "binary_path": "/usr/local/bin/hath0r",
                    "sha256": "deadbeef",
                },
            ),
            patch.object(
                bot,
                "stage_mcp_docker",
                return_value={
                    "success": True,
                    "source": "embedded_template",
                    "mcp_dir": str(tmp_path / "mcp"),
                    "dockerfile": str(tmp_path / "mcp" / "Dockerfile"),
                    "compose_file": str(tmp_path / "mcp" / "docker-compose.yml"),
                    "host_port": 38083,
                },
            ),
            patch("hath0r_cli.bots.install_wizard_bot.UpgradeVerifierBot.verify", return_value={"passed": True}),
        ):
            report = bot.run_wizard(
                method="pipx",
                mcp_dir=tmp_path / "mcp",
                mcp_port=38083,
                skip_docker=True,
                dry_run=False,
            )

        assert report["success"] is True
        assert report["outcome"] == "installed"
        assert bot.receipt_file.is_file()
        assert bot.history_file.is_file()

        st = bot.status(mcp_port=38083)
        assert st["success"] is True
        assert st["last_receipt"]["outcome"] == "installed"

    def test_run_wizard_records_failure_stage(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        with patch.object(
            bot,
            "install_dependencies",
            side_effect=InstallWizardError("dependencies", "DOCKER_DAEMON_UNAVAILABLE", "Daemon stopped", "Start Docker"),
        ):
            report = bot.run_wizard(dry_run=False)

        assert report["success"] is False
        assert report["outcome"] == "failed"
        assert report["failure"]["code"] == "DOCKER_DAEMON_UNAVAILABLE"

    def test_repair_and_uninstall_dry_run(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        rep = bot.repair(mcp_dir=tmp_path / "mcp", mcp_port=38083, dry_run=True)
        assert rep["success"] is True
        assert rep["dry_run"] is True

        uninst = bot.uninstall(mcp_dir=tmp_path / "mcp", purge_data=True, dry_run=True)
        assert uninst["success"] is True
        assert uninst["dry_run"] is True


class TestInstallWizardCliAndRegistry:
    def test_cli_install_wizard_and_setup_commands(self) -> None:
        runner = CliRunner()
        res_help = runner.invoke(cli, ["install-wizard", "--help"])
        assert res_help.exit_code == 0
        assert "run" in res_help.output
        assert "check" in res_help.output
        assert "status" in res_help.output
        assert "repair" in res_help.output
        assert "uninstall" in res_help.output

        res_setup = runner.invoke(cli, ["setup", "--help"])
        assert res_setup.exit_code == 0

        res_dry = runner.invoke(cli, ["--output", "json", "install-wizard", "run", "--dry-run"])
        assert res_dry.exit_code == 0
        payload = json.loads(res_dry.output)
        assert payload["state"] == "ok"
        assert payload["data"]["success"] is True

        res_rep = runner.invoke(cli, ["--output", "json", "install-wizard", "repair", "--dry-run"])
        assert res_rep.exit_code == 0
        assert json.loads(res_rep.output)["state"] == "ok"

        res_uninst = runner.invoke(cli, ["--output", "json", "install-wizard", "uninstall", "--dry-run"])
        assert res_uninst.exit_code == 0
        assert json.loads(res_uninst.output)["state"] == "ok"

        # Text output mode coverage for all subcommands
        res_no_sub = runner.invoke(cli, ["install-wizard"])
        assert res_no_sub.exit_code == 0

        res_text_run = runner.invoke(cli, ["--output", "text", "install-wizard", "run", "--dry-run"])
        assert res_text_run.exit_code == 0

        res_text_rep = runner.invoke(cli, ["--output", "text", "install-wizard", "repair", "--dry-run"])
        assert res_text_rep.exit_code == 0

        res_text_uninst = runner.invoke(cli, ["--output", "text", "install-wizard", "uninstall", "--dry-run"])
        assert res_text_uninst.exit_code == 0

        with patch.object(
            InstallWizardBot,
            "check_environment",
            return_value={
                "success": True,
                "healthy": True,
                "dependencies": {
                    "python": {"ok": True, "version": "3.11.9"},
                    "pipx": {"ok": True, "path": "/usr/local/bin/pipx"},
                    "git": {"ok": True, "path": "/usr/bin/git"},
                    "curl": {"ok": True, "path": "/usr/bin/curl"},
                    "docker": {"ok": True, "path": "/usr/local/bin/docker"},
                    "docker_compose": {"ok": True, "version": "v2.27.0"},
                    "docker_daemon": {"ok": True, "detail": "running"},
                },
                "cli": {"on_path": True, "version": "1.22.0", "method": "pipx", "which": "/usr/local/bin/hath0r"},
                "mcp_docker": {
                    "network": "hath0r-net",
                    "network_present": True,
                    "container_name": "Hath0r-MCP",
                    "container_running": True,
                    "port": 38083,
                    "ready": True,
                },
            },
        ):
            res_chk = runner.invoke(cli, ["--output", "text", "install-wizard", "check"])
            assert res_chk.exit_code == 0
            res_st = runner.invoke(cli, ["--output", "text", "install-wizard", "status"])
            assert res_st.exit_code == 0

        with patch.object(
            InstallWizardBot,
            "run_wizard",
            return_value={
                "success": False,
                "outcome": "failed",
                "message": "Failed",
                "stages": [{"stage": "dependencies", "status": "failed", "code": "DEPENDENCY_MISSING"}],
                "failure": {
                    "stage": "dependencies",
                    "code": "DEPENDENCY_MISSING",
                    "message": "Docker missing",
                    "hint": "Install Docker",
                },
            },
        ):
            res_fail = runner.invoke(cli, ["--output", "text", "install-wizard", "run", "-y"])
            assert res_fail.exit_code == 1

    def test_error_branches_and_uninstall_live(self, tmp_path: Path) -> None:
        runner = _make_runner(
            [
                (1, "", "compose invalid"),  # docker compose config --quiet
            ]
        )
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin", runner=runner)
        with (
            patch.object(bot, "_locate_local_mcp_source", return_value=None),
            patch("shutil.which", side_effect=lambda name: "/usr/local/bin/docker" if name == "docker" else None),
        ):
            with pytest.raises(InstallWizardError) as exc_info:
                bot.stage_mcp_docker(mcp_dir=tmp_path / "mcp", dry_run=False)
            assert exc_info.value.code == "COMPOSE_CONFIG_INVALID"

        # Network create failure
        bot_net = InstallWizardBot(
            cwd=tmp_path,
            home_dir=tmp_path / ".hath0r",
            bin_dir=tmp_path / "bin",
            runner=_make_runner([(1, "", "missing"), (1, "", "create err")]),
        )
        with pytest.raises(InstallWizardError) as exc_net:
            bot_net.ensure_docker_network("hath0r-net", dry_run=False)
        assert exc_net.value.code == "DOCKER_NETWORK_FAILED"

        # Uninstall non-dry-run with purge_data
        mcp_default = bot.default_mcp_dir
        mcp_default.mkdir(parents=True, exist_ok=True)
        (mcp_default / "docker-compose.yml").write_text(EMBEDDED_MCP_COMPOSE, encoding="utf-8")
        bot_un = InstallWizardBot(
            cwd=tmp_path,
            home_dir=tmp_path / ".hath0r",
            bin_dir=tmp_path / "bin",
            runner=_make_runner([(0, "removed", "")]),
        )
        un_res = bot_un.uninstall(mcp_dir=mcp_default, purge_data=True, dry_run=False)
        assert un_res["success"] is True
        assert un_res["purged_dir"] is True

    def test_build_macos_dmg_and_windows_exe(self, tmp_path: Path) -> None:
        bot = InstallWizardBot(cwd=tmp_path, home_dir=tmp_path / ".hath0r", bin_dir=tmp_path / "bin")
        dry = bot.build_installers(out_dir=tmp_path / "out", version="1.22.0", target="all", dry_run=True)
        assert dry["success"] is True
        assert dry["macos_dmg"]["dry_run"] is True
        assert dry["windows_exe"]["dry_run"] is True

        # Live build of macOS DMG and Windows EXE into tmp_path
        live = bot.build_installers(out_dir=tmp_path / "live-out", version="1.22.0", target="all", dry_run=False)
        assert live["success"] is True
        dmg_file = Path(live["macos_dmg"]["dmg_path"])
        exe_file = Path(live["windows_exe"]["exe_path"])
        assert dmg_file.is_file()
        assert dmg_file.stat().st_size > 0
        assert exe_file.is_file()
        assert exe_file.read_bytes()[:2] == b"MZ"  # Valid DOS/PE32+ header

        runner = CliRunner()
        res_pkg = runner.invoke(
            cli,
            ["--output", "text", "install-wizard", "package", "--target", "all", "--out-dir", str(tmp_path / "cli-out"), "--dry-run"],
        )
        assert res_pkg.exit_code == 0

    def test_bot_registry_and_factory_manifest(self, tmp_path: Path) -> None:
        cli_root = Path(__file__).resolve().parents[2]
        factory_path = cli_root / "cfg" / "factories" / "install-wizard-factory.yaml"
        assert factory_path.is_file()
        manifest = yaml.safe_load(factory_path.read_text(encoding="utf-8"))
        assert manifest["factory_id"] == "install-wizard-factory"
        assert len(manifest["workflows"]) == 4

        registry = BotRegistry(cwd=tmp_path)
        assert "install-wizard-bot" in registry.registered_bot_ids()
        out = registry.invoke(
            "install-wizard-bot",
            "run",
            {"method": "pipx", "skip_docker": True},
            dry_run=True,
        )
        assert out.success is True
        assert out.data["success"] is True

    def test_scripts_install_hath0r_dry_run(self) -> None:
        cli_root = Path(__file__).resolve().parents[2]
        script = cli_root / "scripts" / "install_hath0r.py"
        proc = subprocess.run(
            ["python3", str(script), "--dry-run", "-y"],
            cwd=cli_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "Stage 1/5" in proc.stdout
        assert "Stage 2/5" in proc.stdout
