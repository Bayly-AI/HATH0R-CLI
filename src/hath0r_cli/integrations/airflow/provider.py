"""Airflow provider discovery metadata for HATH0R."""

from __future__ import annotations

from typing import Any, Dict


def get_provider_info() -> Dict[str, Any]:
    """Return provider metadata dictionary for Apache Airflow plugin discovery."""
    return {
        "package-name": "apache-airflow-providers-hath0r",
        "name": "HATH0R",
        "description": "Apache Airflow Provider for HATH0R Operator CLI and Cognitive Substrate.",
        "hook-class-names": ["hath0r_cli.integrations.airflow.hook.Hath0rHook"],
        "connection-types": [
            {
                "connection-type": "hath0r",
                "hook-class-name": "hath0r_cli.integrations.airflow.hook.Hath0rHook",
            }
        ],
        "versions": ["0.3.0"],
    }
