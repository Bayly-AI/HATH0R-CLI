"""Tests for Local Memory Space and MemoryManagerBot."""

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.cli import main


def test_memory_manager_bot_init_and_read(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    init_res = bot.init_memory()
    assert init_res["success"] is True

    rules_content = bot.read_topic("rules")
    assert rules_content is not None
    assert "CR-CLI-ENTRY-001" in rules_content

    arch_content = bot.read_topic("architecture")
    assert arch_content is not None
    assert "HATH0R" in arch_content


def test_memory_manager_bot_update(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.init_memory()

    update_res = bot.update_topic("custom_topic", "custom content for testing")
    assert update_res["success"] is True

    read_back = bot.read_topic("custom_topic")
    assert read_back == "custom content for testing"


def test_memory_cli_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res_init = runner.invoke(main, ["memory", "init"])
        assert res_init.exit_code == 0
        assert "Initialized" in res_init.output or "Local Memory Space" in res_init.output

        res_read = runner.invoke(main, ["memory", "read", "rules"])
        assert res_read.exit_code == 0
        assert "Rules" in res_read.output or "CR-CLI-ENTRY-001" in res_read.output
