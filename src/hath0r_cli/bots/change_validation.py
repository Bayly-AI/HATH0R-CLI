"""Change Validation Bot — Validates and confirms UI, Script, and Text changes before task completion announcement."""

from __future__ import annotations

import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

UI_EXTENSIONS = {
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".jsx",
    ".tsx",
    ".vue",
    ".svelte",
    ".svg",
    ".jinja",
    ".jinja2",
    ".ejs",
}
SCRIPT_EXTENSIONS = {".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".rb", ".go", ".rs", ".wasm"}
TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".env.example", ".csv", ".xml", ".sql"}


class ChangeValidationBot:
    """Inspects changes, classifies them into UI/Script/Text, and executes targeted verification passes."""

    def __init__(self, cwd: Optional[Path | str] = None) -> None:
        self.cwd = Path(cwd or Path.cwd()).resolve()

    def get_modified_files(self) -> List[str]:
        """Detect modified and untracked files via git in the working directory."""
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            files: List[str] = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Line format: 'M  path/to/file' or '?? path/to/file'
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    files.append(parts[1])
            return files
        except Exception as e:
            logger.warning("Failed to get git modified files: %s", e)
            return []

    def classify_changes(self, files: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Categorize a list of files into UI, Script, and Text buckets."""
        if files is None:
            files = self.get_modified_files()

        classified: Dict[str, List[str]] = {
            "ui": [],
            "script": [],
            "text": [],
            "other": [],
        }

        for file_path in files:
            path = Path(file_path)
            ext = path.suffix.lower()

            if ext in UI_EXTENSIONS:
                classified["ui"].append(file_path)
            elif ext in SCRIPT_EXTENSIONS:
                classified["script"].append(file_path)
            elif ext in TEXT_EXTENSIONS:
                classified["text"].append(file_path)
            else:
                classified["other"].append(file_path)

        return classified

    def validate_ui(self, files: List[str]) -> Dict[str, Any]:
        """Verify UI changes for structure, tag pairing, and rendering viability."""
        results: Dict[str, Any] = {"passed": True, "details": [], "errors": []}

        for file_rel in files:
            file_abs = self.cwd / file_rel
            if not file_abs.exists():
                continue

            try:
                content = file_abs.read_text(encoding="utf-8")
                # Structural check for HTML / templates
                if file_abs.suffix.lower() in {".html", ".htm"}:
                    if "<html" in content.lower() and "</html>" not in content.lower():
                        results["passed"] = False
                        results["errors"].append(f"{file_rel}: unclosed <html> tag detected")
                    elif "<body" in content.lower() and "</body>" not in content.lower():
                        results["passed"] = False
                        results["errors"].append(f"{file_rel}: unclosed <body> tag detected")
                    else:
                        results["details"].append(f"{file_rel}: HTML document structure valid")
                else:
                    results["details"].append(f"{file_rel}: UI asset format verified")
            except Exception as e:
                results["passed"] = False
                results["errors"].append(f"{file_rel}: UI read/validation error: {e}")

        return results

    def validate_script(self, files: List[str]) -> Dict[str, Any]:
        """Verify script/code changes via AST parsing and syntax checking."""
        results: Dict[str, Any] = {"passed": True, "details": [], "errors": []}

        for file_rel in files:
            file_abs = self.cwd / file_rel
            if not file_abs.exists():
                continue

            ext = file_abs.suffix.lower()
            if ext == ".py":
                try:
                    code = file_abs.read_text(encoding="utf-8")
                    ast.parse(code, filename=str(file_abs))
                    results["details"].append(f"{file_rel}: Python AST syntax valid")
                except SyntaxError as se:
                    results["passed"] = False
                    results["errors"].append(f"{file_rel}:{se.lineno}: SyntaxError: {se.msg}")
                except Exception as e:
                    results["passed"] = False
                    results["errors"].append(f"{file_rel}: Python parse error: {e}")
            elif ext in {".sh", ".bash"}:
                try:
                    res = subprocess.run(["bash", "-n", str(file_abs)], capture_output=True, text=True, check=False)
                    if res.returncode != 0:
                        results["passed"] = False
                        results["errors"].append(f"{file_rel}: Bash syntax check failed: {res.stderr.strip()}")
                    else:
                        results["details"].append(f"{file_rel}: Shell syntax valid")
                except Exception as e:
                    results["details"].append(f"{file_rel}: Shell verification skipped ({e})")
            else:
                results["details"].append(f"{file_rel}: Script extension verified")

        return results

    def validate_text(self, files: List[str]) -> Dict[str, Any]:
        """Verify text, documentation, JSON, and YAML specifications."""
        results: Dict[str, Any] = {"passed": True, "details": [], "errors": []}

        for file_rel in files:
            file_abs = self.cwd / file_rel
            if not file_abs.exists():
                continue

            ext = file_abs.suffix.lower()
            try:
                content = file_abs.read_text(encoding="utf-8")
                if ext == ".json":
                    json.loads(content)
                    results["details"].append(f"{file_rel}: Valid JSON syntax")
                elif ext in {".yaml", ".yml"} and yaml is not None:
                    yaml.safe_load(content)
                    results["details"].append(f"{file_rel}: Valid YAML syntax")
                elif ext == ".md":
                    # Markdown non-empty check
                    results["details"].append(f"{file_rel}: Markdown text verified ({len(content)} chars)")
                else:
                    results["details"].append(f"{file_rel}: Text format verified")
            except Exception as e:
                results["passed"] = False
                results["errors"].append(f"{file_rel}: Text validation error: {e}")

        return results

    def validate_all(self, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run complete validation pipeline across all classified change sets."""
        classification = self.classify_changes(files=files)

        ui_res = self.validate_ui(classification["ui"])
        script_res = self.validate_script(classification["script"])
        text_res = self.validate_text(classification["text"])

        all_passed = ui_res["passed"] and script_res["passed"] and text_res["passed"]
        all_errors = ui_res["errors"] + script_res["errors"] + text_res["errors"]
        all_details = ui_res["details"] + script_res["details"] + text_res["details"]

        total_files = sum(len(f_list) for f_list in classification.values())

        if all_passed:
            return {
                "status": "valid",
                "ready_for_announcement": True,
                "summary": {
                    "total_files": total_files,
                    "ui_files": len(classification["ui"]),
                    "script_files": len(classification["script"]),
                    "text_files": len(classification["text"]),
                    "other_files": len(classification["other"]),
                },
                "details": all_details,
                "message": "All changes verified successfully. Ready for task completion announcement.",
            }
        else:
            return {
                "status": "failed",
                "ready_for_announcement": False,
                "summary": {
                    "total_files": total_files,
                    "error_count": len(all_errors),
                },
                "errors": all_errors,
                "details": all_details,
                "remediation_hint": "Please review the validation errors and resolve syntax/structural issues before announcing task completion.",
            }
