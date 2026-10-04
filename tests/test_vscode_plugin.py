"""Tests for Hath0r VS Code Plugin / Extension release packaging and structure."""

import json
import unittest
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PKG_DIR = ROOT_DIR / "packages" / "vscode-extension"
RELEASE_DIR = ROOT_DIR / "release" / "vscode" / "plugin"
VSIX_PATH = RELEASE_DIR / "hath0r-vscode-0.9.0.vsix"


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
        self.assertTrue(VSIX_PATH.exists(), f"VSIX artifact {VSIX_PATH} must exist")

        with zipfile.ZipFile(VSIX_PATH, "r") as zf:
            namelist = [n.lower() for n in zf.namelist()]
            self.assertIn("[content_types].xml", namelist)
            self.assertIn("extension.vsixmanifest", namelist)
            self.assertIn("extension/package.json", namelist)
            self.assertIn("extension/readme.md", namelist)
            self.assertIn("extension/dist/extension.js", namelist)
            self.assertIn("extension/media/hath0r.svg", namelist)


if __name__ == "__main__":
    unittest.main()
