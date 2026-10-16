"""Tests for Local Memory Space, MemoryGraph compounding, and pre-announcement gate (CR-MEMORY-COMPOUND-001)."""

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots import TaskAnnouncerBot
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.cli import main


def test_memory_manager_bot_init_and_read(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    init_res = bot.init_memory()
    assert init_res["success"] is True

    rules_content = bot.read_topic("rules")
    assert rules_content is not None
    assert "CR-CLI-ENTRY-001" in rules_content
    assert "CR-MEMORY-COMPOUND-001" in rules_content

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


def test_memory_compounding_and_pre_announcement_gate(tmp_path: Path) -> None:
    bot = MemoryManagerBot(cwd=tmp_path)
    bot.initialize_memory()
    announcer = TaskAnnouncerBot(cwd=tmp_path)

    # Gate fails before any task knowledge is compounded
    ver_before = bot.verify_compounded()
    assert ver_before["compounded"] is False
    ann_blocked = announcer.announce_complete(task_id="issue-472", dry_run=False)
    assert ann_blocked["success"] is False
    assert "CR-MEMORY-COMPOUND-001" in str(ann_blocked.get("error"))

    # Compound first episode
    c1 = bot.compound_memory(
        label="Enforce .hath0r/memory across all repos",
        content="Added compound, verify, reflect, and ensure-all to MemoryManagerBot.",
        node_type="episode",
        tags=["memorygraph", "governance"],
        sync_agentgraph=False,
    )
    assert c1["success"] is True

    # Gate now passes and TaskAnnouncerBot succeeds
    ver_after = bot.verify_compounded()
    assert ver_after["compounded"] is True
    ann_passed = announcer.announce_complete(task_id="issue-472", dry_run=False)
    assert ann_passed["success"] is True

    # Compound second decision sharing tag 'memorygraph' -> synthesizes insight node
    c2 = bot.compound_memory(
        label="Pre-Announcement Gate Decision",
        content="TaskAnnouncerBot blocks announcement until verify_compounded passes.",
        node_type="decision",
        tags=["memorygraph", "governance"],
        sync_agentgraph=False,
    )
    assert c2["success"] is True
    assert c2["reflection"]["insights_generated"] >= 1


def test_ensure_all_repos(tmp_path: Path) -> None:
    repo_a = tmp_path / "repo-alpha"
    repo_b = tmp_path / "repo-beta"
    (repo_a / ".git").mkdir(parents=True)
    (repo_b / ".git").mkdir(parents=True)
    (repo_a / "README.md").write_text("# Repo Alpha\nAlpha service repository.", encoding="utf-8")

    bot = MemoryManagerBot(cwd=tmp_path)
    res = bot.ensure_all_repos(root_dir=tmp_path, sync_agentgraph=False)
    assert res["success"] is True
    assert res["repos_count"] == 2
    assert (repo_a / ".hath0r" / "memory" / "graph.json").is_file()
    assert (repo_b / ".hath0r" / "memory" / "graph.json").is_file()


def test_memory_cli_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        res_init = runner.invoke(main, ["memory", "init"])
        assert res_init.exit_code == 0
        assert "Initialized" in res_init.output or "Local Memory Space" in res_init.output

        # Verify fails before compounding
        res_ver_fail = runner.invoke(main, ["memory", "verify"])
        assert res_ver_fail.exit_code != 0

        # Compound via CLI
        res_comp = runner.invoke(
            main,
            [
                "memory",
                "compound",
                "--label",
                "CLI Compounding Test",
                "--content",
                "Verified CLI memory compound command.",
                "--type",
                "episode",
                "--tags",
                "cli,memorygraph",
                "--no-sync",
            ],
        )
        assert res_comp.exit_code == 0

        # Verify passes after compounding
        res_ver_ok = runner.invoke(main, ["memory", "verify"])
        assert res_ver_ok.exit_code == 0
        assert "PASSED" in res_ver_ok.output or '"compounded":' in res_ver_ok.output

        res_read = runner.invoke(main, ["memory", "read", "rules"])
        assert res_read.exit_code == 0
        assert "Rules" in res_read.output or "CR-CLI-ENTRY-001" in res_read.output
