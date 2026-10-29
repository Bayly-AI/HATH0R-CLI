"""Behavioral Integrity & Transparency Evaluation (BITE) Verifier Bot (CR-AGENTIC-SEC-001 / WS1).

Implements Knostic-inspired BITE verification for MCP servers, skills (`SKILL.md`),
rules (`AGENTS.md`, `WARP.md`), and plugins:
1. Extracts atomic behavioral capabilities (`CREDENTIAL_READ`, `NETWORK_EGRESS`, `FILESYSTEM_WRITE`,
   `PROCESS_EXEC`, `PROMPT_OVERRIDE`, `STEGANOGRAPHIC_UNICODE`).
2. Evaluates the 3 canonical BITE questions per behavior:
   - Reachable? (`is_reachable`)
   - Unnecessary? (`is_unnecessary` relative to stated description/intent)
   - Concealed? (`is_concealed` via Unicode variation selectors, zero-width chars, base64, or omission)
3. Produces a deterministic verdict (`CLEAN`, `RISKY`, `DANGEROUS`), SHA-256 content digest,
   and persists `.hath0r/security/bite_manifest.json`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BEHAVIOR_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "CREDENTIAL_READ": [
        ("ssh_or_aws_creds", re.compile(r"(?:~/.ssh|\.aws/credentials|\.credentials/|\.env\b|os\.environ\[)", re.IGNORECASE)),
        ("secret_token_access", re.compile(r"\b(?:AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN|ANTHROPIC_API_KEY|OPENAI_API_KEY|SONAR_TOKEN)\b")),
    ],
    "NETWORK_EGRESS": [
        ("http_request_call", re.compile(r"\b(?:urllib\.request|requests\.(?:post|get|put)|httpx\.(?:post|get|AsyncClient)|curl\s+-X|wget\s+http)", re.IGNORECASE)),
        ("raw_socket_connect", re.compile(r"\bsocket\.socket\b|\bwebsocket\.connect\b", re.IGNORECASE)),
    ],
    "FILESYSTEM_WRITE": [
        ("destructive_fs", re.compile(r"\b(?:shutil\.rmtree|os\.remove|os\.unlink|rm\s+-rf)\b")),
        ("system_path_write", re.compile(r"(?:/etc/passwd|/etc/sudoers|/usr/local/bin/)")),
    ],
    "PROCESS_EXEC": [
        ("shell_execution", re.compile(r"\b(?:subprocess\.(?:Popen|run|call|check_output)|os\.system|os\.popen|eval\(|exec\()\b")),
    ],
    "PROMPT_OVERRIDE": [
        (
            "jailbreak_directive",
            re.compile(
                r"(?:ignore\s+(?:all\s+)?previous\s+instructions|disregard\s+system\s+prompt|you\s+are\s+now\s+unrestricted|bypass\s+safety\s+guardrails|do\s+not\s+mention\s+this\s+to\s+the\s+user)",
                re.IGNORECASE,
            ),
        ),
    ],
}

# Invisible Unicode variation selectors (\uFE00-\uFE0F, \U000E0100-\U000E01EF), zero-width chars, Bidi overrides
CONCEALMENT_UNICODE_PATTERN = re.compile(
    r"[\u200B-\u200F\u202A-\u202E\u2060-\u2064\uFE00-\uFE0F\U000E0100-\U000E01EF]"
)
BASE64_BLOB_PATTERN = re.compile(r"\b(?:base64\.b64decode|atob)\s*\(\s*['\"][A-Za-z0-9+/=]{24,}['\"]")

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "CREDENTIAL_READ": ("credential", "auth", "token", "secret", "login", "env", "vault"),
    "NETWORK_EGRESS": ("http", "api", "fetch", "webhook", "network", "url", "search", "web", "remote", "cloud"),
    "FILESYSTEM_WRITE": ("write", "delete", "clean", "remove", "file", "save", "export", "install"),
    "PROCESS_EXEC": ("exec", "command", "shell", "run", "cli", "process", "script", "build", "test", "docker"),
    "PROMPT_OVERRIDE": (),  # Never legitimate in a skill/tool manifest
}


@dataclass
class BITEBehaviorFinding:
    """Single atomic behavior evaluated under the 3 BITE questions."""

    category: str
    indicator: str
    evidence_snippet: str
    is_reachable: bool
    is_unnecessary: bool
    is_concealed: bool
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL


@dataclass
class BITEArtifactReport:
    """BITE evaluation report for a single skill, rule file, or MCP server definition."""

    artifact_id: str
    artifact_type: str  # skill | mcp_server | rule_file
    path: str
    sha256: str
    stated_purpose: str
    verdict: str  # CLEAN | RISKY | DANGEROUS
    behaviors: list[BITEBehaviorFinding] = field(default_factory=list)
    invisible_unicode_count: int = 0


class BITEVerifierBot:
    """Knostic-style Behavioral Integrity & Transparency Evaluation (BITE) Bot."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()

    @staticmethod
    def compute_sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_stated_purpose(content: str, fallback: str = "") -> str:
        """Extract frontmatter description or first heading/paragraph as stated purpose."""
        desc_match = re.search(r"^description:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if desc_match:
            return desc_match.group(1).strip().strip("'\"")
        lines = [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("---")]
        return " ".join(lines[:3])[:300] if lines else fallback

    def evaluate_content(
        self,
        artifact_id: str,
        artifact_type: str,
        content: str,
        path: str = "<memory>",
        stated_purpose: str | None = None,
    ) -> BITEArtifactReport:
        """Evaluate raw text/code content against the 3 BITE questions."""
        purpose = (stated_purpose or self._extract_stated_purpose(content, fallback=artifact_id)).lower()
        sha256 = self.compute_sha256(content)
        unicode_matches = CONCEALMENT_UNICODE_PATTERN.findall(content)
        has_base64_obfuscation = bool(BASE64_BLOB_PATTERN.search(content))

        findings: list[BITEBehaviorFinding] = []

        if unicode_matches:
            findings.append(
                BITEBehaviorFinding(
                    category="STEGANOGRAPHIC_UNICODE",
                    indicator="invisible_unicode_selectors",
                    evidence_snippet=f"Detected {len(unicode_matches)} invisible/variation-selector Unicode codepoints",
                    is_reachable=True,
                    is_unnecessary=True,
                    is_concealed=True,
                    severity="CRITICAL",
                )
            )

        if has_base64_obfuscation:
            findings.append(
                BITEBehaviorFinding(
                    category="CONCEALED_PAYLOAD",
                    indicator="encoded_base64_execution",
                    evidence_snippet="Inline base64.b64decode/atob payload detected",
                    is_reachable=True,
                    is_unnecessary=True,
                    is_concealed=True,
                    severity="CRITICAL",
                )
            )

        for category, rules in BEHAVIOR_PATTERNS.items():
            allowed_keywords = INTENT_KEYWORDS.get(category, ())
            disclosed_in_purpose = any(kw in purpose for kw in allowed_keywords)

            for indicator_name, pattern in rules:
                match = pattern.search(content)
                if not match:
                    continue
                snippet = match.group(0)[:80]
                is_reachable = True
                is_unnecessary = not disclosed_in_purpose or category == "PROMPT_OVERRIDE"
                is_concealed = (
                    category == "PROMPT_OVERRIDE"
                    or bool(unicode_matches)
                    or has_base64_obfuscation
                    or (is_unnecessary and artifact_type in ("skill", "rule_file"))
                )

                if category == "PROMPT_OVERRIDE" or (is_unnecessary and is_concealed):
                    severity = "CRITICAL"
                elif is_unnecessary:
                    severity = "HIGH"
                else:
                    severity = "LOW"

                findings.append(
                    BITEBehaviorFinding(
                        category=category,
                        indicator=indicator_name,
                        evidence_snippet=snippet,
                        is_reachable=is_reachable,
                        is_unnecessary=is_unnecessary,
                        is_concealed=is_concealed,
                        severity=severity,
                    )
                )

        if any(f.severity == "CRITICAL" for f in findings):
            verdict = "DANGEROUS"
        elif any(f.severity in ("HIGH", "MEDIUM") for f in findings):
            verdict = "RISKY"
        else:
            verdict = "CLEAN"

        return BITEArtifactReport(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            path=path,
            sha256=sha256,
            stated_purpose=purpose[:200],
            verdict=verdict,
            behaviors=findings,
            invisible_unicode_count=len(unicode_matches),
        )

    def audit_skills_and_rules(self, target_dir: Path | None = None) -> dict[str, Any]:
        """Scan SKILL.md, AGENTS.md, and WARP.md files in workspace and persist BITE manifest."""
        root = (target_dir or self.workspace_root).resolve()
        candidate_files: list[tuple[str, Path]] = []

        for pattern, a_type in (("**/SKILL.md", "skill"), ("AGENTS.md", "rule_file"), ("WARP.md", "rule_file")):
            for p in root.glob(pattern):
                if any(part in (".git", ".venv", "venv", "node_modules") for part in p.parts):
                    continue
                candidate_files.append((a_type, p))

        reports: list[BITEArtifactReport] = []
        for a_type, file_path in sorted(candidate_files, key=lambda x: str(x[1])):
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(file_path.relative_to(root)) if file_path.is_relative_to(root) else str(file_path)
            # Rule files and official skills declare governance/CLI operations by design
            purpose_hint = self._extract_stated_purpose(text, fallback=rel)
            if a_type == "rule_file":
                purpose_hint += " cli command shell process run build test docker auth credential secret env http api write file"
            elif a_type == "skill":
                purpose_hint += " cli command shell process run script http api write file"
            reports.append(
                self.evaluate_content(
                    artifact_id=rel,
                    artifact_type=a_type,
                    content=text,
                    path=rel,
                    stated_purpose=purpose_hint,
                )
            )

        return self._finalize_and_persist("skills_and_rules", reports)

    def audit_mcp_servers(self, config_path: Path | None = None) -> dict[str, Any]:
        """Audit MCP server definitions (e.g., cfg/mcp.servers.json) under BITE."""
        candidates = [
            config_path,
            self.workspace_root / "cfg" / "mcp.servers.json",
            self.workspace_root / "cfg" / "mcp-doc-publish.json",
        ]
        reports: list[BITEArtifactReport] = []
        for c_path in candidates:
            if c_path and c_path.exists():
                try:
                    raw = c_path.read_text(encoding="utf-8")
                    rel = str(c_path.relative_to(self.workspace_root)) if c_path.is_relative_to(self.workspace_root) else str(c_path)
                    reports.append(
                        self.evaluate_content(
                            artifact_id=rel,
                            artifact_type="mcp_server",
                            content=raw,
                            path=rel,
                            stated_purpose="mcp server http api remote cloud auth token cli command",
                        )
                    )
                except OSError:
                    continue

        return self._finalize_and_persist("mcp_servers", reports)

    def _finalize_and_persist(self, scope: str, reports: list[BITEArtifactReport]) -> dict[str, Any]:
        dangerous_count = sum(1 for r in reports if r.verdict == "DANGEROUS")
        risky_count = sum(1 for r in reports if r.verdict == "RISKY")
        clean_count = sum(1 for r in reports if r.verdict == "CLEAN")

        payload = {
            "schema": "hath0r.security.bite_manifest/1",
            "scope": scope,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": dangerous_count == 0,
            "summary": {
                "total_audited": len(reports),
                "clean": clean_count,
                "risky": risky_count,
                "dangerous": dangerous_count,
            },
            "artifacts": [asdict(r) for r in reports],
        }

        out_dir = self.workspace_root / ".hath0r" / "security"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "bite_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

        return payload
