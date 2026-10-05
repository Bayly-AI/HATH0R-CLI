"""
HATH0R CLI Phoenix Evaluation & Telemetry Observer Bot.

Monitors distributed telemetry endpoints, audits agent tracing connectivity,
and aggregates evaluation metrics across suite products.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..telemetry import load_otel_config


@dataclass
class PhoenixObserverBot:
    """Audits Phoenix collector health and retrieves aggregate evaluation metrics."""

    custom_endpoint: Optional[str] = None

    def check_health(self) -> Dict[str, Any]:
        """Check availability of Arize Phoenix collector and UI endpoints."""
        cfg = load_otel_config()
        candidates = []
        if self.custom_endpoint:
            candidates.append(self.custom_endpoint)
        if cfg.otlp_endpoint:
            candidates.append(cfg.otlp_endpoint)

        # Canonical Edge & direct candidates
        candidates.extend(
            [
                "http://localhost:58000/phoenix/",
                "http://localhost/phoenix/",
                "http://localhost:6006/",
            ]
        )

        status: Dict[str, Any] = {
            "service": cfg.service_name,
            "environment": cfg.deployment_environment,
            "target_url": candidates[0] if candidates else "http://localhost:58000/phoenix/",
            "healthy": False,
            "http_status": None,
            "error": None,
        }

        for candidate in candidates:
            url = candidate
            if not url.startswith("http"):
                url = f"http://{url}"
            # Ensure trailing slash for root / UI routes
            if not url.endswith("/") and not any(url.endswith(ext) for ext in [".ico", ".json", "/traces", "/metrics"]):
                url = f"{url}/"

            try:
                req = urllib.request.Request(url, headers={"User-Agent": "hath0r-cli/observer-bot"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    if resp.status == 200:
                        status["target_url"] = url
                        status["http_status"] = resp.status
                        status["healthy"] = True
                        status["error"] = None
                        return status
            except Exception as exc:
                if status["error"] is None:
                    status["error"] = str(exc)

        return status

    def get_evaluation_manifest(self) -> Dict[str, Any]:
        """Return the canonical suite evaluation targets and thresholds."""
        return {
            "suite": "1-nation",
            "evaluators": [
                {
                    "name": "StatutoryFaithfulness",
                    "kind": "LLM-as-a-judge",
                    "target_product": "1n-mcp",
                    "min_threshold": 0.45,
                },
                {
                    "name": "NeutralityTone",
                    "kind": "Objective Tone Classifier",
                    "target_product": "1n-mcp",
                    "min_threshold": 0.70,
                },
                {
                    "name": "CitizenReadability",
                    "kind": "Flesch-Kincaid",
                    "target_product": "1n-mcp",
                    "min_threshold": 0.80,
                },
                {
                    "name": "JailbreakSecurity",
                    "kind": "Safety Classifier",
                    "target_product": "agentguard",
                    "min_threshold": 1.00,
                },
            ],
        }


phoenix_observer_bot = PhoenixObserverBot()
