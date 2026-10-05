"""Dynamic MCP Server Mounting and In-Flight Security Policy Engine for Hath0r CLI."""

from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PolicyVerdict:
    """Security assessment result for an in-flight tool invocation."""

    allowed: bool
    risk_level: str  # low | medium | high | critical
    rule_triggered: Optional[str] = None
    reason: str = "Passed all safety policies"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level,
            "rule_triggered": self.rule_triggered,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


def wrap_untrusted_content(content: str, tag: str = "untrusted_retrieved_content") -> str:
    """Enforce structured XML data wrapper with automatic tag escaping for untrusted content."""
    escaped = html.escape(content).replace("<", "&lt;").replace(">", "&gt;")
    return f"<{tag}>\n{escaped}\n</{tag}>"


def sanitize_prompt_input(text: str) -> str:
    """Neutralize direct system prompt injection override commands in input streams."""
    injection_patterns = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)", re.I),
        re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)", re.I),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.I),
        re.compile(r"system\s+override", re.I),
        re.compile(r"act\s+as\s+DAN\b", re.I),
    ]
    sanitized = text
    for pat in injection_patterns:
        sanitized = pat.sub("[NEUTRALIZED_PROMPT_INJECTION]", sanitized)
    return sanitized


class SecretSanitizer:
    """Automated secret redaction filter for logging, transcripts, and CLI output streams (SEC-LEAK-001)."""

    SECRET_PATTERNS = [
        re.compile(r"sk-[a-z0-9_\-]{20,}", re.I),
        re.compile(r"ghp_[a-z0-9]{36}", re.I),
        re.compile(r"gho_[a-z0-9]{36}", re.I),
        re.compile(r"github_pat_[a-z0-9_\-]{20,}", re.I),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"Bearer\s+[a-z0-9\-\._~\+\/]+=*", re.I),
        re.compile(r"(postgres|postgresql|mysql|mongodb|redis)://[a-z0-9_\-]+:[^@\s]+@[a-z0-9_\-\.]+", re.I),
        re.compile(r"-----BEGIN\s+(RSA|EC|OPENSSH|PRIVATE)\s+KEY-----[\s\S]*?-----END\s+\1\s+KEY-----", re.I),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Replace all secret patterns in text with [REDACTED_SECRET]."""
        if not text:
            return text
        sanitized = text
        for pattern in cls.SECRET_PATTERNS:
            sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized


class MCPSecurityPolicyEngine:
    """Evaluates agent tool arguments in-flight to prevent prompt injection, data leakage, and destructive tool misuse."""

    DIRECT_INJECTION = [
        (
            re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)", re.I),
            "CRITICAL: Direct system prompt override attempt (ignore previous instructions)",
        ),
        (
            re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+(instructions|prompts|rules)", re.I),
            "CRITICAL: Direct system prompt override attempt (disregard previous instructions)",
        ),
        (
            re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.I),
            "HIGH: Adversarial mode-switching override attempt",
        ),
        (
            re.compile(r"system\s+override\s*:", re.I),
            "CRITICAL: Direct system override signature detected",
        ),
        (
            re.compile(r"forget\s+(all\s+)?(previous|prior)\s+(rules|guidelines)", re.I),
            "HIGH: Prompt injection rule wiping attempt",
        ),
    ]

    INDIRECT_INJECTION = [
        (
            re.compile(r"\[SYSTEM\s+INSTRUCTION\]", re.I),
            "HIGH: Indirect prompt injection via system instruction tag in external payload",
        ),
        (
            re.compile(r"<system_override>", re.I),
            "HIGH: Indirect prompt injection via fake system_override XML tag",
        ),
        (
            re.compile(r"AI\s+Assistant:\s*Ignore\s+rules", re.I),
            "HIGH: Indirect payload attempting role impersonation override",
        ),
    ]

    SECRET_LEAKAGE = [
        (
            re.compile(r"(sk-[a-z0-9_\-]{20,}|ghp_[a-z0-9]{36}|AKIA[0-9A-Z]{16})", re.I),
            "HIGH: Direct API key / secret credential detected in tool arguments",
        ),
    ]

    DESTRUCTIVE_OPERATIONS = [
        (
            re.compile(r"git\s+push\s+.*(--force|-f)\b", re.I),
            "CRITICAL: Unauthorized git force push operation blocked (SEC-TOOL-002)",
        ),
        (
            re.compile(r"git\s+branch\s+(-D|--delete\s+--force)\b", re.I),
            "HIGH: Unsafe git force branch deletion blocked (SEC-TOOL-002)",
        ),
    ]

    DANGEROUS_COMMANDS = [
        (
            re.compile(r"rm\s+-[rf]*\s+(?:/|/\*|~|\$HOME)", re.I),
            "CRITICAL: Destructive root/home filesystem deletion",
        ),
        (
            re.compile(r"(?:curl|wget)\s+[^|\r\n]+\|\s*(?:bash|sh|zsh)", re.I),
            "CRITICAL: Unverified remote script execution via pipe",
        ),
        (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.I), "CRITICAL: Fork bomb denial of service"),
        (re.compile(r"mkfs(\.\w+)?\s+", re.I), "CRITICAL: Filesystem format attempt"),
        (re.compile(r"chmod\s+(-R\s+)?777\s+/", re.I), "HIGH: Global permission escalation"),
    ]

    PATH_TRAVERSAL = [
        (re.compile(r"(\.\./){2,}", re.I), "HIGH: Directory traversal escape"),
        (
            re.compile(r"/(etc/(passwd|shadow)|root/\.ssh|\.aws/credentials|\.credentials)", re.I),
            "CRITICAL: Sensitive credential / system file access",
        ),
    ]

    SQL_DESTRUCTIVE = [
        (re.compile(r"\bDROP\s+(DATABASE|SCHEMA|TABLE)\b", re.I), "HIGH: Destructive SQL drop operation"),
        (re.compile(r"\bTRUNCATE\s+TABLE\b", re.I), "HIGH: Destructive SQL truncate operation"),
    ]

    ROLE_PERMISSIONS: Dict[str, List[str]] = {
        "read_only": ["view_file", "search_code", "list_dir", "read_url_content", "search_web"],
        "workspace_write": [
            "view_file",
            "search_code",
            "list_dir",
            "read_url_content",
            "search_web",
            "write_to_file",
            "replace_file_content",
            "run_command",
        ],
        "admin_system": ["*"],
    }

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()

    def list_rules(self) -> List[Dict[str, Any]]:
        """List active security guardrail rules."""
        return [
            {
                "id": "SEC-INJ-001",
                "name": "Direct Prompt Injection Guard",
                "risk": "CRITICAL",
                "description": "Blocks direct system prompt override signatures and adversarial prompt patterns.",
            },
            {
                "id": "SEC-INJ-002",
                "name": "Indirect Prompt Injection Guard",
                "risk": "HIGH",
                "description": "Blocks indirect malicious prompt payloads embedded in retrieved content.",
            },
            {
                "id": "SEC-LEAK-001",
                "name": "Secret Redaction Filter",
                "risk": "HIGH",
                "description": "Redacts API tokens, SSH keys, Bearer headers, and connection strings.",
            },
            {
                "id": "SEC-TOOL-001",
                "name": "Workspace Boundary Sandbox Guard",
                "risk": "CRITICAL",
                "description": "Enforces strict workspace directory isolation for write/delete tools.",
            },
            {
                "id": "SEC-TOOL-002",
                "name": "Destructive Operation Guard",
                "risk": "CRITICAL",
                "description": "Blocks unapproved force pushes, schema drops, and process termination.",
            },
            {
                "id": "SEC-CMD-001",
                "name": "Dangerous Shell Commands",
                "risk": "CRITICAL",
                "description": "Blocks rm -rf /, pipe-to-shell, and fork bombs.",
            },
        ]

    def validate_workspace_boundary(self, target_path: str) -> bool:
        """Verify target path is inside workspace boundary (SEC-TOOL-001)."""
        try:
            target = Path(target_path).resolve()
            root = self.workspace_root.resolve()
            return root == target or root in target.parents
        except Exception:
            return False

    def evaluate_tool_permissions(
        self,
        role: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> PolicyVerdict:
        """Evaluate fine-grained tool RBAC profiles and workspace bounds (SEC-TOOL-001 / SEC-TOOL-002)."""
        allowed_tools = self.ROLE_PERMISSIONS.get(role, self.ROLE_PERMISSIONS["read_only"])
        if "*" not in allowed_tools and tool_name not in allowed_tools:
            return PolicyVerdict(
                allowed=False,
                risk_level="high",
                rule_triggered="SEC-TOOL-RBAC",
                reason=f"Role '{role}' is not authorized to execute tool '{tool_name}'.",
            )

        # Check workspace boundary for file modification arguments
        for arg_key in ["TargetFile", "TargetDirectory", "file_path", "target_path", "path"]:
            if arg_key in arguments:
                path_val = str(arguments[arg_key])
                if not self.validate_workspace_boundary(path_val):
                    return PolicyVerdict(
                        allowed=False,
                        risk_level="critical",
                        rule_triggered="SEC-TOOL-001",
                        reason=f"Path '{path_val}' escapes workspace boundary '{self.workspace_root}' (SEC-TOOL-001).",
                    )

        if tool_name in ("run_command", "bash", "execute_command"):
            cmd = str(arguments.get("CommandLine", arguments.get("cmd", "")))
            if re.search(r"\b(DROP\s+DATABASE|DROP\s+SCHEMA)\b", cmd, re.I):
                return PolicyVerdict(
                    allowed=False,
                    risk_level="critical",
                    rule_triggered="SEC-TOOL-002",
                    reason="Destructive database drop schema blocked (SEC-TOOL-002)",
                )

        return self.inspect_invocation("default_server", tool_name, arguments)

    def _inspect_string(self, text: str) -> Optional[Tuple[str, str, str]]:
        """Inspect a single text string against all security rule patterns."""
        for pattern, desc in self.DIRECT_INJECTION:
            if pattern.search(text):
                return "SEC-INJ-001", desc, "critical"

        for pattern, desc in self.INDIRECT_INJECTION:
            if pattern.search(text):
                return "SEC-INJ-002", desc, "high"

        for pattern, desc in self.SECRET_LEAKAGE:
            if pattern.search(text):
                return "SEC-LEAK-001", desc, "high"

        for pattern, desc in self.DESTRUCTIVE_OPERATIONS:
            if pattern.search(text):
                return "SEC-TOOL-002", desc, "critical"

        for pattern, desc in self.DANGEROUS_COMMANDS:
            if pattern.search(text):
                return "SEC-CMD-001", desc, "critical"

        for pattern, desc in self.PATH_TRAVERSAL:
            if pattern.search(text):
                return "SEC-PATH-001", desc, "critical"

        for pattern, desc in self.SQL_DESTRUCTIVE:
            if pattern.search(text):
                return "SEC-SQL-001", desc, "high"

        return None

    def inspect_invocation(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> PolicyVerdict:
        """Inspect tool call arguments in-flight."""
        args_str = json.dumps(arguments)
        violation = self._inspect_string(args_str)

        if violation:
            rule_id, desc, risk = violation
            return PolicyVerdict(
                allowed=False,
                risk_level=risk,
                rule_triggered=rule_id,
                reason=desc,
            )

        return PolicyVerdict(
            allowed=True,
            risk_level="low",
            reason="Tool invocation verified safe.",
        )


class DynamicMCPManager:
    """Manages dynamic runtime mounting and registration of MCP servers."""

    def __init__(self, config_file: Optional[Path] = None) -> None:
        self.config_file = (config_file or Path(".hath0r/dynamic_mcp.json")).resolve()
        self.policy_engine = MCPSecurityPolicyEngine()

    def _load_registry(self) -> Dict[str, Any]:
        """Load persisted dynamic server records."""
        safe_file = self.config_file.resolve()
        if not safe_file.is_file():
            return {}
        try:
            val = json.loads(safe_file.read_text(encoding="utf-8"))
            return val if isinstance(val, dict) else {}
        except Exception:
            return {}

    def _save_registry(self, data: Dict[str, Any]) -> None:
        """Persist dynamic server records."""
        safe_file = self.config_file.resolve()
        safe_file.parent.mkdir(parents=True, exist_ok=True)
        safe_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def connect_server(
        self,
        name: str,
        command: str,
        env: Optional[Dict[str, str]] = None,
        transport: str = "stdio",
    ) -> Dict[str, Any]:
        """Dynamically register a new MCP server connection."""
        reg = self._load_registry()
        reg[name] = {
            "name": name,
            "command": command,
            "env": env or {},
            "transport": transport,
            "connected_at": time.time(),
            "status": "mounted",
        }
        self._save_registry(reg)
        return {"success": True, "server": reg[name]}

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all mounted dynamic MCP servers."""
        reg = self._load_registry()
        return list(reg.values())

    def remove_server(self, name: str) -> Dict[str, Any]:
        """Unmount and deregister an MCP server."""
        reg = self._load_registry()
        if name in reg:
            removed = reg.pop(name)
            self._save_registry(reg)
            return {"success": True, "removed": removed}
        return {"success": False, "error": f"Server not found: {name}"}
