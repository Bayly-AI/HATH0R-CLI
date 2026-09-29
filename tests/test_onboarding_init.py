"""Tests for hath0r init and universal repo-onboarding-factory."""

from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.onboarding import (
    DocRefactorBot,
    GovernanceBot,
    RepoLayoutBot,
    TestHarnessBot,
    TriGraphIngestBot,
)
from hath0r_cli.cli import main


def test_onboarding_bots_unit(tmp_path: Path) -> None:
    # 1. Layout & Backup
    layout_bot = RepoLayoutBot(cwd=tmp_path)
    (tmp_path / "README.md").write_text("# Existing Repo\n")
    backup_res = layout_bot.backup_state()
    assert backup_res["success"] is True
    assert "README.md" in backup_res["files_backed_up"]

    scaffold_res = layout_bot.scaffold_layout()
    assert scaffold_res["success"] is True
    assert (tmp_path / ".hath0r" / "memory").exists()
    assert (tmp_path / "contracts" / "schemas").exists()

    # 2. Governance
    gov_bot = GovernanceBot(cwd=tmp_path)
    agents_res = gov_bot.scaffold_agents_md(product_name="MockService")
    assert agents_res["success"] is True
    assert (tmp_path / "AGENTS.md").exists()
    assert "CR-CLI-ENTRY-001" in (tmp_path / "AGENTS.md").read_text()

    ver_res = gov_bot.init_versioning("1.0.0")
    assert ver_res["success"] is True
    assert (tmp_path / "VERSION").read_text().strip() == "1.0.0"

    # 3. Doc Refactor
    doc_bot = DocRefactorBot(cwd=tmp_path)
    tech_res = doc_bot.scaffold_tech_readme(product_name="MockService")
    assert tech_res["success"] is True
    assert (tmp_path / "TECH_README.md").exists()

    pb_res = doc_bot.seed_playbooks()
    assert pb_res["success"] is True
    assert (tmp_path / "docs" / "governance" / "playbooks" / "playbook-coding.md").exists()

    # 4. Test Harness
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'mock'\n")
    harness_bot = TestHarnessBot(cwd=tmp_path)
    det = harness_bot.detect_stack()
    assert det["stack"] == "python"
    test_res = harness_bot.scaffold_tests()
    assert test_res["success"] is True
    assert (tmp_path / "tests" / "test_smoke.py").exists()

    # 5. Tri-Graph Ingestion
    tri_bot = TriGraphIngestBot(cwd=tmp_path)
    kg_res = tri_bot.compile_knowledge_graph()
    assert kg_res["success"] is True
    assert (tmp_path / ".hath0r" / "state" / "cache" / "knowledge.json").exists()

    mg_res = tri_bot.ingest_memory_graph()
    assert mg_res["success"] is True
    assert (tmp_path / ".hath0r" / "memory" / "graph.json").exists()

    # 6. CI Workflows Sync
    sync_res = layout_bot.sync_ci_workflows()
    assert sync_res["success"] is True
    assert (tmp_path / ".github" / "workflows" / "enforce-promotion-path.yml").exists()

    # 7. Rollback
    rollback_res = layout_bot.rollback_init()
    assert rollback_res["success"] is True
    assert (tmp_path / "README.md").read_text() == "# Existing Repo\n"


def test_hath0r_init_cli_dry_run() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dry-run"])
    assert result.exit_code == 0
    assert '"command":"init"' in result.output
    assert '"state":"ok"' in result.output


def test_hath0r_init_cli_sync_ci(tmp_path: Path) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["--output", "json", "init", "--sync-ci"])
        assert result.exit_code == 0
        assert '"sync_ci":true' in result.output
        assert Path(".github/workflows/enforce-promotion-path.yml").exists()
