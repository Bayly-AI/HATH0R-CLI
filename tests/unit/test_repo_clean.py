"""Unit and workflow tests for repo-clean-factory and micro-bots."""

from pathlib import Path

from hath0r_cli.bots.repo_clean import (
    ConfigOrganizerBot,
    KnowledgeOrganizerBot,
    RepoHygieneBot,
)
from hath0r_cli.factory_validation import validate_factory_file
from hath0r_cli.step_runner import BotRegistry, execute_workflow


def test_repo_hygiene_bot_scan(tmp_path: Path):
    # Setup allowed root files
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    bot = RepoHygieneBot(cwd=tmp_path)
    res = bot.scan_root()
    assert res["success"] is True
    assert res["clean"] is True
    assert res["errant_count"] == 0

    # Add errant file
    (tmp_path / "rogue_dump.tmp").write_text("rogue", encoding="utf-8")
    res2 = bot.scan_root()
    assert res2["clean"] is False
    assert res2["errant_count"] == 1
    assert res2["errant_files"][0]["name"] == "rogue_dump.tmp"


def test_repo_hygiene_bot_clean(tmp_path: Path):
    bot = RepoHygieneBot(cwd=tmp_path)
    errant = tmp_path / "stray.log"
    errant.write_text("error", encoding="utf-8")

    # Dry-run
    res_dry = bot.clean_root(dry_run=True, archive_dir=".hath0r/spool/archive")
    assert res_dry["cleaned_count"] == 1
    assert errant.is_file()

    # Real clean
    res_real = bot.clean_root(dry_run=False, archive_dir=".hath0r/spool/archive")
    assert res_real["cleaned_count"] == 1
    assert not errant.is_file()
    assert (tmp_path / ".hath0r/spool/archive/stray.log").is_file()


def test_config_organizer_bot(tmp_path: Path):
    bot = ConfigOrganizerBot(cwd=tmp_path)
    # Essential config allowed
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    # Misplaced config
    (tmp_path / "extra-app-config.yaml").write_text("key: value\n", encoding="utf-8")

    scan = bot.scan_misplaced_configs()
    assert scan["clean"] is False
    assert scan["misplaced_count"] == 1
    assert scan["misplaced_configs"][0]["name"] == "extra-app-config.yaml"

    # Relocate
    reloc = bot.organize_configs(target_folder=".cfg", dry_run=False)
    assert reloc["count"] == 1
    assert not (tmp_path / "extra-app-config.yaml").is_file()
    assert (tmp_path / ".cfg/extra-app-config.yaml").is_file()


def test_knowledge_organizer_bot(tmp_path: Path):
    bot = KnowledgeOrganizerBot(cwd=tmp_path)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create modular file (small)
    (docs_dir / "short.md").write_text("# Modular Doc\nContent here.\n", encoding="utf-8")
    res1 = bot.audit_knowledge_structure()
    assert res1["organized"] is True

    # Create oversized monolithic file
    big_content = "\n".join([f"Line {i}" for i in range(500)])
    (docs_dir / "monolith.md").write_text(big_content, encoding="utf-8")

    res2 = bot.audit_knowledge_structure()
    assert res2["organized"] is False
    assert res2["findings_count"] == 1
    assert res2["findings"][0]["issue"] in ("monolithic_file", "oversized_monolithic_knowledge")


def test_repo_clean_factory_manifest():
    manifest_path = Path(__file__).resolve().parents[2] / "cfg" / "factories" / "repo-clean-factory.yaml"
    val = validate_factory_file(manifest_path)
    assert val.valid is True
    assert val.factory_id == "repo-clean-factory"
    assert val.bots_count == 3
    assert val.workflows_count == 2


def test_repo_clean_step_runner_workflow(tmp_path: Path):
    registry = BotRegistry(cwd=tmp_path)
    assert "repo-hygiene-bot" in registry.registered_bot_ids()
    assert "config-organizer-bot" in registry.registered_bot_ids()
    assert "knowledge-organizer-bot" in registry.registered_bot_ids()

    wf_def = {
        "id": "test-clean-wf",
        "name": "Test Clean Workflow",
        "steps": [
            {"bot": "repo-hygiene-bot", "action": "scan", "on_failure": "continue"},
            {"bot": "config-organizer-bot", "action": "scan", "on_failure": "continue"},
            {"bot": "knowledge-organizer-bot", "action": "audit", "on_failure": "continue"},
        ]
    }
    wf_res = execute_workflow(wf_def, registry, dry_run=True)
    assert wf_res.success is True
    assert len(wf_res.steps) == 3


def test_resolve_target_repos(tmp_path: Path):
    from hath0r_cli.cli import _resolve_target_repos

    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"
    repo1.mkdir()
    repo2.mkdir()
    (repo1 / ".git").mkdir()
    (repo2 / ".git").mkdir()

    # Specific repo
    res = _resolve_target_repos(str(repo1), all_repos=False)
    assert res == [repo1]

    # Mock group root for all_repos
    import os
    orig_env = os.environ.get("HATH0R_GROUP_ROOT")
    try:
        os.environ["HATH0R_GROUP_ROOT"] = str(tmp_path)
        (tmp_path / "AGENTS.md").write_text("hath0r-opensource", encoding="utf-8")
        (tmp_path / ".hath0r").mkdir()
        res_all = _resolve_target_repos(None, all_repos=True)
        assert len(res_all) == 2
        assert repo1 in res_all
        assert repo2 in res_all
    finally:
        if orig_env:
            os.environ["HATH0R_GROUP_ROOT"] = orig_env
        else:
            os.environ.pop("HATH0R_GROUP_ROOT", None)

