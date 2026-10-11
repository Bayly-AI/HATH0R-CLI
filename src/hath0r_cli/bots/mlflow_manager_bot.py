"""
HATH0R CLI MLflow Lifecycle & Manager Bot.

Provides container orchestration, multi-group deployments (1-Nation, Hath0r, BaylyAI),
experiment tracking, run logging, and REST client integrations for MLflow.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MLflowManagerBot:
    """Manages MLflow lifecycle, multi-group deployments, and experiment tracking."""

    _cached_api_urls: Dict[str, str] = field(default_factory=dict)

    GROUP_COMPOSE_MAP = {
        "hath0r": {
            "compose_file": "cfg/docker/groups/hath0r/docker-compose.yml",
            "project": "hath0r-opensource",
            "service": "mlflow",
            "container": "HATH0R-MLflow",
            "edge_url": "http://localhost:38000/mlflow/",
            "api_url": "http://localhost:38000/mlflow/ajax-api/2.0/mlflow",
            "direct_url": "http://localhost:5000/mlflow/",
        },
        "1-nation": {
            "compose_file": "/Users/raybayly/Development/1-Nation/ATC/deploy/docker/docker-compose.yml",
            "project": "1-nation",
            "service": "1n-mlflow",
            "container": "1NMLFLOW",
            "edge_url": "http://localhost:58000/mlflow/",
            "api_url": "http://localhost:58000/mlflow/ajax-api/2.0/mlflow",
            "direct_url": "http://localhost:5000/mlflow/",
        },
        "bai": {
            "compose_file": "cfg/docker/groups/bai/docker-compose.yml",
            "service": "mlflow",
            "container": "BAI-MLflow",
            "edge_url": "http://localhost:48000/mlflow/",
            "api_url": "http://localhost:48000/mlflow/ajax-api/2.0/mlflow",
            "direct_url": "http://localhost:45000/mlflow/",
        },
    }

    def start_mlflow(self, group: str = "hath0r", detach: bool = True) -> Dict[str, Any]:
        """Start the MLflow container for the target group."""
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["hath0r"])
        compose_file = group_cfg["compose_file"]
        service = group_cfg["service"]

        cmd = ["docker", "compose"]
        if "project" in group_cfg:
            cmd.extend(["-p", group_cfg["project"]])
        cmd.extend(["-f", compose_file, "up"])
        if detach:
            cmd.append("-d")
        cmd.append(service)

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "success": True,
                "group": group,
                "container": group_cfg["container"],
                "edge_url": group_cfg["edge_url"],
                "direct_url": group_cfg["direct_url"],
                "output": res.stdout.strip(),
            }
        except subprocess.CalledProcessError as exc:
            return {
                "success": False,
                "group": group,
                "container": group_cfg["container"],
                "error": exc.stderr.strip() or str(exc),
            }

    def stop_mlflow(self, group: str = "hath0r") -> Dict[str, Any]:
        """Stop the MLflow container for the target group."""
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["hath0r"])
        compose_file = group_cfg["compose_file"]
        service = group_cfg["service"]

        cmd = ["docker", "compose"]
        if "project" in group_cfg:
            cmd.extend(["-p", group_cfg["project"]])
        cmd.extend(["-f", compose_file, "stop", service])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "success": True,
                "group": group,
                "container": group_cfg["container"],
                "output": res.stdout.strip(),
            }
        except subprocess.CalledProcessError as exc:
            return {
                "success": False,
                "group": group,
                "container": group_cfg["container"],
                "error": exc.stderr.strip() or str(exc),
            }

    def check_status(self, group: str = "hath0r", custom_endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Check status of MLflow container and UI / API endpoints."""
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["hath0r"])
        candidates = []
        if custom_endpoint:
            candidates.append(custom_endpoint)
        candidates.extend(
            [
                group_cfg["edge_url"],
                group_cfg["direct_url"],
                "http://localhost:38000/mlflow/",
                "http://localhost:35000/mlflow/",
                "http://localhost:58000/mlflow/",
                "http://localhost:5000/mlflow/",
            ]
        )

        status: Dict[str, Any] = {
            "group": group,
            "container": group_cfg["container"],
            "healthy": False,
            "active_url": None,
            "http_status": None,
            "error": None,
        }

        for url in candidates:
            probe_url = url if url.endswith("/") else f"{url}/"
            try:
                req = urllib.request.Request(probe_url, headers={"User-Agent": "hath0r-cli/mlflow-manager"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        status["healthy"] = True
                        status["active_url"] = probe_url
                        status["http_status"] = resp.status
                        status["error"] = None
                        return status
            except Exception as exc:
                if status["error"] is None:
                    status["error"] = str(exc)

        return status

    def _get_api_url(self, group: str = "hath0r", custom_endpoint: Optional[str] = None) -> str:
        if custom_endpoint:
            endpoint = custom_endpoint.rstrip("/")
            if endpoint.endswith("/ajax-api/2.0/mlflow") or endpoint.endswith("/api/2.0/mlflow"):
                return endpoint
            return f"{endpoint}/ajax-api/2.0/mlflow"
        if group in self._cached_api_urls:
            return self._cached_api_urls[group]
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["hath0r"])
        st = self.check_status(group=group)
        if st["healthy"] and st["active_url"]:
            base = st["active_url"].rstrip("/")
            api_url = f"{base}/ajax-api/2.0/mlflow"
            self._cached_api_urls[group] = api_url
            return api_url
        return group_cfg["api_url"]

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        group: str = "hath0r",
        custom_endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        api_base = self._get_api_url(group=group, custom_endpoint=custom_endpoint)
        url = f"{api_base}{path}"
        headers = {
            "User-Agent": "hath0r-cli/mlflow-manager",
            "Content-Type": "application/json",
        }
        encoded_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=3.0) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content else {}

    def get_experiments(self, group: str = "hath0r", custom_endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query registered experiments from MLflow."""
        try:
            res = self._request("GET", "/experiments/search?max_results=50", group=group, custom_endpoint=custom_endpoint)
            return res.get("experiments", [])
        except Exception:
            return []

    def get_or_create_experiment(
        self,
        name: str,
        group: str = "hath0r",
        custom_endpoint: Optional[str] = None,
    ) -> Optional[str]:
        """Get or create an experiment by name, returning its experiment_id."""
        try:
            # Check if exists
            quoted = urllib.parse.quote(name)
            res = self._request("GET", f"/experiments/get-by-name?experiment_name={quoted}", group=group, custom_endpoint=custom_endpoint)
            if "experiment" in res and "experiment_id" in res["experiment"]:
                return res["experiment"]["experiment_id"]
        except Exception:
            pass

        # Try to create
        try:
            res = self._request(
                "POST",
                "/experiments/create",
                data={"name": name},
                group=group,
                custom_endpoint=custom_endpoint,
            )
            return res.get("experiment_id")
        except Exception:
            return None

    def get_runs(
        self,
        experiment_id: str,
        group: str = "hath0r",
        custom_endpoint: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query runs for a specific experiment ID."""
        try:
            res = self._request(
                "POST",
                "/runs/search",
                data={"experiment_ids": [experiment_id], "max_results": 50},
                group=group,
                custom_endpoint=custom_endpoint,
            )
            return res.get("runs", [])
        except Exception:
            return []

    def log_run(
        self,
        experiment_name: str,
        run_name: str,
        params: Dict[str, Any],
        metrics: Dict[str, float],
        tags: Optional[Dict[str, str]] = None,
        group: str = "hath0r",
        custom_endpoint: Optional[str] = None,
    ) -> Optional[str]:
        """Create an experiment run, log parameters and metrics, and mark it finished."""
        exp_id = self.get_or_create_experiment(name=experiment_name, group=group, custom_endpoint=custom_endpoint)
        if not exp_id:
            return None

        now_ms = int(time.time() * 1000)
        user_tags = [{"key": k, "value": str(v)} for k, v in (tags or {}).items()]
        user_tags.append({"key": "mlflow.runName", "value": run_name})

        try:
            # 1. Create run
            run_data = {
                "experiment_id": exp_id,
                "start_time": now_ms,
                "tags": user_tags,
                "run_name": run_name,
            }
            res = self._request("POST", "/runs/create", data=run_data, group=group, custom_endpoint=custom_endpoint)
            run_id = res.get("run", {}).get("info", {}).get("run_id")
            if not run_id:
                return None

            # 2. Log parameters
            for k, v in params.items():
                self._request(
                    "POST",
                    "/runs/log-parameter",
                    data={"run_id": run_id, "key": k, "value": str(v)},
                    group=group,
                    custom_endpoint=custom_endpoint,
                )

            # 3. Log metrics
            for k, v in metrics.items():
                try:
                    val = float(v)
                    self._request(
                        "POST",
                        "/runs/log-metric",
                        data={"run_id": run_id, "key": k, "value": val, "timestamp": now_ms, "step": 1},
                        group=group,
                        custom_endpoint=custom_endpoint,
                    )
                except (ValueError, TypeError):
                    continue

            # 4. Mark run as finished
            self._request(
                "POST",
                "/runs/update",
                data={"run_id": run_id, "status": "FINISHED", "end_time": int(time.time() * 1000)},
                group=group,
                custom_endpoint=custom_endpoint,
            )

            return run_id
        except Exception:
            return None


mlflow_manager_bot = MLflowManagerBot()
