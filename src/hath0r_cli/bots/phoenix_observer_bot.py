"""
HATH0R CLI Phoenix Evaluation & Telemetry Observer Bot.

Monitors distributed telemetry endpoints, audits agent tracing connectivity,
and aggregates evaluation metrics across suite products.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from ..telemetry import load_otel_config


@dataclass
class PhoenixObserverBot:
    """Audits Phoenix collector health and retrieves aggregate evaluation metrics."""

    custom_endpoint: Optional[str] = None

    def check_health(self) -> Dict[str, Any]:
        """Check availability of Arize Phoenix collector and UI endpoints."""
        cfg = load_otel_config()
        endpoint = self.custom_endpoint or cfg.otlp_endpoint or "http://localhost:6006"
        health_url = endpoint.replace(":4318", ":6006").rstrip("/")
        if not health_url.startswith("http"):
            health_url = f"http://{health_url}"

        status: Dict[str, Any] = {
            "service": cfg.service_name,
            "environment": cfg.deployment_environment,
            "target_url": health_url,
            "healthy": False,
            "http_status": None,
            "error": None,
        }

        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "hath0r-cli/observer-bot"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                status["http_status"] = resp.status
                status["healthy"] = (resp.status == 200)
        except Exception as exc:
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
