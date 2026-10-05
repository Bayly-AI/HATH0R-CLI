"""
HATH0R CLI Phoenix Lifecycle & Manager Bot.

Provides unified container orchestration, multi-group deployment (Hath0r, 1-Nation, BaylyAI),
project namespace analytics, FinOps cost calculation, and health diagnostics for Arize Phoenix.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PhoenixManagerBot:
    """Manages Arize Phoenix lifecycle, multi-group deployments, and telemetry analytics."""

    GROUP_COMPOSE_MAP = {
        "hath0r": {
            "compose_file": "cfg/docker/groups/hath0r/docker-compose.yml",
            "service": "phoenix",
            "container": "HATH0R-Phoenix",
            "edge_url": "http://localhost:38000/phoenix/",
            "direct_url": "http://localhost:36006",
        },
        "1-nation": {
            "compose_file": "/Users/raybayly/Development/1-Nation/ATC/deploy/docker/docker-compose.yml",
            "project": "1-nation",
            "service": "1n-phoenix",
            "container": "1NPHOENIX",
            "edge_url": "http://localhost:58000/phoenix/",
            "direct_url": "http://localhost:6006",
        },
        "bai": {
            "compose_file": "cfg/docker/groups/bai/docker-compose.yml",
            "service": "phoenix",
            "container": "BAI-Phoenix",
            "edge_url": "http://localhost:48000/phoenix/",
            "direct_url": "http://localhost:46006",
        },
    }

    def start_phoenix(self, group: str = "hath0r", detach: bool = True) -> Dict[str, Any]:
        """Start the Phoenix container for the target group."""
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

    def stop_phoenix(self, group: str = "hath0r") -> Dict[str, Any]:
        """Stop the Phoenix container for the target group."""
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
        """Check status of Phoenix container and proxy endpoints."""
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["hath0r"])
        candidates = []
        if custom_endpoint:
            candidates.append(custom_endpoint)
        candidates.extend([
            group_cfg["edge_url"],
            group_cfg["direct_url"],
            "http://localhost:58000/phoenix/",
            "http://localhost:6006/",
        ])

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
                req = urllib.request.Request(probe_url, headers={"User-Agent": "hath0r-cli/phoenix-manager"})
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

    def get_projects(self, group: str = "1-nation") -> List[Dict[str, Any]]:
        """Query active projects and span distributions from the running Phoenix instance."""
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["1-nation"])
        container = group_cfg["container"]

        query_py = (
            "import sqlite3, json\n"
            "con = sqlite3.connect('/data/phoenix.db')\n"
            "cur = con.cursor()\n"
            "try:\n"
            "    projects = {}\n"
            "    rows = cur.execute('SELECT attributes FROM spans').fetchall()\n"
            "    for (attr_json,) in rows:\n"
            "        data = json.loads(attr_json)\n"
            "        pname = data.get('tool', {}).get('service') or data.get('bot', {}).get('id') or 'default'\n"
            "        projects[pname] = projects.get(pname, 0) + 1\n"
            "    print(json.dumps([{'name': k, 'span_count': v} for k, v in projects.items()]))\n"
            "except Exception as e:\n"
            "    print(json.dumps([{'error': str(e)}]))\n"
        )

        cmd = ["docker", "exec", container, "/usr/bin/python3.13", "-c", query_py]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout.strip())
        except Exception:
            # Fallback list if container is stopped or empty
            return [
                {"name": "1-nation-mcp", "span_count": 0, "status": "configured"},
                {"name": "1n-customer-mcp", "span_count": 0, "status": "configured"},
                {"name": "hath0r-framework", "span_count": 0, "status": "configured"},
                {"name": "bayly-ai-mcp", "span_count": 0, "status": "configured"},
            ]

    def get_cost_summary(self, group: str = "1-nation") -> Dict[str, Any]:
        """Aggregate FinOps token counts and calculated USD costs across recorded LLM spans."""
        group_cfg = self.GROUP_COMPOSE_MAP.get(group, self.GROUP_COMPOSE_MAP["1-nation"])
        container = group_cfg["container"]

        query_py = (
            "import sqlite3, json\n"
            "con = sqlite3.connect('/data/phoenix.db')\n"
            "cur = con.cursor()\n"
            "total_tokens = 0\n"
            "total_cost = 0.0\n"
            "spans_count = 0\n"
            "try:\n"
            "    spans_count = cur.execute('SELECT count(*) FROM spans').fetchone()[0]\n"
            "    rows = cur.execute('SELECT attributes FROM spans').fetchall()\n"
            "    for (attr_json,) in rows:\n"
            "        data = json.loads(attr_json)\n"
            "        total_tokens += data.get('llm', {}).get('token_count', {}).get('total', 0)\n"
            "        total_cost += data.get('llm', {}).get('cost', {}).get('total', 0.0)\n"
            "    print(json.dumps({'total_spans': spans_count, 'total_tokens': total_tokens, 'total_cost_usd': round(total_cost, 4)}))\n"
            "except Exception as e:\n"
            "    print(json.dumps({'error': str(e), 'total_spans': spans_count, 'total_tokens': 0, 'total_cost_usd': 0.0}))\n"
        )

        cmd = ["docker", "exec", container, "/usr/bin/python3.13", "-c", query_py]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout.strip())
        except Exception:
            return {"total_spans": 0, "total_tokens": 0, "total_cost_usd": 0.0, "status": "offline"}


phoenix_manager_bot = PhoenixManagerBot()
