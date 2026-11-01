"""Tests for Hath0r VS Code Plugin / Extension release packaging and structure."""

import json
import unittest
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT_DIR / "packages" / "vscode-extension"
VSCODE_RELEASE_ROOT = ROOT_DIR / "release" / "vscode"
RELEASE_DIR = VSCODE_RELEASE_ROOT / "plugin"


def _expected_vsix_path() -> Path:
    pkg = json.loads((PKG_DIR / "package.json").read_text(encoding="utf-8"))
    vsix_name = f"{pkg['name']}-{pkg['version']}.vsix"
    if (RELEASE_DIR / vsix_name).is_file():
        return RELEASE_DIR / vsix_name
    return VSCODE_RELEASE_ROOT / vsix_name


class TestHath0rVSCodePlugin(unittest.TestCase):
    def test_extension_source_structure(self):
        """Verify package.json manifest, icons, and source definitions."""
        self.assertTrue((PKG_DIR / "package.json").exists())
        self.assertTrue((PKG_DIR / "README.md").exists())
        self.assertTrue((PKG_DIR / "CHANGELOG.md").exists())
        self.assertTrue((PKG_DIR / "LICENSE").exists())
        self.assertTrue((PKG_DIR / "media" / "hath0r.svg").exists())
        self.assertTrue((PKG_DIR / "media" / "hath0r.png").exists())
        self.assertTrue((PKG_DIR / "src" / "extension.ts").exists())
        self.assertTrue((PKG_DIR / "src" / "client.ts").exists())
        self.assertTrue((PKG_DIR / "src" / "commands.ts").exists())

        with open(PKG_DIR / "package.json", "r", encoding="utf-8") as f:
            pkg = json.load(f)

        self.assertEqual(pkg.get("name"), "hath0r-vscode")
        self.assertEqual(pkg.get("publisher"), "BaylyAI")
        self.assertIn("hath0r.doctor", [c["command"] for c in pkg["contributes"]["commands"]])
        self.assertIn("hath0r.qualityGate", [c["command"] for c in pkg["contributes"]["commands"]])

    def test_vsix_packaging_and_contents(self):
        """Verify the generated .vsix package adheres to Open Packaging specifications."""
        vsix_path = _expected_vsix_path()
        self.assertTrue(vsix_path.exists(), f"VSIX artifact {vsix_path} must exist")

        with zipfile.ZipFile(vsix_path, "r") as zf:
            namelist = [n.lower() for n in zf.namelist()]
            self.assertIn("[content_types].xml", namelist)
            self.assertIn("extension.vsixmanifest", namelist)
            self.assertIn("extension/package.json", namelist)
            self.assertIn("extension/readme.md", namelist)
            self.assertIn("extension/dist/extension.js", namelist)
            self.assertIn("extension/media/hath0r.svg", namelist)


if __name__ == "__main__":
    unittest.main()
