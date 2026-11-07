#!/usr/bin/env python3
"""Build script for HATH0R Visual Studio Code Plugin / Extension releases in ./release/vscode."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import zipfile
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
VSCODE_PKG_DIR = ROOT_DIR / "packages" / "vscode-extension"
RELEASE_DIR = ROOT_DIR / "release"
RELEASE_VSCODE_ROOT = RELEASE_DIR / "vscode"
RELEASE_VSCODE_DIR = RELEASE_VSCODE_ROOT / "plugin"


def read_repo_version(root_dir: Path = ROOT_DIR) -> str:
    """Read canonical version from root VERSION file."""
    ver_file = root_dir / "VERSION"
    if ver_file.is_file():
        return ver_file.read_text(encoding="utf-8").strip()
    pkg = json.loads((VSCODE_PKG_DIR / "package.json").read_text(encoding="utf-8"))
    return str(pkg.get("version", "0.9.0"))


def sync_package_json_version(version: Optional[str] = None) -> dict:
    """Ensure packages/vscode-extension/package.json matches the canonical VERSION."""
    pkg_path = VSCODE_PKG_DIR / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    target_ver = version or read_repo_version()
    if pkg.get("version") != target_ver:
        pkg["version"] = target_ver
        pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    return pkg


def vsix_name(version: Optional[str] = None) -> str:
    """VSIX file name derived from the extension manifest."""
    pkg = json.loads((VSCODE_PKG_DIR / "package.json").read_text(encoding="utf-8"))
    ver = version or pkg.get("version") or read_repo_version()
    return f"{pkg['name']}-{ver}.vsix"


def npm(*args: str) -> None:
    """Run an npm command in the extension package; fail the build on error."""
    subprocess.run(["npm", *args], cwd=VSCODE_PKG_DIR, check=True)


def rotate_existing_vscode_release(
    release_dir: Path = RELEASE_DIR,
    previous_dir: Optional[Path] = None,
    current_version: Optional[str] = None,
    force_archive: bool = False,
    dry_run: bool = False,
) -> Optional[Path]:
    """Move existing items from `release/vscode/` into `release/previous/<prev_ver>/vscode/` before building new release."""
    vscode_root = release_dir / "vscode"
    prev_root = previous_dir or (release_dir / "previous")
    target_ver = current_version or read_repo_version()

    if not vscode_root.is_dir():
        return None

    existing_items = [p for p in vscode_root.iterdir() if p.name not in (".DS_Store", ".gitkeep")]
    if not existing_items:
        return None

    # Detect version of existing VSCode release
    ver_re = re.compile(r"hath0r-vscode-(\d+\.\d+\.\d+)\.vsix")
    detected_ver: Optional[str] = None
    for f in vscode_root.rglob("*.vsix"):
        m = ver_re.search(f.name)
        if m:
            detected_ver = m.group(1)
            if detected_ver != target_ver:
                break

    if not detected_ver:
        ext_pkg = vscode_root / "plugin" / "extension" / "package.json"
        if ext_pkg.is_file():
            try:
                detected_ver = json.loads(ext_pkg.read_text(encoding="utf-8")).get("version")
            except (OSError, ValueError):
                detected_ver = None

    if not detected_ver:
        detected_ver = target_ver

    if detected_ver == target_ver and not force_archive:
        return None

    archive_vscode_dir = prev_root / detected_ver / "vscode"
    if not dry_run:
        if archive_vscode_dir.exists():
            shutil.rmtree(archive_vscode_dir, ignore_errors=True)
        archive_vscode_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(vscode_root, archive_vscode_dir, dirs_exist_ok=True)
        for item in existing_items:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
    return archive_vscode_dir


def clean_release_dir(
    release_dir: Path = RELEASE_DIR,
    previous_dir: Optional[Path] = None,
    current_version: Optional[str] = None,
) -> None:
    print("[Hath0r VSCode Build] Rotating and cleaning release/vscode directory...")
    rotate_existing_vscode_release(
        release_dir=release_dir,
        previous_dir=previous_dir,
        current_version=current_version,
        force_archive=True,
    )
    vscode_root = release_dir / "vscode"
    plugin_dir = vscode_root / "plugin"
    if vscode_root.exists():
        shutil.rmtree(vscode_root)
    plugin_dir.mkdir(parents=True, exist_ok=True)


def generate_vsix_manifest(pkg_json: dict) -> str:
    """Generate extension.vsixmanifest complying with VS Code Marketplace Open Packaging conventions."""
    name = saxutils.escape(pkg_json.get("name", "hath0r-vscode"))
    version = saxutils.escape(pkg_json.get("version", read_repo_version()))
    publisher = saxutils.escape(pkg_json.get("publisher", "BaylyAI"))
    display_name = saxutils.escape(
        pkg_json.get("displayName", "Hath0r - Enterprise Autonomous AI Agent Orchestration and Control Plane")
    )
    description = saxutils.escape(pkg_json.get("description", ""))
    license_file = "extension/LICENSE"
    readme_file = "extension/README.md"
    icon_file = "extension/media/hath0r.png" if (VSCODE_PKG_DIR / "media" / "hath0r.png").exists() else ""

    manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{name}" Version="{version}" Publisher="{publisher}"/>
    <DisplayName>{display_name}</DisplayName>
    <Description xml:space="preserve">{description}</Description>
    <Tags>hath0r,ai-agents,agentic-ai,taguchi,finops,tri-graph,mcp,control-plane</Tags>
    <Categories>Machine Learning,Programming Languages,Testing,Visualization,Other</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Badges></Badges>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.80.0" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace,web" />
    </Properties>
    <License>{license_file}</License>
    <Icon>{icon_file}</Icon>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="{readme_file}" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="{license_file}" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="{icon_file}" Addressable="true" />
  </Assets>
</PackageManifest>
"""
    try:
        ET.fromstring(manifest)
    except Exception as e:
        raise ValueError(f"Generated VSIX manifest is invalid XML: {e}")

    return manifest.strip()


def generate_content_types() -> str:
    """Generate [Content_Types].xml for Open Packaging Conventions."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="js" ContentType="application/javascript"/>
  <Default Extension="ts" ContentType="text/plain"/>
  <Default Extension="md" ContentType="text/markdown"/>
  <Default Extension="svg" ContentType="image/svg+xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="txt" ContentType="text/plain"/>
  <Default Extension="vsixmanifest" ContentType="text/xml"/>
</Types>
""".strip()


def _create_opc_vsix_archive(plugin_dir: Path, vsix_target: Path) -> None:
    """Create a valid Open Packaging Conventions (.vsix) zip archive from staged `plugin_dir`."""
    staging_dir = plugin_dir / "extension"
    manifest_file = plugin_dir / "extension.vsixmanifest"
    content_types_file = plugin_dir / "[Content_Types].xml"
    with zipfile.ZipFile(vsix_target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_file, "extension.vsixmanifest")
        zf.write(content_types_file, "[Content_Types].xml")
        for f in sorted(staging_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(staging_dir)
                arcname = f"extension/{rel.as_posix()}"
                zf.write(f, arcname)
                if rel.name == "README.md":
                    zf.write(f, "extension/readme.md")
                elif rel.name == "CHANGELOG.md":
                    zf.write(f, "extension/changelog.md")


def build_vscode_package(
    release_dir: Path = RELEASE_DIR,
    version: Optional[str] = None,
    use_vsce: bool = False,
) -> Path:
    print("[Hath0r VSCode Build] Staging VS Code plugin files into release/vscode...")
    pkg_json = sync_package_json_version(version)
    ver = str(pkg_json["version"])

    vscode_root = release_dir / "vscode"
    plugin_dir = vscode_root / "plugin"
    staging_dir = plugin_dir / "extension"
    staging_dir.mkdir(parents=True, exist_ok=True)

    for item in ["package.json", "README.md", "CHANGELOG.md", "LICENSE", "tsconfig.json", ".vscodeignore"]:
        src = VSCODE_PKG_DIR / item
        if src.exists():
            shutil.copy2(src, staging_dir / item)

    for sub_name in ("media", "src", "dist", "test"):
        src_sub = VSCODE_PKG_DIR / sub_name
        if src_sub.exists():
            shutil.copytree(src_sub, staging_dir / sub_name, dirs_exist_ok=True)

    rel_docs_dir = plugin_dir / "docs"
    rel_docs_dir.mkdir(parents=True, exist_ok=True)
    for doc_file in ["README.md", "TECH_README.md", "LICENSE", "CHANGELOG.md"]:
        if (ROOT_DIR / doc_file).exists() and not (rel_docs_dir / doc_file).exists():
            shutil.copy2(ROOT_DIR / doc_file, rel_docs_dir / doc_file)

    manifest_xml = generate_vsix_manifest(pkg_json)
    content_types_xml = generate_content_types()
    (plugin_dir / "extension.vsixmanifest").write_text(manifest_xml, encoding="utf-8")
    (plugin_dir / "[Content_Types].xml").write_text(content_types_xml, encoding="utf-8")

    vsix_filename = vsix_name(ver)
    vsix_target = plugin_dir / vsix_filename

    if use_vsce:
        print("[Hath0r VSCode Build] Packaging extension with @vscode/vsce...")
        cmd = ["npx", "--yes", "@vscode/vsce", "package", "--no-dependencies", "--out", str(vsix_target)]
        res = subprocess.run(cmd, cwd=VSCODE_PKG_DIR, capture_output=True, text=True)
        if res.returncode != 0 or not vsix_target.exists():
            _create_opc_vsix_archive(plugin_dir, vsix_target)
    else:
        _create_opc_vsix_archive(plugin_dir, vsix_target)

    with zipfile.ZipFile(vsix_target) as zf:
        if "extension/dist/extension.js" not in zf.namelist():
            raise SystemExit("[Hath0r VSCode Build] VSIX is missing extension/dist/extension.js")

    # Place canonical VSIX files directly in release/vscode/ as well as release/vscode/plugin/
    root_versioned_vsix = vscode_root / vsix_filename
    root_canonical_vsix = vscode_root / "hath0r-vscode.vsix"
    shutil.copy2(vsix_target, root_versioned_vsix)
    shutil.copy2(vsix_target, root_canonical_vsix)

    sha_digest = hashlib.sha256(vsix_target.read_bytes()).hexdigest()
    (vscode_root / f"{root_versioned_vsix.name}.sha256").write_text(
        f"{sha_digest}  {root_versioned_vsix.name}\n", encoding="utf-8"
    )
    (vscode_root / f"{root_canonical_vsix.name}.sha256").write_text(
        f"{sha_digest}  {root_canonical_vsix.name}\n", encoding="utf-8"
    )
    (vscode_root / "CHECKSUMS.sha256").write_text(
        f"{sha_digest}  {root_canonical_vsix.name}\n{sha_digest}  {root_versioned_vsix.name}\n",
        encoding="utf-8",
    )

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"vsix_name={vsix_target.name}\nvsix_path={vsix_target}\n")
    print(f"[Hath0r VSCode Build] Successfully finalized VSIX package: {root_versioned_vsix}")
    return root_versioned_vsix


def run_vscode_tests() -> None:
    """Install pinned dev dependencies, compile TypeScript to dist/, and run the extension tests."""
    print("[Hath0r VSCode Build] Installing dependencies, compiling and testing...")
    npm("ci", "--no-audit", "--no-fund")
    npm("test")


def main() -> None:
    clean_release_dir()
    if os.environ.get("HATH0R_VSCODE_SKIP_NPM") != "1":
        run_vscode_tests()
        build_vscode_package(use_vsce=True)
    else:
        build_vscode_package(use_vsce=False)

    print(f"\n[Hath0r VSCode Build Success] Artifacts created in {RELEASE_VSCODE_ROOT}:")
    for f in sorted(RELEASE_VSCODE_ROOT.iterdir()):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
