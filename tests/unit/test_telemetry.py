"""Unit tests for OpenTelemetry tracer provider, spans, and telemetry correlation."""

from __future__ import annotations

from pathlib import Path

from hath0r_cli.step_runner import BotRegistry, execute_workflow, spool_telemetry_event
from hath0r_cli.telemetry import (
    OTelConfig,
    get_current_trace_context,
    get_tracer,
    init_tracer,
    load_otel_config,
    trace_span,
)


def test_otel_config_load() -> None:
    cfg = load_otel_config()
    assert isinstance(cfg, OTelConfig)
    assert cfg.service_name in ("hath0r-cli", "control-tower-cli")
    assert cfg.service_namespace == "hath0r-opensource"


def test_init_tracer_and_get_tracer() -> None:
    ok = init_tracer()
    assert ok is True
    tracer = get_tracer("test_tracer")
    assert tracer is not None


def test_trace_span_context_manager() -> None:
    with trace_span("test_root_span", attributes={"test.attr": "value"}):
        ctx = get_current_trace_context()
        assert "trace_id" in ctx
        assert "span_id" in ctx
        assert len(ctx["trace_id"]) == 32
        assert len(ctx["span_id"]) == 16


def test_step_runner_traces_workflow_and_steps(tmp_path: Path) -> None:
    registry = BotRegistry(cwd=tmp_path)
    workflow_def = {
        "id": "test-telemetry-workflow",
        "name": "Test Telemetry Workflow",
        "steps": [
            {
                "bot": "branch-guard-bot",
                "action": "check-current-branch",
                "args": {"target_branch": "development"},
                "on_failure": "continue",
            }
        ],
    }

    result = execute_workflow(workflow_def, registry, dry_run=True)
    assert result.workflow_id == "test-telemetry-workflow"
    assert len(result.steps) == 1
    assert result.steps[0].bot_id == "branch-guard-bot"


def test_spool_telemetry_event_injects_trace_context(tmp_path: Path) -> None:
    with trace_span("test_spool_span"):
        ctx = get_current_trace_context()
        spool_path = spool_telemetry_event("test_event", {"status": "ok"}, base_dir=tmp_path)
        assert spool_path is not None
        assert spool_path.is_file()

        content = spool_path.read_text(encoding="utf-8")
        assert ctx["trace_id"] in content
        assert ctx["span_id"] in content
