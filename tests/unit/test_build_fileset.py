"""Tests for scripts/build_fileset.py."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def build_mod():
    import importlib.util

    path = ROOT / "scripts" / "build_fileset.py"
    spec = importlib.util.spec_from_file_location("build_fileset", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_build_fileset_creates_tarball_and_manifest(build_mod, tmp_path: Path) -> None:
    fw = ROOT.parent / "hath0r"
    tar_path = build_mod.build(
        tmp_path,
        product_id="hath0r-member",
        framework_root=fw if fw.is_dir() else None,
    )
    assert tar_path.is_file()
    assert tar_path.name.startswith("hath0r-fileset-")
    assert tar_path.name.endswith(".tar.gz")
    sha = tar_path.with_name(tar_path.name + ".sha256")
    assert sha.is_file()
    digest_line = sha.read_text(encoding="utf-8")
    assert tar_path.name in digest_line

    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
    assert any(n.endswith("AGENTS.md") for n in names)
    assert any(n.endswith("cfg/suite.yaml") for n in names)
    assert any(n.endswith("MANIFEST.json") for n in names)
    assert any(n.endswith("bin/hath0r-bootstrap.sh") for n in names)
    # no absolute user paths leaked into archive member names
    assert not any("/Users/" in n for n in names)

    # extract manifest
    stage = tmp_path / "extract"
    stage.mkdir()
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(stage)
    manifest_files = list(stage.rglob("MANIFEST.json"))
    assert manifest_files
    manifest = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert manifest["schema"] == "hath0r.fileset.manifest/1"
    assert manifest["engine_package"] == "hath0r-cli"
    assert "cli_version" in manifest
