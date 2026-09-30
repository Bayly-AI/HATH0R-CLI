import re
from pathlib import Path
from typing import Any

import yaml


class VersionBot:
    """Ensures semantic versioning and injects UI version footers across repositories."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = cwd or Path.cwd()
        self.cfg_dir = self.cwd / ".hath0r" / "cfg"

    def enforce_version(self, dry_run: bool = False) -> dict[str, Any]:
        """Check/create version config and inject into UI footers."""
        self.cfg_dir.mkdir(parents=True, exist_ok=True)
        version_file = self.cfg_dir / "version.yaml"

        version = "0.0.1"
        if version_file.exists():
            try:
                data = yaml.safe_load(version_file.read_text(encoding="utf-8")) or {}
                if "version" in data:
                    version = str(data["version"])
            except Exception:
                pass

        # Verify valid semver
        if not re.match(r"^\d+\.\d+\.\d+(-.*)?$", version):
            return {"success": False, "error": f"Version '{version}' does not comply with Semantic Versioning."}

        if not dry_run:
            # Always ensure the file exists and is updated
            version_file.write_text(yaml.dump({"version": version}))

        # Inject into UI
        injected_files = []
        footer_block = (
            "<!-- HATH0R-VERSION-FOOTER -->\n"
            f'<div style="position: fixed; bottom: 0; left: 0; width: 100%; text-align: center; '
            f"font-size: 8px; color: lightgrey; font-family: 'Avenir Next', 'Avenir Next Roman', "
            f'sans-serif; z-index: 9999;">'
            f"v{version}</div>\n"
            "<!-- /HATH0R-VERSION-FOOTER -->"
        )

        html_files = list(self.cwd.rglob("*.html"))
        # Exclude hidden directories like .hath0r, .git, node_modules
        html_files = [
            f
            for f in html_files
            if not any(p.startswith(".") or p == "node_modules" for p in f.relative_to(self.cwd).parts)
        ]

        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")

            # If already has footer, replace it
            pattern = re.compile(r"<!-- HATH0R-VERSION-FOOTER -->.*?<!-- /HATH0R-VERSION-FOOTER -->", re.DOTALL)
            if pattern.search(content):
                new_content = pattern.sub(footer_block, content)
            else:
                # Inject before </body>
                if "</body>" in content:
                    new_content = content.replace("</body>", f"{footer_block}\n</body>")
                else:
                    new_content = content + f"\n{footer_block}"

            if new_content != content:
                if not dry_run:
                    html_file.write_text(new_content, encoding="utf-8")
                injected_files.append(str(html_file.relative_to(self.cwd)))

        return {
            "success": True,
            "version": version,
            "injected_files": injected_files,
            "message": f"Enforced version v{version} and injected UI footer into {len(injected_files)} files.",
        }
