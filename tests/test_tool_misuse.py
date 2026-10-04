"""Unit tests for Tool Misuse Hardening (SEC-TOOL-001 & SEC-TOOL-002)."""

from __future__ import annotations

from pathlib import Path

from hath0r_cli.mcp_security import MCPSecurityPolicyEngine


def test_sec_tool_001_workspace_boundary_guard(tmp_path):
    engine = MCPSecurityPolicyEngine(workspace_root=tmp_path)

    # Valid inside workspace path
    valid_file = str(tmp_path / "src" / "main.py")
    assert engine.validate_workspace_boundary(valid_file) is True

    # Escaping workspace path
    outside_file = str(tmp_path.parent.parent / "etc" / "passwd")
    assert engine.validate_workspace_boundary(outside_file) is False

    # Tool invocation evaluation with escaping path
    verdict = engine.evaluate_tool_permissions(
        role="workspace_write",
        tool_name="write_to_file",
        arguments={"TargetFile": outside_file, "CodeContent": "malicious"},
    )
    assert verdict.allowed is False
    assert verdict.rule_triggered == "SEC-TOOL-001"
    assert verdict.risk_level == "critical"


def test_sec_tool_002_destructive_operation_guard(tmp_path):
    engine = MCPSecurityPolicyEngine(workspace_root=tmp_path)

    destructive_commands = [
        "git push origin master --force",
        "git push -f origin development",
        "git branch -D production",
        "DROP DATABASE production_db",
    ]

    for cmd in destructive_commands:
        verdict = engine.evaluate_tool_permissions(
            role="workspace_write",
            tool_name="run_command",
            arguments={"CommandLine": cmd},
        )
        assert verdict.allowed is False
        assert verdict.rule_triggered == "SEC-TOOL-002"
        assert verdict.risk_level in ["critical", "high"]


def test_tool_rbac_profiles(tmp_path):
    engine = MCPSecurityPolicyEngine(workspace_root=tmp_path)

    # Read-only role trying write_to_file tool
    verdict = engine.evaluate_tool_permissions(
        role="read_only",
        tool_name="write_to_file",
        arguments={"TargetFile": str(tmp_path / "test.py")},
    )
    assert verdict.allowed is False
    assert verdict.rule_triggered == "SEC-TOOL-RBAC"

    # Workspace write role executing allowed write_to_file tool inside workspace
    verdict_allowed = engine.evaluate_tool_permissions(
        role="workspace_write",
        tool_name="write_to_file",
        arguments={"TargetFile": str(tmp_path / "test.py"), "CodeContent": "print('hello')"},
    )
    assert verdict_allowed.allowed is True
