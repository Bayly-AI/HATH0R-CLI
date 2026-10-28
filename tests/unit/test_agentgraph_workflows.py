"""Tests for AgentGraph integration into Preflight, PR Bot, and Clean-Repo workflows."""

from __future__ import annotations

from pathlib import Path

from hath0r_cli.bots import PRBot
from hath0r_cli.bots.agentgraph_bot import AgentGraphBot
from hath0r_cli.bots.quality import PreflightBot
from hath0r_cli.bots.repo_clean import CleanReposWorkflowBot


def test_preflight_passes_with_valid_agentgraph(tmp_path: Path):
    """Preflight passes when AgentGraph is valid."""
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    bot = AgentGraphBot(cwd=tmp_path)
    bot.sync(persist=True)

    preflight = PreflightBot(cwd=tmp_path)
    ag_check = preflight._agentgraph_ok()
    assert ag_check["ok"] is True
    assert "AgentGraph valid" in ag_check["message"]


def test_preflight_fails_with_cyclic_agentgraph(tmp_path: Path):
    """Preflight fails when cyclic inheritance dependencies exist in AgentGraph."""
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    bot = AgentGraphBot(cwd=tmp_path)
    graph = {
        "schema_version": "hath0r.agentgraph/1",
        "graph_id": "test-preflight-fail",
        "nodes": [
            {"id": "role:x", "plane": "rules", "type": "agent_role", "label": "Role X"},
            {"id": "role:y", "plane": "rules", "type": "agent_role", "label": "Role Y"},
        ],
        "edges": [
            {"source": "role:x", "target": "role:y", "relation": "INHERITS_FROM", "is_current": True},
            {"source": "role:y", "target": "role:x", "relation": "INHERITS_FROM", "is_current": True},
        ],
    }
    bot.save_graph(graph, target_path=str(tmp_path))

    preflight = PreflightBot(cwd=tmp_path)
    ag_check = preflight._agentgraph_ok()
    assert ag_check["ok"] is False
    assert "Cyclic inheritance" in ag_check["error"]


def test_pr_bot_injects_agentgraph_summary(tmp_path: Path):
    """PR Bot injects AgentGraph audit summaries into PR descriptions."""
    bot = AgentGraphBot(cwd=tmp_path)
    bot.sync(persist=True)

    pr_bot = PRBot(cwd=tmp_path)
    res = pr_bot.create_pr(
        title="feat: test pr",
        body="Initial description",
        dry_run=True,
    )
    assert res["success"] is True
    assert "### AgentGraph Audit Summary" in res["body"]
    assert "Cycles Detected" in res["body"]


def test_repo_clean_step7_agentgraph_sync(tmp_path: Path):
    """RepoCleanLifecycleBot Step 7 runs agentgraph sync and validate."""
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
    (tmp_path / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "branch", "-M", "development"], cwd=tmp_path, check=True)

    clean_bot = CleanReposWorkflowBot(cwd=tmp_path)
    res = clean_bot.run_clean_repo_workflow(target_repos=[tmp_path], auto_commit=False)

    repo_report = res["repos"][0]
    step7 = repo_report["steps"].get("7_update_documentation")
    assert step7 is not None
    assert step7["agentgraph_synced"] is True
    assert step7["agentgraph_valid"] is True
    assert (tmp_path / ".hath0r" / "agentgraph" / "snapshot.json").is_file()


def test_clean_repo_branch_merge_conflict_resolution_and_prune(tmp_path: Path):
    """CleanReposWorkflowBot merges feature branches with changes, resolves conflicts, and deletes stale branches."""
    import subprocess

    bare_remote = tmp_path / "origin.git"
    bare_remote.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=bare_remote, check=True)

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare_remote)], cwd=repo_dir, check=True)

    (repo_dir / "AGENTS.md").write_text("# Agents\nLine 1\n", encoding="utf-8")
    (repo_dir / "README.md").write_text("# Readme\n", encoding="utf-8")
    (repo_dir / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "branch", "-M", "development"], cwd=repo_dir, check=True)
    subprocess.run(["git", "push", "-u", "origin", "development"], cwd=repo_dir, check=True)

    # Create a stale remote branch with 0 new commits
    subprocess.run(["git", "checkout", "-b", "chore/stale-branch"], cwd=repo_dir, check=True)
    subprocess.run(["git", "push", "-u", "origin", "chore/stale-branch"], cwd=repo_dir, check=True)

    # Create a feature branch with unmerged changes AND a conflict on AGENTS.md
    subprocess.run(["git", "checkout", "-b", "feature/new-capability", "development"], cwd=repo_dir, check=True)
    (repo_dir / "AGENTS.md").write_text("# Agents\nFeature branch line\n", encoding="utf-8")
    (repo_dir / "feature.txt").write_text("new feature payload\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "feat: add feature payload"], cwd=repo_dir, check=True)
    subprocess.run(["git", "push", "-u", "origin", "feature/new-capability"], cwd=repo_dir, check=True)

    # Advance development on AGENTS.md to trigger a merge conflict
    subprocess.run(["git", "checkout", "development"], cwd=repo_dir, check=True)
    (repo_dir / "AGENTS.md").write_text("# Agents\nCanonical development line\n", encoding="utf-8")
    subprocess.run(["git", "add", "AGENTS.md"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "docs: update canonical agents"], cwd=repo_dir, check=True)
    subprocess.run(["git", "push", "origin", "development"], cwd=repo_dir, check=True)

    # Switch onto feature branch before running workflow to verify it switches back to development
    subprocess.run(["git", "checkout", "feature/new-capability"], cwd=repo_dir, check=True)

    clean_bot = CleanReposWorkflowBot(cwd=repo_dir)
    res = clean_bot.run_clean_repo_workflow(target_repos=[repo_dir], auto_commit=True)

    repo_report = res["repos"][0]
    step9_10 = repo_report["steps"]["9_10_pr_status"]
    step11 = repo_report["steps"]["11_delete_feature_branches"]
    step12 = repo_report["steps"]["12_return_to_development"]

    assert "feature/new-capability" in step9_10["merged_branches"]
    assert "feature/new-capability" in step9_10["conflicts_resolved"]
    assert "feature/new-capability" in step11["deleted_local"]
    assert "chore/stale-branch" in step11["deleted_local"]
    assert "feature/new-capability" in step11["deleted_remote"]
    assert "chore/stale-branch" in step11["deleted_remote"]
    assert step12["branch"] == "development"
    assert step12["pushed_origin"] is True

    # Verify feature.txt from the merged branch exists on development and AGENTS.md kept canonical line
    assert (repo_dir / "feature.txt").read_text(encoding="utf-8") == "new feature payload\n"
    assert "Canonical development line" in (repo_dir / "AGENTS.md").read_text(encoding="utf-8")

    # Verify only development remains locally and remotely
    local_branches = CleanReposWorkflowBot._git_out(
        repo_dir, ["for-each-ref", "--format=%(refname:short)", "refs/heads/"]
    ).splitlines()
    assert local_branches == ["development"]


def test_clean_repo_worktree_detach_and_tree_conflict_resolution(tmp_path: Path):
    """CleanReposWorkflowBot detaches secondary feature worktrees and resolves modify/delete tree conflicts."""
    import shutil
    import subprocess

    repo_dir = tmp_path / "main_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)

    (repo_dir / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (repo_dir / "README.md").write_text("# Readme\n", encoding="utf-8")
    (repo_dir / "shared.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_dir, check=True)

    assert CleanReposWorkflowBot._detect_base_branch(repo_dir) == "main"
    assert CleanReposWorkflowBot._is_canonical_branch("dependabot/pip/pytest") is True

    # 1. Create a secondary worktree on feature/wt-branch (clean merge)
    wt_dir = tmp_path / "wt_feature"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/wt-branch", str(wt_dir), "main"],
        cwd=repo_dir,
        check=True,
    )
    (wt_dir / "wt_file.txt").write_text("from worktree\n", encoding="utf-8")
    subprocess.run(["git", "add", "wt_file.txt"], cwd=wt_dir, check=True)
    subprocess.run(["git", "commit", "-m", "feat: worktree change"], cwd=wt_dir, check=True)

    # 2. Create a modify/delete conflict branch: feature/mod-del modifies shared.txt, main deletes it
    subprocess.run(["git", "checkout", "-b", "feature/mod-del", "main"], cwd=repo_dir, check=True)
    (repo_dir / "shared.txt").write_text("modified on feature\n", encoding="utf-8")
    (repo_dir / "extra.txt").write_text("extra from mod-del\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "feat: modify shared.txt"], cwd=repo_dir, check=True)

    subprocess.run(["git", "checkout", "main"], cwd=repo_dir, check=True)
    subprocess.run(["git", "rm", "shared.txt"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "chore: remove shared.txt on main"], cwd=repo_dir, check=True)

    # Also create an artifact to exercise _cleanup_artifacts
    (repo_dir / ".DS_Store").write_text("junk", encoding="utf-8")
    (repo_dir / ".coverage").write_text("cov", encoding="utf-8")
    cache_dir = repo_dir / ".pytest_cache"
    cache_dir.mkdir()
    (cache_dir / "readme").write_text("cache", encoding="utf-8")

    # Run prune + merge + prune
    wt_res = CleanReposWorkflowBot._prune_worktrees(repo_dir)
    assert any("feature/wt-branch" in d for d in wt_res["detached_worktrees"])

    hygiene = CleanReposWorkflowBot._review_merge_and_prune_branches(
        repo_dir, base_branch="main", auto_commit=True
    )
    assert "feature/wt-branch" in hygiene["merged_branches"]
    assert "feature/mod-del" in hygiene["merged_branches"]
    assert "feature/mod-del" in hygiene["conflicts_resolved"]
    assert "feature/wt-branch" in hygiene["deleted_local"]
    assert "feature/mod-del" in hygiene["deleted_local"]
    assert (repo_dir / "wt_file.txt").is_file()
    assert (repo_dir / "extra.txt").is_file()
    shutil.rmtree(wt_dir, ignore_errors=True)


