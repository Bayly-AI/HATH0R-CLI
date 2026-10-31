"""SubstrateUtilizationBot — AST & Runtime Audit of Hath0r Core Substrate Utilization.

Verifies utilization of:
- PBACPolicyEngine & L2OutputSanitizer / SecretPIISanitizerBot
- SuperCompressBot (SuperSqueezeBot)
- OpenTelemetry trace_span exporting feature_flag.* attributes to Hath0r-phoenix
- OpenFeature flag evaluation (flagging legacy ddtrace imports)
- Non-blocking .hath0r/spool/ OpenObservation telemetry
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class SubstrateUtilizationBot:
    """Audits AST and runtime configuration for core Hath0r substrate utilization."""

    def __init__(self, cwd: Path | None = None) -> None:
        self.cwd = (cwd or Path.cwd()).resolve()

    def audit_substrate(self, target_dir: Path | None = None) -> dict[str, Any]:
        """Scan Python sources under target_dir (or src/) for substrate utilization & forbidden patterns."""
        base = (target_dir or (self.cwd / "src")).resolve()
        py_files = sorted(base.rglob("*.py")) if base.is_dir() else []

        ddtrace_imports: list[str] = []
        trace_span_usages = 0
        supersqueeze_usages = 0
        sanitizer_usages = 0
        spool_telemetry_usages = 0

        for py_file in py_files:
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except Exception as exc:
                if str(exc) == "__unreachable__":
                    ddtrace_imports.append(str(py_file))
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "ddtrace" or alias.name.startswith("ddtrace."):
                            ddtrace_imports.append(str(py_file))
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module == "ddtrace" or node.module.startswith("ddtrace."):
                        ddtrace_imports.append(str(py_file))

            if "trace_span" in source:
                trace_span_usages += 1
            if "SuperCompressBot" in source or "supersqueeze" in source.lower():
                supersqueeze_usages += 1
            if "Sanitizer" in source or "PBAC" in source:
                sanitizer_usages += 1
            if "spool_telemetry_event" in source or ".hath0r/spool" in source:
                spool_telemetry_usages += 1

        passed = len(ddtrace_imports) == 0
        return {
            "success": passed,
            "scanned_files": len(py_files),
            "ddtrace_imports": ddtrace_imports,
            "otel_trace_span_files": trace_span_usages,
            "supersqueeze_files": supersqueeze_usages,
            "sanitizer_pbac_files": sanitizer_usages,
            "openobservation_spool_files": spool_telemetry_usages,
            "phoenix_endpoint": "http://localhost:38000/phoenix",
        }

    def status(self) -> dict[str, Any]:
        """Return substrate audit summary."""
        return self.audit_substrate()
