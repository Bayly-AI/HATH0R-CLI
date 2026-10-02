"""Unit tests and benchmarks for Hath0r CLI lazy command and telemetry loading."""

import click
from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.lazy_group import COMMAND_REGISTRY, Hath0rLazyGroup
from hath0r_cli.telemetry import (
    OTelConfig,
    get_current_trace_context,
    get_tracer,
    init_tracer,
    trace_span,
)


def test_command_registry_contains_expected_commands():
    """Verify all canonical CLI command groups are registered in COMMAND_REGISTRY."""
    expected = [
        "doctor",
        "init",
        "kb",
        "planes",
        "schema",
        "mcp",
        "factory",
        "branch",
        "pr",
        "janitor",
        "task",
        "jev",
        "docker",
        "quality",
        "preflight",
        "deploy",
        "release",
        "docs",
        "issue",
        "repo",
        "clean-repos",
        "clean-repo",
        "voice",
        "speak",
        "playbook",
        "context",
        "memory",
        "contracts",
        "local",
        "wasm",
        "tui",
        "serve",
        "validate-change",
        "vision",
    ]
    for cmd in expected:
        assert cmd in COMMAND_REGISTRY, f"Missing {cmd} in COMMAND_REGISTRY"


def test_lazy_group_resolution():
    """Verify Hath0rLazyGroup dynamically resolves commands without errors."""
    group = Hath0rLazyGroup()
    ctx = click.Context(group)

    cmd_list = group.list_commands(ctx)
    assert len(cmd_list) >= len(COMMAND_REGISTRY)
    assert "doctor" in cmd_list
    assert "vision" in cmd_list
    assert "branch" in cmd_list

    # Resolve individual command
    doctor_cmd = group.get_command(ctx, "doctor")
    assert doctor_cmd is not None
    assert isinstance(doctor_cmd, click.Command)

    vision_cmd = group.get_command(ctx, "vision")
    assert vision_cmd is not None
    assert isinstance(vision_cmd, click.Command)


def test_cli_version_execution():
    """Verify hath0r --version execution through lazy group."""
    runner = CliRunner()
    res = runner.invoke(cli, ["--version"])
    assert res.exit_code == 0
    assert "hath0r" in res.output
    assert "version" in res.output


def test_telemetry_lazy_tracer():
    """Verify deferred tracer initialization and trace span context manager."""
    cfg = OTelConfig(enabled=True)
    assert init_tracer(cfg) is True

    tracer = get_tracer("test_tracer")
    assert tracer is not None

    with trace_span("test_span", attributes={"test.key": "val"}):
        ctx = get_current_trace_context()
        assert isinstance(ctx, dict)
