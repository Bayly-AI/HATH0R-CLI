"""Tests for Hath0r CLI release folder structure, previous version archiving, and dual-repo sync."""

import hashlib
import tempfile
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from scripts.build_release_binaries import (
    cleanup_and_archive_release_dir,
    generate_checksums,
     read_version,
    rotate_previous_release,
    sync_to_framework,
)


def test_release_directory_structure_and_readmes():
    """Verify release/{mac,windows,vscode} directory and previous archive folder structure in CLI root."""
    root = Path(__file__).resolve().parents[1]
    release_dir = root / "release"
    mac_dir = release_dir / "mac"
    win_dir = release_dir / "windows"
    vscode_dir = release_dir / "vscode"
    prev_dir = release_dir / "previous"
    current_ver = read_version(root)

    assert release_dir.is_dir(), "release/ directory must exist in HATH0R-CLI"
    assert (release_dir / "README.md").is_file(), "release/README.md must exist"
    assert mac_dir.is_dir(), "release/mac/ directory must exist"
    assert win_dir.is_dir(), "release/windows/ directory must exist"
    assert vscode_dir.is_dir(), "release/vscode/ directory must exist"
    assert prev_dir.is_dir(), "release/previous/ directory must exist"
    assert (prev_dir / "README.md").is_file(), "release/previous/README.md must exist"
    assert (release_dir / "CHECKSUMS.sha256").is_file(), "release/CHECKSUMS.sha256 must exist"
    assert (mac_dir / "Hath0r-Install-Wizard.dmg").is_file(), "macOS DMG installer must exist in release/mac/"
    assert (win_dir / "Hath0r-Install-Wizard.exe").is_file(), "Windows EXE installer must exist in release/windows/"
    assert (vscode_dir / f"hath0r-vscode-{current_ver}.vsix").is_file(), (
        "VSCode VSIX installer must exist in release/vscode/"
    )

    # Ensure no unpacked hath0r-fileset-* directories or older versioned files remain at release/ root
    for item in release_dir.iterdir():
        assert not (item.is_dir() and item.name.startswith("hath0r-fileset-")), (
            f"Unpacked fileset directory {item.name} must not remain in release/ root"
        )
        if item.is_file() and item.name.startswith("hath0r-fileset-"):
            assert current_ver in item.name, f"Old fileset {item.name} must be archived in release/previous/"


def test_cleanup_and_archive_release_dir():
    """Verify older versioned files and unpacked fileset directories are moved to release/previous/<ver>/."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        rel_dir = tmp / "release"
        prev_dir = rel_dir / "previous"
        rel_dir.mkdir(parents=True)
        prev_dir.mkdir(parents=True)

        # Unpacked old fileset directory + old tarball + current tarball
        old_stage = rel_dir / "hath0r-fileset-1.20.0"
        old_stage.mkdir(parents=True)
        (old_stage / "VERSION").write_text("1.20.0\n", encoding="utf-8")
        (rel_dir / "hath0r-fileset-1.21.0.tar.gz").write_text("tar 1.21.0", encoding="utf-8")
        (rel_dir / "hath0r-fileset-1.22.0.tar.gz").write_text("tar 1.22.0", encoding="utf-8")

        res = cleanup_and_archive_release_dir(rel_dir, prev_dir, current_version="1.22.0", dry_run=False)
        assert "1.20.0" in res["archived_versions"]
        assert "1.21.0" in res["archived_versions"]
        assert not old_stage.exists()
        assert not (rel_dir / "hath0r-fileset-1.21.0.tar.gz").exists()
        assert (rel_dir / "mac" / "hath0r-fileset-1.22.0.tar.gz").is_file()
        assert (rel_dir / "windows" / "hath0r-fileset-1.22.0.tar.gz").is_file()
        assert (prev_dir / "1.20.0" / "hath0r-fileset-1.20.0.tar.gz").is_file()
        assert (prev_dir / "1.21.0" / "hath0r-fileset-1.21.0.tar.gz").is_file()


def test_checksum_computation_and_generation():
    """Verify SHA256 calculation and checksum file generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        file_a = tmp / "hath0r-darwin-arm64"
        file_a.write_bytes(b"dummy binary data arm64")
        file_b = tmp / "hath0r-linux-x86_64"
        file_b.write_bytes(b"dummy binary data x86_64")

        chk = generate_checksums(tmp)
        assert chk.is_file()
        content = chk.read_text(encoding="utf-8")
        assert "hath0r-darwin-arm64" in content
        assert "hath0r-linux-x86_64" in content

        digest_a = hashlib.sha256(b"dummy binary data arm64").hexdigest()
        assert digest_a in content


def test_rotation_previous_release():
    """Verify clearing release/{mac,windows,vscode} into previous/<version>/{mac,windows,vscode}/ archive."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        rel_dir = tmp / "release"
        prev_dir = rel_dir / "previous"
        (rel_dir / "mac").mkdir(parents=True)
        (rel_dir / "windows").mkdir(parents=True)
        (rel_dir / "vscode").mkdir(parents=True)
        prev_dir.mkdir(parents=True)

        # Create active 0.2.0 files in mac, windows, vscode
        (rel_dir / "mac" / "Hath0r-Install-Wizard-0.2.0-macos.dmg").write_text("dmg 0.2.0", encoding="utf-8")
        (rel_dir / "mac" / "hath0r-darwin-arm64").write_text("bin 0.2.0", encoding="utf-8")
        (rel_dir / "windows" / "Hath0r-Install-Wizard-0.2.0-windows-x64.exe").write_text("exe 0.2.0", encoding="utf-8")
        (rel_dir / "vscode" / "hath0r-vscode-0.2.0.vsix").write_text("vsix 0.2.0", encoding="utf-8")
        (rel_dir / "README.md").write_text("Release Docs", encoding="utf-8")

        archived = rotate_previous_release(rel_dir, prev_dir, current_version="0.3.0", dry_run=False)
        assert archived is not None
        assert archived.name == "0.2.0"
        assert (archived / "mac" / "Hath0r-Install-Wizard-0.2.0-macos.dmg").is_file()
        assert (archived / "mac" / "hath0r-darwin-arm64").is_file()
        assert (archived / "windows" / "Hath0r-Install-Wizard-0.2.0-windows-x64.exe").is_file()
        assert (archived / "vscode" / "hath0r-vscode-0.2.0.vsix").is_file()
        assert (archived / "CHECKSUMS.sha256").is_file()

        # Root README is preserved and mac/windows/vscode were cleared out for the new build
        assert (rel_dir / "README.md").is_file()
        assert not (rel_dir / "mac" / "Hath0r-Install-Wizard-0.2.0-macos.dmg").exists()
        assert not (rel_dir / "windows" / "Hath0r-Install-Wizard-0.2.0-windows-x64.exe").exists()
        assert not (rel_dir / "vscode" / "hath0r-vscode-0.2.0.vsix").exists()


def test_sync_to_framework():
    """Verify synchronization of release/{mac,windows,vscode,previous} between CLI and Framework."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        cli_rel = tmp / "cli" / "release"
        fw_rel = tmp / "framework" / "release"

        (cli_rel / "mac").mkdir(parents=True)
        (cli_rel / "windows").mkdir(parents=True)
        (cli_rel / "vscode").mkdir(parents=True)
        (cli_rel / "previous" / "0.2.0").mkdir(parents=True)

        (cli_rel / "mac" / "hath0r-darwin-arm64").write_text("latest-bin", encoding="utf-8")
        (cli_rel / "windows" / "Hath0r-Install-Wizard.exe").write_text("latest-exe", encoding="utf-8")
        (cli_rel / "vscode" / "hath0r-vscode.vsix").write_text("latest-vsix", encoding="utf-8")
        (cli_rel / "previous" / "0.2.0" / "hath0r-darwin-arm64").write_text("old-bin", encoding="utf-8")

        success = sync_to_framework(cli_rel, fw_rel, dry_run=False)
        assert success is True
        assert (fw_rel / "mac" / "hath0r-darwin-arm64").is_file()
        assert (fw_rel / "windows" / "Hath0r-Install-Wizard.exe").is_file()
        assert (fw_rel / "vscode" / "hath0r-vscode.vsix").is_file()
        assert (fw_rel / "previous" / "0.2.0" / "hath0r-darwin-arm64").is_file()
        assert (fw_rel / "CHECKSUMS.sha256").is_file()


def test_release_cli_commands():
    """Verify hath0r release build, rotate, validate, and sync commands via CLI runner."""
    runner = CliRunner()

    res_build = runner.invoke(cli, ["release", "build", "--dry-run"])
    assert res_build.exit_code == 0
    assert "Release build complete" in res_build.output or "command" in res_build.output

    res_rotate = runner.invoke(cli, ["release", "rotate", "--dry-run"])
    assert res_rotate.exit_code == 0
    assert "Rotated" in res_rotate.output or "rotated" in res_rotate.output or "release.rotate" in res_rotate.output

    res_sync = runner.invoke(cli, ["release", "sync", "--dry-run"])
    assert res_sync.exit_code == 0
    assert "synchronized" in res_sync.output.lower() or "release.sync" in res_sync.output


def test_release_bot_rotate_and_validate_and_step_runner():
    """Verify ReleaseBot.rotate_previous, ReleaseBot.validate root hygiene gate, and BotRegistry dispatch."""
    from hath0r_cli.bots.quality import ReleaseBot
    from hath0r_cli.step_runner import BotRegistry

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        (tmp / "VERSION").write_text("1.22.0\n", encoding="utf-8")
        (tmp / "CHANGELOG.md").write_text("## [1.22.0] - 2026-11-01\n- Added Install Wizard.\n", encoding="utf-8")
        rel_dir = tmp / "release"
        prev_dir = rel_dir / "previous"
        rel_dir.mkdir(parents=True)
        prev_dir.mkdir(parents=True)

        # Put an older 1.21.0 release artifact at release/ root and a mixed 0.3.0 file inside previous/1.5.0
        (rel_dir / "hath0r-fileset-1.21.0.tar.gz").write_text("old 1.21.0", encoding="utf-8")
        (rel_dir / "hath0r-darwin-arm64").write_text("bin 1.21.0", encoding="utf-8")
        (prev_dir / "1.5.0").mkdir(parents=True)
        (prev_dir / "1.5.0" / "hath0r-fileset-1.5.0.tar.gz").write_text("1.5.0", encoding="utf-8")
        (prev_dir / "1.5.0" / "hath0r-fileset-0.3.0.tar.gz").write_text("0.3.0", encoding="utf-8")

        bot = ReleaseBot(cwd=tmp)
        # Before rotation, validate() flags the non-current 1.21.0 artifact at release/ root
        val_before = bot.validate()
        assert val_before["success"] is False
        assert val_before["release_root_clean"] is False
        assert "hath0r-fileset-1.21.0.tar.gz" in val_before["stale_release_items"]

        # Rotate moves 1.21.0 files to previous/1.21.0/ and splits 0.3.0 out of previous/1.5.0/ into previous/0.3.0/
        rot = bot.rotate_previous(sync_framework=False, dry_run=False)
        assert rot["success"] is True
        assert (prev_dir / "1.21.0" / "hath0r-fileset-1.21.0.tar.gz").is_file()
        assert (prev_dir / "1.21.0" / "hath0r-darwin-arm64").is_file()
        assert (prev_dir / "0.3.0" / "hath0r-fileset-0.3.0.tar.gz").is_file()
        assert not (prev_dir / "1.5.0" / "hath0r-fileset-0.3.0.tar.gz").exists()

        # After rotation, validate() passes cleanly
        val_after = bot.validate()
        assert val_after["success"] is True
        assert val_after["release_root_clean"] is True

        # Verify BotRegistry dispatches release-bot rotate action
        registry = BotRegistry(cwd=tmp)
        step_res = registry.invoke(
            "release-bot",
            "rotate",
            {"sync_framework": False},
            dry_run=True,
        )
        assert step_res.success is True

