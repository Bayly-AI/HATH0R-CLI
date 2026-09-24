"""Structured CLI response envelope models (hath0r.cli.response/1)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

RESPONSE_SCHEMA = "hath0r.cli.response/1"
VALID_STATES = frozenset({"ok", "degraded", "unavailable", "error"})
VALID_SEVERITIES = frozenset({"error", "warning", "info"})


@dataclass
class ResponseMeta:
    """Producer metadata for a CLI response."""

    cli_version: str
    duration_ms: int
    dry_run: bool | None = None


@dataclass
class Diagnostic:
    """Structured diagnostic entry (hath0r.cli.diagnostic/1)."""

    code: str
    message: str
    severity: str
    remediation: str | None = None
    provenance: dict[str, Any] | None = None
    ttl: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize, omitting optional keys that are None."""
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.remediation is not None:
            payload["remediation"] = self.remediation
        if self.provenance is not None:
            payload["provenance"] = self.provenance
        if self.ttl is not None:
            payload["ttl"] = self.ttl
        if self.details is not None:
            payload["details"] = self.details
        return payload


@dataclass
class CliResponse:
    """Top-level structured JSON response envelope."""

    schema: str = RESPONSE_SCHEMA
    command: str = ""
    generated_at: str = ""
    state: str = "ok"
    data: dict[str, Any] | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    meta: ResponseMeta | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON encoding."""
        meta_dict = None
        if self.meta is not None:
            meta_dict = {k: v for k, v in asdict(self.meta).items() if v is not None}
        return {
            "schema": self.schema,
            "command": self.command,
            "generated_at": self.generated_at,
            "state": self.state,
            "data": self.data,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "meta": meta_dict,
        }
