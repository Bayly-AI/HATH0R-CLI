"""Unit tests for Data Leakage Prevention & Secret Sanitization (SEC-LEAK-001)."""

from __future__ import annotations

from hath0r_cli.mcp_security import MCPSecurityPolicyEngine, SecretSanitizer


def test_sec_leak_001_sanitizer():
    raw_texts = [
        "User API key is sk-proj-1234567890abcdef1234567890abcdef in config",
        "GitHub token ghp_123456789012345678901234567890123456 exposed",
        "AWS credentials AKIAIOSFODNN7EXAMPLE found in environment",
        "Authorization header Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "DB connection string postgres://admin:secretpass123@localhost:5432/mydb",
    ]

    for text in raw_texts:
        sanitized = SecretSanitizer.sanitize(text)
        assert "[REDACTED_SECRET]" in sanitized
        assert "sk-proj-" not in sanitized
        assert "ghp_12345" not in sanitized
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "secretpass123" not in sanitized


def test_sec_leak_001_policy_engine_inspection():
    engine = MCPSecurityPolicyEngine()
    verdict = engine.inspect_invocation("test_server", "set_config", {"api_key": "sk-1234567890abcdef1234567890abcdef"})

    assert verdict.allowed is False
    assert verdict.rule_triggered == "SEC-LEAK-001"
    assert verdict.risk_level == "high"
