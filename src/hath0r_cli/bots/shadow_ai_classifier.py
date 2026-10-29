"""AgentSonar Shadow-AI Commit & Workflow Classifier Bot (CR-AGENTIC-SEC-001 / WS6).

Implements Knostic AgentSonar-inspired weighted 0-100 scoring model to classify Git commits
and repository workflows as:
- `AUTONOMOUS_AGENT` (score >= 70)
- `AI_ASSISTED_HYBRID` (40 <= score < 70)
- `HUMAN_AUTHORED` (score < 40)
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

COAUTHOR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("claude_code", re.compile(r"Co-Authored-By:\s*Claude|noreply@anthropic\.com", re.IGNORECASE)),
    ("github_copilot", re.compile(r"Co-Authored-By:\s*Copilot|copilot@", re.IGNORECASE)),
    ("cursor_agent", re.compile(r"Co-Authored-By:\s*Cursor|cursoragent", re.IGNORECASE)),
    ("openai_codex", re.compile(r"Co-Authored-By:\s*(?:OpenAI|Codex)", re.IGNORECASE)),
    ("hath0r_bot", re.compile(r"\[hath0r-bot\]|CR-TASK-EVAL-001|CR-MEMORY-COMPOUND-001", re.IGNORECASE)),
]

AGENT_FILE_FOOTPRINTS = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    ".github/copilot-instructions.md",
    ".hath0r/evals/latest.json",
    ".hath0r/memory/graph.json",
)


@dataclass
class CommitAgentSonarScore:
    """AgentSonar behavioral score for a single commit."""

    commit_sha: str
    author: str
    subject: str
    score: int
    classification: str  # AUTONOMOUS_AGENT | AI_ASSISTED_HYBRID | HUMAN_AUTHORED
    signals: list[str] = field(default_factory=list)


class ShadowAIClassifierBot:
    """Classifies commits and workspace footprints using AgentSonar behavioral heuristics."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    def score_commit(
        self,
        commit_sha: str,
        author: str,
        message: str,
        changed_files: list[str] | None = None,
    ) -> CommitAgentSonarScore:
        score = 0
        signals: list[str] = []
        files = changed_files or []

        for label, pat in COAUTHOR_PATTERNS:
            if pat.search(message):
                score += 55
                signals.append(f"signature:{label}")

        # Conventional commit + multi-bullet structured body typical of agentic PR synthesis
        if re.match(r"^(?:feat|fix|chore|docs|refactor|test)(?:\([^)]+\))?:\s+.+", message):
            score += 15
            signals.append("conventional_header")

        bullet_lines = [ln for ln in message.splitlines() if ln.strip().startswith(("- ", "* "))]
        if len(bullet_lines) >= 3:
            score += 15
            signals.append("structured_multi_bullet_body")

        if any(f in AGENT_FILE_FOOTPRINTS or f.startswith(".hath0r/") for f in files):
            score += 25
            signals.append("agent_substrate_file_touch")

        if len(files) >= 8:
            score += 10
            signals.append("high_file_fanout")

        bounded = min(100, score)
        if bounded >= 70:
            classification = "AUTONOMOUS_AGENT"
        elif bounded >= 40:
            classification = "AI_ASSISTED_HYBRID"
        else:
            classification = "HUMAN_AUTHORED"

        subject = message.splitlines()[0] if message.splitlines() else ""
        return CommitAgentSonarScore(
            commit_sha=commit_sha[:12],
            author=author,
            subject=subject[:100],
            score=bounded,
            classification=classification,
            signals=signals,
        )

    def scan_recent_commits(self, limit: int = 10) -> dict[str, Any]:
        """Inspect recent git commits in workspace and compute AgentSonar distribution."""
        proc = subprocess.run(
            ["git", "log", f"-n{max(1, limit)}", "--pretty=format:%H%x1f%an%x1f%B%x1e"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        records: list[CommitAgentSonarScore] = []
        if proc.returncode == 0 and proc.stdout.strip():
            for raw_entry in proc.stdout.split("\x1e"):
                entry = raw_entry.strip()
                if not entry:
                    continue
                parts = entry.split("\x1f")
                if len(parts) < 3:
                    continue
                sha, author, msg = parts[0].strip(), parts[1].strip(), parts[2].strip()
                f_proc = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
                    cwd=self.workspace_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                files = [ln.strip() for ln in f_proc.stdout.splitlines() if ln.strip()] if f_proc.returncode == 0 else []
                records.append(self.score_commit(sha, author, msg, files))

        counts = {
            "AUTONOMOUS_AGENT": sum(1 for r in records if r.classification == "AUTONOMOUS_AGENT"),
            "AI_ASSISTED_HYBRID": sum(1 for r in records if r.classification == "AI_ASSISTED_HYBRID"),
            "HUMAN_AUTHORED": sum(1 for r in records if r.classification == "HUMAN_AUTHORED"),
        }
        present_footprints = [fp for fp in AGENT_FILE_FOOTPRINTS if (self.workspace_root / fp).exists()]

        return {
            "workspace": str(self.workspace_root),
            "commits_analyzed": len(records),
            "distribution": counts,
            "detected_agent_footprints": present_footprints,
            "commits": [asdict(r) for r in records],
        }
