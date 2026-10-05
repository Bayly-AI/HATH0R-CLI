#!/usr/bin/env python3
"""Build script for HATH0R Visual Studio Code Plugin / Extension releases in ./release/vscode/plugin."""

import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VSCODE_PKG_DIR = ROOT_DIR / "packages" / "vscode-extension"
RELEASE_VSCODE_DIR = ROOT_DIR / "release" / "vscode" / "plugin"
VSIX_NAME = "hath0r-vscode-0.9.0.vsix"


def clean_release_dir():
    print("[Hath0r VSCode Build] Cleaning release directory...")
    if RELEASE_VSCODE_DIR.exists():
        shutil.rmtree(RELEASE_VSCODE_DIR)
    RELEASE_VSCODE_DIR.mkdir(parents=True, exist_ok=True)


def generate_vsix_manifest(pkg_json: dict) -> str:
    """Generate extension.vsixmanifest complying with VS Code Marketplace Open Packaging conventions."""
    name = saxutils.escape(pkg_json.get("name", "hath0r-vscode"))
    version = saxutils.escape(pkg_json.get("version", "0.9.0"))
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


def build_vscode_package():
    print("[Hath0r VSCode Build] Staging VS Code plugin files...")
    staging_dir = RELEASE_VSCODE_DIR / "extension"
    staging_dir.mkdir(parents=True, exist_ok=True)

    with open(VSCODE_PKG_DIR / "package.json", "r", encoding="utf-8") as f:
        pkg_json = json.load(f)

    for item in ["package.json", "README.md", "CHANGELOG.md", "LICENSE", "tsconfig.json", ".vscodeignore"]:
        src = VSCODE_PKG_DIR / item
        if src.exists():
            shutil.copy2(src, staging_dir / item)

    if (VSCODE_PKG_DIR / "media").exists():
        shutil.copytree(VSCODE_PKG_DIR / "media", staging_dir / "media", dirs_exist_ok=True)
    if (VSCODE_PKG_DIR / "src").exists():
        shutil.copytree(VSCODE_PKG_DIR / "src", staging_dir / "src", dirs_exist_ok=True)
    if (VSCODE_PKG_DIR / "dist").exists():
        shutil.copytree(VSCODE_PKG_DIR / "dist", staging_dir / "dist", dirs_exist_ok=True)
    if (VSCODE_PKG_DIR / "test").exists():
        shutil.copytree(VSCODE_PKG_DIR / "test", staging_dir / "test", dirs_exist_ok=True)

    rel_docs_dir = RELEASE_VSCODE_DIR / "docs"
    rel_docs_dir.mkdir(parents=True, exist_ok=True)
    if (ROOT_DIR / "docs").exists():
        shutil.copytree(ROOT_DIR / "docs", rel_docs_dir, dirs_exist_ok=True)

    for doc_file in ["README.md", "TECH_README.md", "AGENTS.md", "LICENSE", "CHANGELOG.md"]:
        if (ROOT_DIR / doc_file).exists():
            shutil.copy2(ROOT_DIR / doc_file, rel_docs_dir / doc_file)

    vsix_target = RELEASE_VSCODE_DIR / VSIX_NAME
    manifest_content = generate_vsix_manifest(pkg_json)
    content_types_content = generate_content_types()

    (RELEASE_VSCODE_DIR / "extension.vsixmanifest").write_text(manifest_content, encoding="utf-8")
    (RELEASE_VSCODE_DIR / "[Content_Types].xml").write_text(content_types_content, encoding="utf-8")

    vsce_packaged = False
    try:
        print("[Hath0r VSCode Build] Packaging extension with @vscode/vsce...")
        cmd = ["npx", "--yes", "@vscode/vsce", "package", "--no-dependencies", "--out", str(vsix_target)]
        res = subprocess.run(cmd, cwd=VSCODE_PKG_DIR, capture_output=True, text=True)
        if res.returncode == 0 and vsix_target.exists():
            vsce_packaged = True
            print(f"[Hath0r VSCode Build] Created official marketplace VSIX via vsce: {vsix_target.name}")
        else:
            print(f"[Hath0r VSCode Build] vsce note: {res.stderr.strip() or res.stdout.strip()}")
    except Exception as e:
        print(f"[Hath0r VSCode Build] vsce fallback: {e}")

    if not vsce_packaged:
        print(f"[Hath0r VSCode Build] Building standard marketplace package {vsix_target.name}...")
        with zipfile.ZipFile(vsix_target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types_content)
            zf.writestr("extension.vsixmanifest", manifest_content)
            for root, _, files in os.walk(staging_dir):
                for file in files:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(RELEASE_VSCODE_DIR)
                    zf.write(full_path, arcname=str(rel_path))

    print(f"[Hath0r VSCode Build] Successfully finalized VSIX package: {vsix_target}")


def run_vscode_tests():
    print("[Hath0r VSCode Build] Running extension test suite...")
    test_file = VSCODE_PKG_DIR / "test" / "extension.test.js"
    cmd = ["node", "--test", str(test_file)]
    subprocess.run(cmd, cwd=ROOT_DIR, check=True)


def main():
    clean_release_dir()
    build_vscode_package()
    run_vscode_tests()

    print(f"\n[Hath0r VSCode Build Success] Artifacts created in {RELEASE_VSCODE_DIR}:")
    for f in sorted(RELEASE_VSCODE_DIR.rglob("*")):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            rel_name = f.relative_to(RELEASE_VSCODE_DIR)
            print(f"  - {rel_name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
