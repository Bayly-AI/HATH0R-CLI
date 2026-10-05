"""ChurnManagerBot & HotspotRefactorBot Orchestration for Hath0r CLI."""

from __future__ import annotations

import collections
import datetime
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("hath0r.bots.churn")


class ChurnManagerBot:
    """Autonomous bot for repository code churn auditing, hotspot ranking, and PR gating."""

    def __init__(self, pmat_bin: str = "pmat") -> None:
        self.pmat_bin = pmat_bin

    def is_pmat_available(self) -> bool:
        """Check if native PMAT binary is installed in system PATH."""
        return shutil.which(self.pmat_bin) is not None

    def doctor(self, repo_path: Optional[str | Path] = None) -> Dict[str, Any]:
        """Probe PMAT binary, MCP server registration, and repository status."""
        target_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        is_git = (target_path / ".git").exists()

        pmat_native = self.is_pmat_available()
        status_mode = "native_binary" if pmat_native else "git_log_substrate"

        # Check MCP registration
        mcp_cfg_path = Path("/Users/raybayly/Development/OpenSource/HATH0R-CLI/cfg/mcp.servers.json")
        mcp_registered = False
        if mcp_cfg_path.exists():
            try:
                with open(mcp_cfg_path, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                    mcp_registered = any(
                        s.get("id") == "pmat-mcp" for s in cfg_data.get("servers", [])
                    )
            except Exception:
                mcp_registered = False

        return {
            "status": "OK",
            "repo_path": str(target_path),
            "is_git_repository": is_git,
            "pmat_native_binary": pmat_native,
            "engine_mode": status_mode,
            "mcp_registered": mcp_registered,
            "schema_contract": "contracts/hath0r-pmat-churn-report-v1.schema.json",
        }

    def analyze(
        self,
        repo_path: Optional[str | Path] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Execute time-windowed code churn analysis."""
        target_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()

        # Try hath0r_engine PmatAdapter first if available
        try:
            from hath0r_engine.analysis.pmat_adapter import pmat_adapter
            return pmat_adapter.analyze_churn(target_path, days=days)
        except ImportError:
            pass

        return self._local_git_analysis(target_path, days=days)

    def _local_git_analysis(self, target_path: Path, days: int = 30) -> Dict[str, Any]:
        """Standalone fallback git analysis."""
        since_date = f"{days} days ago"
        cmd = [
            "git",
            "log",
            f"--since={since_date}",
            "--numstat",
            "--pretty=format:COMMIT:%H",
            "--no-merges",
        ]

        try:
            res = subprocess.run(
                cmd,
                cwd=str(target_path),
                capture_output=True,
                text=True,
                check=True,
            )
            raw_output = res.stdout
        except Exception as e:
            logger.error("Git log execution failed: %s", e)
            raw_output = ""

        file_churn: Dict[str, int] = collections.defaultdict(int)
        file_added: Dict[str, int] = collections.defaultdict(int)
        file_deleted: Dict[str, int] = collections.defaultdict(int)
        co_changes: Dict[str, Set[str]] = collections.defaultdict(set)

        current_commit_files: List[str] = []
        commits_evaluated = 0

        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("COMMIT:"):
                commits_evaluated += 1
                if current_commit_files:
                    for f1 in current_commit_files:
                        for f2 in current_commit_files:
                            if f1 != f2:
                                co_changes[f1].add(f2)
                current_commit_files = []
                continue

            parts = line.split("\t")
            if len(parts) >= 3:
                added_str, deleted_str, path_str = parts[0], parts[1], parts[2]
                if added_str == "-" or deleted_str == "-":
                    continue
                try:
                    added = int(added_str)
                    deleted = int(deleted_str)
                except ValueError:
                    continue

                file_churn[path_str] += 1
                file_added[path_str] += added
                file_deleted[path_str] += deleted
                current_commit_files.append(path_str)

        if current_commit_files:
            for f1 in current_commit_files:
                for f2 in current_commit_files:
                    if f1 != f2:
                        co_changes[f1].add(f2)

        try:
            head_sha = (
                subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(target_path),
                    text=True,
                )
                .strip()
            )
        except Exception:
            head_sha = "unknown"

        hotspots: List[Dict[str, Any]] = []
        total_churn_lines = 0

        for fpath, churn_count in file_churn.items():
            added = file_added[fpath]
            deleted = file_deleted[fpath]
            lines_churn = added + deleted
            total_churn_lines += lines_churn

            # Complexity estimate
            abs_file = target_path / fpath
            complexity_score = 1.0
            if abs_file.exists() and abs_file.is_file():
                try:
                    content = abs_file.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    branching_keywords = {"if ", "elif ", "for ", "while ", "case ", "catch ", "except ", "match "}
                    branch_count = sum(1 for line in lines for kw in branching_keywords if kw in line.strip())
                    complexity_score = round(min(50.0, 1.0 + (branch_count * 0.5)), 2)
                except Exception:
                    complexity_score = 1.0

            norm_freq = min(1.0, churn_count / 15.0)
            norm_vol = min(1.0, lines_churn / 600.0)
            norm_comp = min(1.0, complexity_score / 30.0)
            volatility_score = round((norm_freq * 0.40) + (norm_vol * 0.30) + (norm_comp * 0.30), 4)

            if volatility_score >= 0.75:
                risk_tier = "CRITICAL"
            elif volatility_score >= 0.50:
                risk_tier = "HIGH"
            elif volatility_score >= 0.25:
                risk_tier = "MEDIUM"
            else:
                risk_tier = "LOW"

            co_list = sorted(list(co_changes[fpath]))[:5]

            hotspots.append(
                {
                    "file_path": fpath,
                    "churn_count": churn_count,
                    "lines_added": added,
                    "lines_deleted": deleted,
                    "complexity_score": complexity_score,
                    "volatility_score": volatility_score,
                    "risk_tier": risk_tier,
                    "co_changing_files": co_list,
                }
            )

        hotspots.sort(key=lambda x: x["volatility_score"], reverse=True)
        mean_vol = (
            round(sum(h["volatility_score"] for h in hotspots) / len(hotspots), 4)
            if hotspots
            else 0.0
        )

        return {
            "schema_version": "hath0r.pmat.churn/1",
            "repository": str(target_path.name),
            "commit_hash": head_sha,
            "analysis_window_days": days,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "summary": {
                "total_files_analyzed": len(hotspots),
                "total_commits_evaluated": commits_evaluated,
                "total_churn_lines": total_churn_lines,
                "mean_volatility_score": mean_vol,
                "hotspot_count": len([h for h in hotspots if h["risk_tier"] in ("HIGH", "CRITICAL")]),
            },
            "hotspots": hotspots,
            "recommendations": [
                f"Refactor critical hotspot '{hotspots[0]['file_path']}' with volatility {hotspots[0]['volatility_score']}"
            ]
            if hotspots and hotspots[0]["risk_tier"] == "CRITICAL"
            else [],
        }

    def hotspots(
        self,
        repo_path: Optional[str | Path] = None,
        days: int = 30,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return top N hotspot files."""
        report = self.analyze(repo_path, days=days)
        return report.get("hotspots", [])[:limit]

    def pr_risk(
        self,
        repo_path: Optional[str | Path] = None,
        base_branch: str = "development",
    ) -> Dict[str, Any]:
        """Evaluate PR risk against git base branch."""
        target_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        try:
            from hath0r_engine.analysis.pmat_adapter import pmat_adapter
            return pmat_adapter.evaluate_pr_risk(target_path, base_branch=base_branch)
        except ImportError:
            pass

        report = self.analyze(target_path, days=30)
        hotspot_map = {h["file_path"]: h for h in report.get("hotspots", [])}

        try:
            diff_raw = subprocess.check_output(
                ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
                cwd=str(target_path),
                text=True,
            )
        except Exception:
            diff_raw = ""

        changed_files = [f.strip() for f in diff_raw.splitlines() if f.strip()]
        touched_hotspots: List[Dict[str, Any]] = []
        max_volatility = 0.0

        for f in changed_files:
            if f in hotspot_map:
                h = hotspot_map[f]
                touched_hotspots.append(h)
                if h["volatility_score"] > max_volatility:
                    max_volatility = h["volatility_score"]

        if max_volatility >= 0.75:
            overall_risk = "CRITICAL"
            safe_to_merge = False
            rec_tier = "REASONING"
        elif max_volatility >= 0.50:
            overall_risk = "HIGH"
            safe_to_merge = True
            rec_tier = "REASONING"
        elif max_volatility >= 0.25:
            overall_risk = "MEDIUM"
            safe_to_merge = True
            rec_tier = "STANDARD"
        else:
            overall_risk = "LOW"
            safe_to_merge = True
            rec_tier = "LIGHT"

        return {
            "branch_evaluated": "HEAD",
            "base_branch": base_branch,
            "changed_files_count": len(changed_files),
            "touched_hotspots": touched_hotspots,
            "max_volatility_score": max_volatility,
            "overall_risk_tier": overall_risk,
            "safe_to_merge": safe_to_merge,
            "recommended_reasoning_tier": rec_tier,
        }

    def render_ui_html(
        self,
        repo_path: Optional[str | Path] = None,
        days: int = 30,
    ) -> str:
        """Render Generative UI HTML dashboard."""
        target_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        report = self.analyze(target_path, days=days)

        try:
            from hath0r_engine.ui.churn_heatmap import ChurnHeatmapComponent
            comp = ChurnHeatmapComponent(report_data=report)
            return comp.render_html()
        except ImportError:
            pass

        # Built-in lightweight fallback renderer
        summary = report.get("summary", {})
        hotspots = report.get("hotspots", [])
        rows_html = "".join(
            f"<tr><td>{h['file_path']}</td><td>{h['churn_count']}</td><td>{h['complexity_score']}</td><td>{h['volatility_score']}</td><td>{h['risk_tier']}</td></tr>"
            for h in hotspots
        )

        return f"""<!DOCTYPE html>
<html>
<head><title>Hath0r Code Churn Heatmap</title></head>
<body>
  <h1>PMAT Churn Dashboard: {report.get('repository')}</h1>
  <p>Analyzed {summary.get('total_files_analyzed', 0)} files ({summary.get('hotspot_count', 0)} hotspots)</p>
  <table border="1">
    <tr><th>File</th><th>Churn</th><th>Complexity</th><th>Volatility</th><th>Risk</th></tr>
    {rows_html}
  </table>
</body>
</html>"""


class HotspotRefactorBot:
    """Proposes decoupled architectural refactorings for high-volatility modules."""

    def propose_refactoring(
        self,
        file_path: str,
        repo_path: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """Generate structured refactoring recommendations."""
        target_path = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        abs_file = target_path / file_path

        if not abs_file.exists():
            return {
                "file_path": file_path,
                "error": f"Target file '{file_path}' does not exist in workspace.",
            }

        # Analyze file structure
        content = abs_file.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()

        steps: List[str] = [
            f"Extract complex internal branch logic in {file_path} into isolated strategy handlers.",
            "Introduce Facade / Protocol boundary to decouple co-changing modules.",
            "Implement automated Playwright/unit test coverage targeting edge cases.",
        ]

        return {
            "file_path": file_path,
            "line_count": len(lines),
            "refactoring_type": "MODULAR_DECOUPLING",
            "proposed_steps": steps,
            "suggested_pattern": "Strategy / Dependency Injection",
            "risk_mitigation": "Reduces co-change cascade failures and isolates regression scope.",
        }


churn_manager_bot = ChurnManagerBot()
hotspot_refactor_bot = HotspotRefactorBot()
