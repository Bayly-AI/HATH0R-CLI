"""Unit tests for WorktreeManager and hath0r branch worktree CLI commands."""

import subprocess
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.worktree_manager import WorktreeManager


def test_worktree_manager_list():
    """Verify listing worktrees in the current repo."""
    mgr = WorktreeManager()
    wts = mgr.list_worktrees()
    assert len(wts) >= 1
    assert any(w.is_main for w in wts)


def test_worktree_lifecycle(tmp_path: Path):
    """Verify git worktree creation, listing, and removal in temporary repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(repo), check=True)

    dummy_file = repo / "README.md"
    dummy_file.write_text("Hello World", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(repo), check=True, capture_output=True)

    mgr = WorktreeManager(repo_root=repo)
    wts_init = mgr.list_worktrees()
    assert len(wts_init) == 1

    # Create worktree
    res_create = mgr.create_worktree(branch="feature-sandbox", task_id="task-999", create_branch=True, base_branch="main")
    assert res_create["success"] is True
    assert Path(res_create["path"]).exists()

    # List worktrees
    wts_after = mgr.list_worktrees()
    assert len(wts_after) == 2

    # Remove worktree
    res_remove = mgr.remove_worktree(target="task-999", force=True)
    assert res_remove["success"] is True
    assert not Path(res_create["path"]).exists()


def test_cli_worktree_commands():
    """Verify hath0r branch worktree list and prune commands."""
    runner = CliRunner()
    res_list = runner.invoke(cli, ["-o", "json", "branch", "worktree", "list"])
    assert res_list.exit_code == 0
    assert "worktrees" in res_list.output

    res_prune = runner.invoke(cli, ["-o", "json", "branch", "worktree", "prune"])
    assert res_prune.exit_code == 0
    assert "ok" in res_prune.output
