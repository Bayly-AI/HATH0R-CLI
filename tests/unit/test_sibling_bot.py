"""Unit tests for SiblingManagerBot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from hath0r_cli.bots.sibling_bot import SUITE_SIBLINGS, SiblingManagerBot


def _make_mock_runner(records: List[Tuple[List[str], Path | None]] | None = None):
    def runner(cmd: List[str], cwd: Path | None = None, timeout: int = 120) -> Tuple[int, str, str]:
        if records is not None:
            records.append((cmd, cwd))
        return 0, "mock success", ""

    return runner


def test_resolve_product_spec() -> None:
    bot = SiblingManagerBot()
    # Canonical product_id
    atc_spec = bot.resolve_product_spec("hath0r-atc")
    assert atc_spec is not None
    assert atc_spec["product_id"] == "hath0r-atc"
    assert atc_spec["repo"] == "Bayly-AI/HATH0R-ATC"

    # Alias
    atc_alias = bot.resolve_product_spec("atc")
    assert atc_alias is not None
    assert atc_alias["product_id"] == "hath0r-atc"

    # MCP alias
    mcp_spec = bot.resolve_product_spec("mcp")
    assert mcp_spec is not None
    assert mcp_spec["product_id"] == "hath0r-mcp"

    # Unknown
    unknown = bot.resolve_product_spec("nonexistent")
    assert unknown is None


def test_locate_sibling(tmp_path: Path) -> None:
    bot = SiblingManagerBot(group_root=tmp_path)
    assert bot.locate_sibling("hath0r-atc") is None

    # Create sibling folder
    atc_dir = tmp_path / "hath0r-atc"
    atc_dir.mkdir()
    assert bot.locate_sibling("hath0r-atc") == atc_dir
    assert bot.locate_sibling("atc") == atc_dir


def test_get_local_version(tmp_path: Path) -> None:
    bot = SiblingManagerBot()
    # Empty
    assert bot.get_local_version(tmp_path) is None

    # VERSION file
    (tmp_path / "VERSION").write_text("0.2.2\n", encoding="utf-8")
    assert bot.get_local_version(tmp_path) == "0.2.2"

    # pyproject.toml fallback when VERSION absent
    (tmp_path / "VERSION").unlink()
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.0.1"\n', encoding="utf-8")
    assert bot.get_local_version(tmp_path) == "1.0.1"


def test_get_remote_latest_version() -> None:
    def mock_http(url: str, headers: Dict[str, str]) -> bytes:
        if "releases/latest" in url:
            return json.dumps({"tag_name": "v0.2.2"}).encode("utf-8")
        return b"[]"

    bot = SiblingManagerBot(http_get=mock_http)
    tag = bot.get_remote_latest_version("Bayly-AI/HATH0R-ATC")
    assert tag == "v0.2.2"


def test_scan_siblings(tmp_path: Path) -> None:
    bot = SiblingManagerBot(group_root=tmp_path)
    res = bot.scan_siblings()
    assert not res["all_canonical_present"]
    assert "hath0r-atc" in res["products"]
    assert not res["products"]["hath0r-atc"]["present"]

    # Create folders
    for pid, spec in SUITE_SIBLINGS.items():
        p_dir = tmp_path / spec["default_dir"]
        p_dir.mkdir(parents=True, exist_ok=True)
        (p_dir / "VERSION").write_text("1.0.0", encoding="utf-8")

    res2 = bot.scan_siblings()
    assert res2["all_canonical_present"]
    assert res2["products"]["hath0r-atc"]["present"]
    assert res2["products"]["hath0r-atc"]["local_version"] == "1.0.0"


def test_download_and_install_already_installed(tmp_path: Path) -> None:
    bot = SiblingManagerBot(group_root=tmp_path)
    atc_dir = tmp_path / "hath0r-atc"
    atc_dir.mkdir()
    (atc_dir / "VERSION").write_text("0.2.2", encoding="utf-8")

    res = bot.download_and_install("hath0r-atc")
    assert res["success"]
    assert res["already_installed"]
    assert res["version"] == "0.2.2"


def test_download_and_install_clones_and_installs(tmp_path: Path) -> None:
    calls: List[Tuple[List[str], Path | None]] = []

    def mock_runner(cmd: List[str], cwd: Path | None = None, timeout: int = 120) -> Tuple[int, str, str]:
        calls.append((cmd, cwd))
        if cmd[0] == "git" and cmd[1] == "clone":
            # Simulate git clone creating directory and files
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
            (target / "VERSION").write_text("0.2.2\n", encoding="utf-8")
            (target / "pyproject.toml").write_text('[project]\nversion = "0.2.2"\n', encoding="utf-8")
        return 0, "ok", ""

    bot = SiblingManagerBot(group_root=tmp_path, runner=mock_runner)
    res = bot.download_and_install("hath0r-mcp")
    assert res["success"]
    assert res["installed"]
    assert res["version"] == "0.2.2"

    # Verified clone command was invoked
    assert any(c[0][:2] == ["git", "clone"] for c in calls)


def test_ensure_siblings(tmp_path: Path) -> None:
    bot = SiblingManagerBot(group_root=tmp_path)

    # Dry run when missing
    dry = bot.ensure_siblings(dry_run=True)
    assert dry["success"]
    assert len(dry["results"]) == 2
    assert all(r["action"] == "would_install" for r in dry["results"])

    # Pre-create one
    (tmp_path / "hath0r-atc").mkdir()
    (tmp_path / "hath0r-atc" / "VERSION").write_text("0.2.2", encoding="utf-8")

    dry2 = bot.ensure_siblings(dry_run=True)
    atc_res = next(r for r in dry2["results"] if r["product_id"] == "hath0r-atc")
    mcp_res = next(r for r in dry2["results"] if r["product_id"] == "hath0r-mcp")
    assert atc_res["action"] == "already_present"
    assert mcp_res["action"] == "would_install"
