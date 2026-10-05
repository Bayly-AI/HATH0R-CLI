"""PMAT Bot for Hath0r CLI Control Tower.

Autonomous micro-bot servicing PMAT code churn, formal provability scores,
AST complexity analysis, and multi-dimensional reporting across suite worktrees.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_engine.analysis.pmat_stats_engine import pmat_stats_engine


class PmatBot:
    """Autonomous PMAT Bot for querying multi-dimensional stats, provability, and complexity."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()

    def doctor(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Perform health check of PMAT stats engine and repository state."""
        target = Path(repo_path) if repo_path else self.cwd
        return {
            "status": "OK",
            "bot_name": "PmatBot",
            "repo_path": str(target.resolve()),
            "is_git_repository": (target / ".git").exists(),
            "schema_contract": "contracts/hath0r-pmat-stats-report-v1.schema.json",
            "supported_intents": [
                "get PMAT stats",
                "analyze code churn",
                "check provability score",
                "calculate complexity score",
            ],
        }

    def get_stats(self, repo_path: Optional[str] = None, window_days: int = 30) -> Dict[str, Any]:
        """Generate multi-dimensional PMAT stats report."""
        target = Path(repo_path) if repo_path else self.cwd
        return pmat_stats_engine.generate_multi_dimensional_report(repo_path=target, days=window_days)

    def analyze_churn(self, repo_path: Optional[str] = None, window_days: int = 30) -> Dict[str, Any]:
        """Extract code churn subset report."""
        stats = self.get_stats(repo_path=repo_path, window_days=window_days)
        return {
            "repository": stats.get("repository"),
            "commit_hash": stats.get("commit_hash"),
            "churn": stats.get("churn"),
            "hotspots": [
                {
                    "file_path": h["file_path"],
                    "churn_score": h["churn_score"],
                    "risk_tier": h["risk_tier"],
                }
                for h in stats.get("hotspots", [])
            ],
        }

    def check_provability(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract formal provability score breakdown."""
        stats = self.get_stats(repo_path=repo_path)
        return {
            "repository": stats.get("repository"),
            "provability": stats.get("provability"),
            "provability_rankings": [
                {
                    "file_path": h["file_path"],
                    "provability_score": h["provability_score"],
                    "defect_probability": round(1.0 - h["provability_score"], 4),
                }
                for h in stats.get("hotspots", [])
            ],
        }

    def calculate_complexity(self, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract AST complexity metrics breakdown."""
        stats = self.get_stats(repo_path=repo_path)
        return {
            "repository": stats.get("repository"),
            "complexity": stats.get("complexity"),
            "complexity_rankings": [
                {
                    "file_path": h["file_path"],
                    "complexity_score": h["complexity_score"],
                    "risk_tier": h["risk_tier"],
                }
                for h in stats.get("hotspots", [])
            ],
        }

    def handle_conversational_intent(self, intent_text: str, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """Route operator conversational queries to appropriate PMAT metric handlers."""
        intent_lower = intent_text.lower().strip()
        if "churn" in intent_lower:
            return self.analyze_churn(repo_path=repo_path)
        elif "provability" in intent_lower:
            return self.check_provability(repo_path=repo_path)
        elif "complexity" in intent_lower:
            return self.calculate_complexity(repo_path=repo_path)
        else:
            return self.get_stats(repo_path=repo_path)


pmat_bot = PmatBot()
