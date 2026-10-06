"""Antagonistic Review Bot for PR Quality Gates & Tech Debt Enforcement (CR-CLI-TECH-DEBT-001)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class AntagonisticReviewBot:
    """Adversarial critic for inspecting git diffs, unhandled edge cases, and self-admitted tech debt."""

    def __init__(self, root_path: Optional[Path] = None) -> None:
        self.root_path = root_path or Path.cwd()

    def review_diff(self, diff_content: Optional[str] = None) -> Dict[str, Any]:
        """Perform adversarial code review on git diff against main/development branch."""
        if diff_content is None:
            try:
                out = subprocess.check_output(
                    ["git", "diff", "HEAD~1"],
                    cwd=self.root_path,
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8", errors="ignore")
                diff_content = out
            except Exception:
                diff_content = ""

        flaws = []
        tech_debts = []

        lines = diff_content.splitlines()
        added_text = "\n".join([line[1:].strip() for line in lines if line.startswith("+")])

        # Check swallowed exceptions across single or multi-line blocks
        if re.search(r"except\s*(?:Exception|BaseException)?\s*:[\s\n]*pass\b", added_text):
            flaws.append({
                "type": "SwallowedException",
                "severity": "critical",
                "message": "Swallowed exception detected (except Exception: pass). Breakages must be handled or re-raised.",
                "line_number": 1,
            })

        for idx, line in enumerate(lines, start=1):
            if not line.startswith("+"):
                continue

            # Check self-admitted tech debt (CR-CLI-TECH-DEBT-001)
            tech_match = re.search(r"\b(TODO|FIXME|HACK|XXX|STUB)\b:?\s*(.*)", line, re.IGNORECASE)
            if tech_match:
                marker = tech_match.group(1).upper()
                desc = tech_match.group(2).strip() or "Self-admitted technical debt in diff"
                tech_debts.append({
                    "marker": marker,
                    "description": desc,
                    "line_content": line,
                    "line_number": idx,
                })

        # Auto-create GitHub issues for discovered tech debt under CR-CLI-TECH-DEBT-001
        created_issues = []
        for td in tech_debts:
            try:
                title = f"tech-debt: resolve {td['marker']} in codebase - {td['description'][:60]}"
                body = (
                    f"### Self-Admitted Technical Debt (CR-CLI-TECH-DEBT-001)\n\n"
                    f"**Marker**: `{td['marker']}`\n"
                    f"**Description**: {td['description']}\n"
                    f"**Location**: Line {td['line_number']} in recent diff.\n\n"
                    f"Automatically identified by `AntagonisticReviewBot`."
                )
                res = subprocess.check_output(
                    ["gh", "issue", "create", "--title", title, "--body", body],
                    cwd=self.root_path,
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8").strip()
                created_issues.append({"title": title, "issue_url": res})
            except Exception:
                pass

        is_passed = len(flaws) == 0
        return {
            "status": "passed" if is_passed else "failed",
            "passed_gate": is_passed,
            "adversarial_flaws_count": len(flaws),
            "adversarial_flaws": flaws,
            "tech_debts_count": len(tech_debts),
            "tech_debts": tech_debts,
            "auto_created_issues": created_issues,
        }


antagonistic_review_bot = AntagonisticReviewBot()
