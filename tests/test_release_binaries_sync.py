"""Tests for Hath0r CLI release folder structure, previous version archiving, and dual-repo sync."""

import hashlib
import shutil
import tempfile
from pathlib import Path
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.bots.quality import ReleaseBot
from scripts.build_release_binaries import (
    compute_sha256,
    generate_checksums,
    rotate_previous_release,
    sync_to_framework,
    execute_release_build,
)


def test_release_directory_structure_and_readmes():
    """Verify release directory and previous archive folder structure in CLI root."""
    root = Path(__file__).resolve().parents[1]
    release_dir = root / "release"
    prev_dir = release_dir / "previous"

    assert release_dir.is_dir(), "release/ directory must exist in HATH0R-CLI"
    assert (release_dir / "README.md").is_file(), "release/README.md must exist"
    assert prev_dir.is_dir(), "release/previous/ directory must exist"
    assert (prev_dir / "README.md").is_file(), "release/previous/README.md must exist"
    assert (release_dir / "CHECKSUMS.sha256").is_file(), "release/CHECKSUMS.sha256 must exist"


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
    """Verify rotating previous release artifacts into previous/<version>/ archive."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        rel_dir = tmp / "release"
        prev_dir = rel_dir / "previous"
        rel_dir.mkdir(parents=True)
        prev_dir.mkdir(parents=True)

        # Create active 0.2.0 files
        (rel_dir / "hath0r_cli-0.2.0.tar.gz").write_text("tarball 0.2.0", encoding="utf-8")
        (rel_dir / "hath0r-darwin-arm64").write_text("bin 0.2.0", encoding="utf-8")
        (rel_dir / "README.md").write_text("Release Docs", encoding="utf-8")

        archived = rotate_previous_release(rel_dir, prev_dir, current_version="0.3.0", dry_run=False)
        assert archived is not None
        assert archived.name == "0.2.0"
        assert (archived / "hath0r_cli-0.2.0.tar.gz").is_file()
        assert (archived / "hath0r-darwin-arm64").is_file()
        assert (archived / "CHECKSUMS.sha256").is_file()

        # Root README is preserved
        assert (rel_dir / "README.md").is_file()
        # Old files moved out of root release
        assert not (rel_dir / "hath0r_cli-0.2.0.tar.gz").exists()


def test_sync_to_framework():
    """Verify synchronization between CLI release folder and Framework release folder."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        cli_rel = tmp / "cli" / "release"
        fw_rel = tmp / "framework" / "release"

        cli_rel.mkdir(parents=True)
        (cli_rel / "previous" / "0.2.0").mkdir(parents=True)

        (cli_rel / "hath0r-darwin-arm64").write_text("latest-bin", encoding="utf-8")
        (cli_rel / "previous" / "0.2.0" / "hath0r-darwin-arm64").write_text("old-bin", encoding="utf-8")

        success = sync_to_framework(cli_rel, fw_rel, dry_run=False)
        assert success is True
        assert (fw_rel / "hath0r-darwin-arm64").is_file()
        assert (fw_rel / "previous" / "0.2.0" / "hath0r-darwin-arm64").is_file()
        assert (fw_rel / "CHECKSUMS.sha256").is_file()


def test_release_cli_commands():
    """Verify hath0r release build and sync commands via CLI runner."""
    runner = CliRunner()

    res_build = runner.invoke(cli, ["release", "build", "--dry-run"])
    assert res_build.exit_code == 0
    assert "Release build complete" in res_build.output or "command" in res_build.output

    res_sync = runner.invoke(cli, ["release", "sync", "--dry-run"])
    assert res_sync.exit_code == 0
    assert "synchronized" in res_sync.output.lower() or "release.sync" in res_sync.output
