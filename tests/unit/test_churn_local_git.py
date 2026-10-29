"""ChurnManagerBot's built-in git-log analysis, used when hath0r_engine is absent."""

from __future__ import annotations

import subprocess
import sys

import pytest

from hath0r_cli.bots.churn_manager_bot import ChurnManagerBot

_ENGINE_MODULES = ("hath0r_engine.analysis.pmat_adapter", "hath0r_engine.ui.churn_heatmap")


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "development")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    hot = tmp_path / "hot.py"
    for i in range(16):
        body = "\n".join(f"if x == {j}:\n    y = {j}" for j in range(40 + i * 3))
        hot.write_text(body + "\n", encoding="utf-8")
        (tmp_path / "side.txt").write_text(f"{i}\n", encoding="utf-8")
        (tmp_path / "blob.bin").write_bytes(bytes([0, i, 255]))
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-q", "-m", f"c{i}")
    _git(tmp_path, "checkout", "-q", "-b", "feature/1-x")
    hot.write_text("if a:\n    b = 1\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("pass\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "change")
    return tmp_path


@pytest.fixture
def no_engine(monkeypatch):
    for name in _ENGINE_MODULES:
        monkeypatch.setitem(sys.modules, name, None)


def test_local_analysis_ranks_hotspots(repo, no_engine):
    bot = ChurnManagerBot()
    report = bot.analyze(repo, days=30)
    assert report["schema_version"] == "hath0r.pmat.churn/1"
    assert report["summary"]["total_commits_evaluated"] == 17
    top = report["hotspots"][0]
    assert top["file_path"] == "hot.py" and top["risk_tier"] in ("CRITICAL", "HIGH")
    assert "side.txt" in top["co_changing_files"]
    assert all(h["file_path"] != "blob.bin" for h in report["hotspots"])
    assert len(bot.hotspots(repo, limit=1)) == 1


def test_local_pr_risk_and_html(repo, no_engine):
    bot = ChurnManagerBot()
    risk = bot.pr_risk(repo, base_branch="development")
    assert risk["changed_files_count"] == 2
    assert risk["overall_risk_tier"] in ("CRITICAL", "HIGH", "MEDIUM")
    assert bot.pr_risk(repo, base_branch="no-such-branch")["overall_risk_tier"] == "LOW"
    html = bot.render_ui_html(repo)
    assert "<table" in html and "hot.py" in html


def test_local_analysis_outside_git(tmp_path, no_engine):
    report = ChurnManagerBot()._local_git_analysis(tmp_path)
    assert report["commit_hash"] == "unknown" and report["hotspots"] == []
    assert report["recommendations"] == []


@pytest.mark.parametrize(
    "volatility,tier",
    [(0.9, "CRITICAL"), (0.6, "HIGH"), (0.3, "MEDIUM"), (0.1, "LOW")],
    ids=["critical", "high", "medium", "low"],
)
def test_pr_risk_tiers(monkeypatch, repo, no_engine, volatility, tier):
    bot = ChurnManagerBot()
    monkeypatch.setattr(
        bot, "analyze", lambda *a, **k: {"hotspots": [{"file_path": "hot.py", "volatility_score": volatility}]}
    )
    assert bot.pr_risk(repo)["overall_risk_tier"] == tier
