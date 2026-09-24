"""Unit tests for portable group root / KB path resolution."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from hath0r_cli import cli


def _make_group_root(path: Path, marker: str = "hath0r-opensource") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "AGENTS.md").write_text(f"# Group\nmarker: {marker}\n", encoding="utf-8")
    (path / ".hath0r").mkdir(exist_ok=True)
    return path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HATH0R_GROUP_ROOT", raising=False)
    monkeypatch.delenv("HATH0R_KB_PATH", raising=False)


def test_group_root_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    root = tmp_path / "custom-group"
    root.mkdir()
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(root))
    assert cli._group_root() == root.resolve()


def test_group_root_env_expands_user(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    # Use a path under tmp that we can still expand via ~ by mocking home.
    home = tmp_path / "home"
    home.mkdir()
    group = home / "my-group"
    group.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("HATH0R_GROUP_ROOT", "~/my-group")
    assert cli._group_root() == group.resolve()


def test_discover_walk_up_from_nested_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    root = _make_group_root(tmp_path / "OpenSource")
    nested = root / "HATH0R-CLI" / "src"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert cli._group_root() == root.resolve()


def test_discover_prefers_outermost_group_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Member checkouts also have AGENTS.md + .hath0r; outermost group wins."""
    root = _make_group_root(tmp_path / "OpenSource")
    member = _make_group_root(root / "HATH0R-CLI")
    nested = member / "src"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert cli._group_root() == root.resolve()


def test_discover_ignores_agents_without_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    (decoy / "AGENTS.md").write_text("# unrelated agents file\n", encoding="utf-8")
    (decoy / ".hath0r").mkdir()
    nested = decoy / "child"
    nested.mkdir()
    monkeypatch.chdir(nested)
    # Soft fallback should also fail (not a real group in test home).
    monkeypatch.setattr(cli, "_SOFT_FALLBACK_GROUP_ROOT", tmp_path / "nope")
    with pytest.raises(click.ClickException) as excinfo:
        cli._group_root()
    assert "HATH0R_GROUP_ROOT" in str(excinfo.value)
    assert "hath0r-opensource" in str(excinfo.value)


def test_discover_requires_hath0r_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    root = tmp_path / "almost"
    root.mkdir()
    (root / "AGENTS.md").write_text("hath0r-opensource\n", encoding="utf-8")
    # no .hath0r/
    monkeypatch.chdir(root)
    monkeypatch.setattr(cli, "_SOFT_FALLBACK_GROUP_ROOT", tmp_path / "nope")
    with pytest.raises(click.ClickException):
        cli._group_root()


def test_soft_fallback_when_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    soft = _make_group_root(tmp_path / "Development" / "OpenSource")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(cli, "_SOFT_FALLBACK_GROUP_ROOT", soft)
    assert cli._group_root() == soft.resolve()


def test_soft_fallback_skipped_when_invalid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    soft = tmp_path / "Development" / "OpenSource"
    soft.mkdir(parents=True)
    # empty dir — not a group root
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(cli, "_SOFT_FALLBACK_GROUP_ROOT", soft)
    with pytest.raises(click.ClickException) as excinfo:
        cli._group_root()
    msg = str(excinfo.value)
    assert "Could not determine HATHOR OpenSource group root" in msg
    assert "Remediation" in msg


def test_env_takes_priority_over_walk_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    walked = _make_group_root(tmp_path / "walked")
    nested = walked / "sub"
    nested.mkdir()
    env_root = tmp_path / "from-env"
    env_root.mkdir()
    monkeypatch.chdir(nested)
    monkeypatch.setenv("HATH0R_GROUP_ROOT", str(env_root))
    assert cli._group_root() == env_root.resolve()


def test_kb_path_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    kb = tmp_path / "custom-kb"
    kb.mkdir()
    monkeypatch.setenv("HATH0R_KB_PATH", str(kb))
    # Even without a group root, KB override should win.
    assert cli._kb_path() == kb


def test_kb_path_default_under_group_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    root = _make_group_root(tmp_path / "OpenSource")
    monkeypatch.chdir(root)
    assert cli._kb_path() == root.resolve() / ".hath0r" / "knowledgebase"


def test_looks_like_group_root_helpers(tmp_path: Path) -> None:
    good = _make_group_root(tmp_path / "good")
    assert cli._looks_like_group_root(good) is True
    bad = tmp_path / "bad"
    bad.mkdir()
    assert cli._looks_like_group_root(bad) is False


def test_discover_group_root_direct(tmp_path: Path) -> None:
    root = _make_group_root(tmp_path / "grp")
    nested = root / "a" / "b"
    nested.mkdir(parents=True)
    assert cli._discover_group_root(nested) == root.resolve()
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cli._discover_group_root(empty) is None


def test_no_hardcoded_user_path_in_cli_source() -> None:
    source = Path(cli.__file__).read_text(encoding="utf-8")
    assert "/Users/raybayly" not in source
    assert "DEFAULT_GROUP_ROOT" not in source
