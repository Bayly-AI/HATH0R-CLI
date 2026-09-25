"""OpenTelemetry integration and distributed tracing support for HATH0R CLI."""

from __future__ import annotations

import json
import os
import random
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.trace import Status, StatusCode

    HAVE_OTEL = True
except ImportError:
    HAVE_OTEL = False
    trace = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment, misc]
    TracerProvider = None  # type: ignore[assignment, misc]
    SimpleSpanProcessor = None  # type: ignore[assignment, misc]
    Status = None  # type: ignore[assignment, misc]
    StatusCode = None  # type: ignore[assignment, misc]


@dataclass
class OTelConfig:
    """Parsed OpenTelemetry configuration."""

    service_name: str = "hath0r-cli"
    service_namespace: str = "hath0r-opensource"
    deployment_environment: str = "local"
    enabled: bool = True
    otlp_endpoint: str | None = None
    sampler_ratio: float = 1.0


_CONFIG_LOADED: OTelConfig | None = None
_TRACER_INITIALIZED: bool = False

# Fallback in-process trace context stack for environments where opentelemetry-sdk is absent
_FALLBACK_CONTEXT_STACK: list[dict[str, str]] = []


def _generate_trace_id() -> str:
    return format(random.getrandbits(128), "032x")


def _generate_span_id() -> str:
    return format(random.getrandbits(64), "016x")


def load_otel_config(config_path: Path | None = None) -> OTelConfig:
    """Load OTel configuration from cfg/observability/otel.json or environment."""
    global _CONFIG_LOADED
    if _CONFIG_LOADED is not None:
        return _CONFIG_LOADED

    cfg = OTelConfig()

    # Check environment toggle
    if os.environ.get("HATH0R_OTEL_ENABLED", "").lower() in ("false", "0", "no") or os.environ.get(
        "OTEL_SDK_DISABLED", ""
    ).lower() in ("true", "1", "yes"):
        cfg.enabled = False
        _CONFIG_LOADED = cfg
        return cfg

    # Attempt to load file
    target_file = config_path
    if not target_file:
        base_dir = Path.cwd()
        target_file = base_dir / "cfg" / "observability" / "otel.json"
        if not target_file.exists():
            group_root = os.environ.get("HATH0R_GROUP_ROOT")
            if group_root:
                target_file = Path(group_root) / "cfg" / "observability" / "otel.json"

    if target_file and target_file.is_file():
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            res = data.get("resource", {})
            cfg.service_name = res.get("service_name", cfg.service_name)
            cfg.service_namespace = res.get("service_namespace", cfg.service_namespace)
            cfg.deployment_environment = res.get("deployment_environment", cfg.deployment_environment)

            exporters = data.get("exporters", {}).get("otlp", {})
            endpoint_env = exporters.get("endpoint_env", "OTEL_EXPORTER_OTLP_ENDPOINT")
            cfg.otlp_endpoint = os.environ.get(endpoint_env) or exporters.get("default_endpoint")

            traces_cfg = data.get("traces", {})
            cfg.enabled = traces_cfg.get("enabled", True)
            try:
                cfg.sampler_ratio = float(traces_cfg.get("sampler_arg", "1.0"))
            except ValueError:
                cfg.sampler_ratio = 1.0
        except Exception:
            pass

    # Environment overrides
    cfg.service_name = os.environ.get("OTEL_SERVICE_NAME", cfg.service_name)
    cfg.deployment_environment = os.environ.get("ENVIRONMENT", cfg.deployment_environment)
    if "OTEL_EXPORTER_OTLP_ENDPOINT" in os.environ:
        cfg.otlp_endpoint = os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]

    _CONFIG_LOADED = cfg
    return cfg


def init_tracer(config: OTelConfig | None = None) -> bool:
    """Initialize OpenTelemetry tracer provider (or fallback provider)."""
    global _TRACER_INITIALIZED
    if _TRACER_INITIALIZED:
        return True

    cfg = config or load_otel_config()
    if not cfg.enabled:
        return False

    if not HAVE_OTEL or Resource is None or TracerProvider is None or trace is None:
        # Fallback trace context engine initialized
        _TRACER_INITIALIZED = True
        return True

    try:
        resource = Resource.create(
            {
                "service.name": cfg.service_name,
                "service.namespace": cfg.service_namespace,
                "deployment.environment": cfg.deployment_environment,
            }
        )
        provider = TracerProvider(resource=resource)

        # In-memory / fallback exporter if otlp package is available
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            if cfg.otlp_endpoint and SimpleSpanProcessor is not None:
                exporter = OTLPSpanExporter(endpoint=f"{cfg.otlp_endpoint.rstrip('/')}/v1/traces")
                provider.add_span_processor(SimpleSpanProcessor(exporter))
        except ImportError:
            pass

        trace.set_tracer_provider(provider)
        _TRACER_INITIALIZED = True
        return True
    except Exception:
        _TRACER_INITIALIZED = True
        return True


def get_tracer(name: str = "hath0r_cli") -> Any:
    """Get active tracer instance."""
    if not _TRACER_INITIALIZED:
        init_tracer()

    if HAVE_OTEL and trace is not None:
        return trace.get_tracer(name)
    return "hath0r-fallback-tracer"


def get_current_trace_context() -> dict[str, str]:
    """Return active trace_id and span_id if available."""
    if HAVE_OTEL and trace is not None:
        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                return {
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                }

    if _FALLBACK_CONTEXT_STACK:
        return dict(_FALLBACK_CONTEXT_STACK[-1])

    return {}


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    tracer_name: str = "hath0r_cli",
) -> Generator[Any, None, None]:
    """Context manager for tracing a block of execution with error handling and fallback support."""
    tracer = get_tracer(tracer_name)

    if HAVE_OTEL and trace is not None and hasattr(tracer, "start_as_current_span"):
        attrs = {k: v for k, v in (attributes or {}).items() if v is not None}
        with tracer.start_as_current_span(name, attributes=attrs) as span:
            try:
                yield span
                if Status is not None and StatusCode is not None:
                    span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                if Status is not None and StatusCode is not None:
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                raise
    else:
        # Fallback trace context propagation
        parent = _FALLBACK_CONTEXT_STACK[-1] if _FALLBACK_CONTEXT_STACK else None
        trace_id = parent["trace_id"] if parent else _generate_trace_id()
        span_id = _generate_span_id()
        ctx = {"trace_id": trace_id, "span_id": span_id, "name": name}
        _FALLBACK_CONTEXT_STACK.append(ctx)
        try:
            yield ctx
        finally:
            _FALLBACK_CONTEXT_STACK.pop()
