"""Deterministic L2 Pre-Persist Secret & PII Sanitizer Bot (CR-AGENTIC-SEC-001 / WS2).

Prevents credential, API key, JWT, private key, and PII leakage across:
- `.hath0r/memory/sessions/*.json` and `.hath0r/memory/graph.json` (`MemoryManagerBot`)
- `.hath0r/finops/token_telemetry.jsonl` (`TokenTelemetryCLIBot`)
- `.hath0r/state/hahp/*.json` (`HAHPProtocolManager`)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SECRET_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,255}\b")),
    ("GITHUB_PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,255}\b")),
    ("ANTHROPIC_KEY", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{16,255}\b")),
    ("OPENAI_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{20,255}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,255}\b")),
    ("JWT_TOKEN", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    (
        "PRIVATE_KEY",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
        ),
    ),
]

PII_REGEXES: list[tuple[str, re.Pattern[str]]] = [
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
]


@dataclass
class SanitizationResult:
    """Summary of L2 pre-persist sanitization."""

    sanitized_text: str
    secrets_redacted: int = 0
    pii_redacted: int = 0
    redaction_types: list[str] = field(default_factory=list)


class SecretPIISanitizerBot:
    """Deterministic L2 sanitizer for memory, HAHP handoffs, and telemetry ledgers."""

    def __init__(self, redact_pii: bool = True) -> None:
        self.redact_pii = redact_pii

    def redact_text(self, text: str, redact_pii: bool | None = None) -> SanitizationResult:
        if not text:
            return SanitizationResult(sanitized_text=text)
        use_pii = self.redact_pii if redact_pii is None else redact_pii
        out = text
        sec_cnt = 0
        pii_cnt = 0
        r_types: list[str] = []

        for label, pat in SECRET_REGEXES:
            matches = list(pat.finditer(out))
            if matches:
                sec_cnt += len(matches)
                r_types.append(label)
                out = pat.sub(f"[REDACTED:{label}]", out)

        if use_pii:
            for label, pat in PII_REGEXES:
                matches = list(pat.finditer(out))
                if matches:
                    pii_cnt += len(matches)
                    r_types.append(label)
                    out = pat.sub(f"[PII_REDACTED:{label}]", out)

        return SanitizationResult(
            sanitized_text=out,
            secrets_redacted=sec_cnt,
            pii_redacted=pii_cnt,
            redaction_types=sorted(set(r_types)),
        )

    def redact_payload(self, obj: Any, redact_pii: bool | None = None) -> Any:
        """Recursively sanitize strings inside dicts and lists before JSON persistence."""
        if isinstance(obj, str):
            return self.redact_text(obj, redact_pii=redact_pii).sanitized_text
        if isinstance(obj, dict):
            return {k: self.redact_payload(v, redact_pii=redact_pii) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.redact_payload(item, redact_pii=redact_pii) for item in obj]
        return obj


secret_pii_sanitizer = SecretPIISanitizerBot()
