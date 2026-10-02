"""Dynamic MCP Server Mounting and In-Flight Security Policy Engine for Hath0r CLI."""

from __future__ import annotations

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


class MCPSecurityPolicyEngine:
    """Evaluates agent tool arguments in-flight to prevent prompt injection and destructive actions."""

    DANGEROUS_COMMANDS = [
        (re.compile(r"rm\s+(-[rfRF]+\s+|--recursive\s+|--force\s+)*(/|/\*|~|\$HOME)", re.I), "CRITICAL: Destructive root/home filesystem deletion"),
        (re.compile(r"(curl|wget)\s+.*\|\s*(bash|sh|zsh)", re.I), "CRITICAL: Unverified remote script execution via pipe"),
        (re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.I), "CRITICAL: Fork bomb denial of service"),
        (re.compile(r"mkfs(\.\w+)?\s+", re.I), "CRITICAL: Filesystem format attempt"),
        (re.compile(r"chmod\s+(-R\s+)?777\s+/", re.I), "HIGH: Global permission escalation"),
    ]

    PATH_TRAVERSAL = [
        (re.compile(r"(\.\./){2,}", re.I), "HIGH: Directory traversal escape"),
        (re.compile(r"/(etc/(passwd|shadow)|root/\.ssh|\.aws/credentials|\.credentials)", re.I), "CRITICAL: Sensitive credential / system file access"),
    ]

    SQL_DESTRUCTIVE = [
        (re.compile(r"\bDROP\s+(DATABASE|SCHEMA|TABLE)\b", re.I), "HIGH: Destructive SQL drop operation"),
        (re.compile(r"\bTRUNCATE\s+TABLE\b", re.I), "HIGH: Destructive SQL truncate operation"),
    ]

    def list_rules(self) -> List[Dict[str, Any]]:
        """List active security guardrail rules."""
        return [
            {"id": "SEC-CMD-001", "name": "Dangerous Shell Commands", "risk": "CRITICAL", "description": "Blocks rm -rf /, pipe-to-shell, and fork bombs."},
            {"id": "SEC-PATH-001", "name": "Path Traversal & Secrets Access", "risk": "CRITICAL", "description": "Blocks ../.. traversal and access to system credentials."},
            {"id": "SEC-SQL-001", "name": "Destructive SQL Statements", "risk": "HIGH", "description": "Blocks accidental DROP TABLE/DATABASE queries."},
        ]

    def _inspect_string(self, text: str) -> Optional[Tuple[str, str, str]]:
        """Inspect a single text string against all security rule patterns."""
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
        self.config_file = config_file or Path(".hath0r/dynamic_mcp.json")
        self.policy_engine = MCPSecurityPolicyEngine()

    def _load_registry(self) -> Dict[str, Any]:
        """Load persisted dynamic server records."""
        if not self.config_file.is_file():
            return {}
        try:
            val = json.loads(self.config_file.read_text(encoding="utf-8"))
            return val if isinstance(val, dict) else {}
        except Exception:
            return {}

    def _save_registry(self, data: Dict[str, Any]) -> None:
        """Persist dynamic server records."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

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
