"""Tests for Infrastructure as Code (IaC), Container Salting, and EKS Fargate subsystem."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from hath0r_cli.bots.iac_bot import IaCManagingBot
from hath0r_cli.commands.iac import iac
from hath0r_cli.iac.container_scaffolder import ContainerScaffolder
from hath0r_cli.iac.fargate_generator import FargateGenerator
from hath0r_cli.iac.salting_coordinator import SaltingCoordinator


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "test-service"
    ws.mkdir()
    (ws / "pyproject.toml").write_text("[project]\nname = 'test-service'\nversion = '0.1.0'\n")
    return ws


def test_container_scaffolder_python(temp_workspace: Path) -> None:
    scaffolder = ContainerScaffolder()
    res = scaffolder.scaffold(temp_workspace, tech_stack="python")

    assert res["tech_stack"] == "python"
    assert "Dockerfile" in res["files_written"]
    assert ".dockerignore" in res["files_written"]

    df_content = (temp_workspace / "Dockerfile").read_text()
    assert "FROM python:3.11-slim AS builder" in df_content
    assert "FROM python:3.11-slim AS runner" in df_content
    assert "USER 10001:10001" in df_content
    assert "HEALTHCHECK" in df_content

    audit = scaffolder.audit_dockerfile(temp_workspace)
    assert audit["compliant"] is True
    assert audit["multi_stage"] is True
    assert audit["non_root"] is True
    assert audit["has_healthcheck"] is True


def test_container_scaffolder_node(tmp_path: Path) -> None:
    ws = tmp_path / "node-service"
    ws.mkdir()
    scaffolder = ContainerScaffolder()
    res = scaffolder.scaffold(ws, tech_stack="node")

    assert res["tech_stack"] == "node"
    df_content = (ws / "Dockerfile").read_text()
    assert "FROM node:20-alpine AS builder" in df_content
    assert "USER 10001:10001" in df_content


def test_salting_coordinator(temp_workspace: Path) -> None:
    salter = SaltingCoordinator(temp_workspace)
    receipt = salter.salt_container(image_name="test-service", workspace=temp_workspace)

    assert receipt["schema_version"] == "hath0r.iac.salting/1"
    assert receipt["pinned_digest"].startswith("sha256:")
    assert "@sha256:" in receipt["pinned_ref"]
    assert receipt["attestation"]["signature_provider"] == "cosign"

    receipt_file = temp_workspace / ".hath0r" / "iac" / "salting-receipt.json"
    assert receipt_file.exists()

    audit = salter.audit_salting(temp_workspace)
    assert audit["is_salted"] is True
    assert audit["compliant"] is True


def test_fargate_generator_scaffold_and_validate(temp_workspace: Path) -> None:
    gen = FargateGenerator()
    res = gen.scaffold(temp_workspace, app_name="test-service")

    assert "fargate-profile.yaml" in res["files_written"]
    assert "k8s/deployment.yaml" in res["files_written"]
    assert "k8s/ingress.yaml" in res["files_written"]

    audit = gen.audit_fargate(temp_workspace)
    assert audit["compliant"] is True
    assert audit["has_profile"] is True
    assert audit["has_k8s"] is True
    assert audit["target_type_ip"] is True
    assert audit["privileged_detected"] is False

    # Test detection of forbidden privileged mode
    (temp_workspace / "k8s" / "bad.yaml").write_text("securityContext:\n  privileged: true\n")
    audit_bad = gen.audit_fargate(temp_workspace)
    assert audit_bad["compliant"] is False
    assert audit_bad["privileged_detected"] is True


def test_fargate_generator_render(temp_workspace: Path) -> None:
    gen = FargateGenerator()
    gen.scaffold(temp_workspace, app_name="test-service")

    render_res = gen.render(temp_workspace, environment="staging")
    assert render_res["environment"] == "staging"
    assert render_res["count"] > 0
    assert (temp_workspace / "build" / "iac" / "staging" / "deployment.yaml").exists()


def test_iac_managing_bot_lifecycle(temp_workspace: Path) -> None:
    bot = IaCManagingBot(workspace=temp_workspace)

    # Pre-init audit should show non-compliant
    audit_pre = bot.audit_workspace(temp_workspace)
    assert audit_pre["compliant"] is False

    # Init
    init_res = bot.init_iac(temp_workspace, app_name="test-service")
    assert init_res["success"] is True

    # Validate
    val_res = bot.validate_iac(temp_workspace)
    assert val_res["valid"] is True
    assert val_res["score"] >= 0.90


def test_cli_iac_commands(temp_workspace: Path) -> None:
    runner = CliRunner()

    # 1. hath0r iac init
    res_init = runner.invoke(iac, ["init", str(temp_workspace), "--app-name", "test-app"])
    assert res_init.exit_code == 0
    data_init = json.loads(res_init.output)
    assert data_init["state"] == "ok"
    assert data_init["data"]["success"] is True

    # 2. hath0r iac validate
    res_val = runner.invoke(iac, ["validate", str(temp_workspace)])
    assert res_val.exit_code == 0
    data_val = json.loads(res_val.output)
    assert data_val["state"] == "ok"
    assert data_val["data"]["valid"] is True

    # 3. hath0r iac salt
    res_salt = runner.invoke(iac, ["salt", "test-app", "--workspace", str(temp_workspace)])
    assert res_salt.exit_code == 0
    data_salt = json.loads(res_salt.output)
    assert data_salt["state"] == "ok"
    assert "pinned_digest" in data_salt["data"]

    # 4. hath0r iac render
    res_render = runner.invoke(iac, ["render", str(temp_workspace), "--env", "staging"])
    assert res_render.exit_code == 0
    data_render = json.loads(res_render.output)
    assert data_render["state"] == "ok"
    assert data_render["data"]["environment"] == "staging"

    # 5. hath0r iac audit
    res_audit = runner.invoke(iac, ["audit", str(temp_workspace)])
    assert res_audit.exit_code == 0
    data_audit = json.loads(res_audit.output)
    assert data_audit["state"] == "ok"
    assert data_audit["data"]["compliant"] is True


def test_iac_mcp_tools() -> None:
    from hath0r_cli.server.mcp_server import create_mcp_server

    server = create_mcp_server()
    tools = set(server._tool_manager._tools.keys())
    expected_iac_tools = {
        "hath0r_iac_audit",
        "hath0r_iac_init",
        "hath0r_iac_validate",
        "hath0r_iac_salt",
        "hath0r_iac_render",
    }
    assert expected_iac_tools.issubset(tools)


