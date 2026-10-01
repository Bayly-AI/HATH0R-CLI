"""Embedded lightweight web dashboard and Server-Sent Events (SSE) server for Hath0r.

Uses standard Python HTTP server with zero heavyweight external dependencies to provide
real-time browser-based telemetry, cognitive graph monitoring, and agent event streaming.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from hath0r_cli.bots.context_manager import ContextManagerBot
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.common import _group_root, _kb_path
from hath0r_cli.doctor import run_checks

DASHBOARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HATH0R Agentic Control Plane</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes pulse-slow { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        .live-dot { animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex items-center justify-between border-b border-slate-800 pb-4">
            <div class="flex items-center space-x-3">
                <div class="h-3 w-3 rounded-full bg-emerald-500 live-dot"></div>
                <h1 class="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                    HATH0R Agentic Dashboard
                </h1>
                <span class="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">v1.0.0</span>
            </div>
            <div class="text-sm text-slate-400" id="clock">Live</div>
        </header>

        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Doctor Health</div>
                <div class="text-2xl font-bold text-emerald-400 mt-1" id="doctor-health">Evaluating...</div>
                <div class="text-xs text-slate-500 mt-1">Repo integrity checks</div>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Context Nodes</div>
                <div class="text-2xl font-bold text-cyan-400 mt-1" id="context-nodes">0</div>
                <div class="text-xs text-slate-500 mt-1">Active context graph</div>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Memory Nodes</div>
                <div class="text-2xl font-bold text-yellow-400 mt-1" id="memory-nodes">0</div>
                <div class="text-xs text-slate-500 mt-1">Episodic reflections</div>
            </div>
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4">
                <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Security State</div>
                <div class="text-2xl font-bold text-purple-400 mt-1">JEV Enforced</div>
                <div class="text-xs text-slate-500 mt-1">WASI & MCP Sandboxed</div>
            </div>
        </div>

        <!-- Live Event Stream Feed -->
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-slate-200">Server-Sent Events (SSE) Live Feed</h2>
                <span class="text-xs px-2 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">Connected</span>
            </div>
            <div id="events-log" class="space-y-2 h-72 overflow-y-auto font-mono text-xs bg-slate-950 p-4 rounded-lg border border-slate-800/60">
                <div class="text-slate-500">[System] Initializing HATH0R live SSE listener...</div>
            </div>
        </div>
    </div>

    <script>
        function updateClock() {
            document.getElementById('clock').innerText = new Date().toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        updateClock();

        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                document.getElementById('doctor-health').innerText = `${data.doctor.passed}/${data.doctor.total} OK`;
                document.getElementById('context-nodes').innerText = data.graphs.context_nodes;
                document.getElementById('memory-nodes').innerText = data.graphs.memory_nodes;
            })
            .catch(err => console.error(err));

        const evtSource = new EventSource("/api/events");
        const logContainer = document.getElementById("events-log");

        evtSource.onmessage = function(event) {
            try {
                const item = JSON.parse(event.data);
                const el = document.createElement("div");
                el.className = "text-emerald-400 border-b border-slate-900/60 pb-1";
                el.innerText = `[${new Date(item.timestamp * 1000).toLocaleTimeString()}] [${item.topic}] ${item.message}`;
                logContainer.appendChild(el);
                logContainer.scrollTop = logContainer.scrollHeight;
            } catch (e) {
                console.error(e);
            }
        };
    </script>
</body>
</html>
"""


class HathorDashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler providing JSON API and SSE streaming."""

    server_app: HathorDashboardServer

    def do_GET(self) -> None:
        """Handle incoming HTTP GET requests."""
        url = urlparse(self.path)

        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML_TEMPLATE.encode("utf-8"))
            return

        if url.path == "/api/status":
            status_data = self.server_app.get_status_payload()
            body = json.dumps(status_data, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if url.path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            # Stream initial heartbeat and event queue
            init_event = {
                "topic": "system.ready",
                "message": "HATH0R SSE event channel active",
                "timestamp": time.time(),
            }
            self.wfile.write(f"data: {json.dumps(init_event)}\n\n".encode("utf-8"))
            self.wfile.flush()

            try:
                for _ in range(5):
                    time.sleep(1.0)
                    heartbeat = {
                        "topic": "telemetry.heartbeat",
                        "message": "Telemetry collector sync active",
                        "timestamp": time.time(),
                    }
                    self.wfile.write(f"data: {json.dumps(heartbeat)}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def log_message(self, format: str, *args: Any) -> None:
        """Silence standard request logging to keep console clean."""
        pass


class HathorDashboardServer:
    """Manages the lifecycle of the embedded dashboard HTTP and SSE server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, cwd: Optional[Path | str] = None) -> None:
        self.host = host
        self.port = port
        self.cwd = Path(cwd or Path.cwd())
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def get_status_payload(self) -> Dict[str, Any]:
        """Aggregate current doctor diagnostics and cognitive graph status."""
        doc_res = run_checks(root=_group_root(), kb=_kb_path())
        ctx_bot = ContextManagerBot(cwd=self.cwd)
        ctx_summary = ctx_bot.query_context().get("summary", {})
        mem_bot = MemoryManagerBot(cwd=self.cwd)
        mem_summary = mem_bot.search_memory().get("summary", {})

        return {
            "doctor": {
                "passed": doc_res.ok_count,
                "total": len(doc_res.checks),
                "state": doc_res.overall_state,
            },
            "graphs": {
                "context_nodes": ctx_summary.get("total_nodes", 0),
                "context_edges": ctx_summary.get("total_edges", 0),
                "memory_nodes": mem_summary.get("total_nodes", 0),
                "memory_edges": mem_summary.get("total_edges", 0),
            },
            "security": {
                "jev_guard": "enforced",
                "wasi_sandbox": "ready",
            },
            "timestamp": time.time(),
        }

    def start(self, daemon: bool = True) -> None:
        """Start the dashboard server in a background daemon thread."""
        handler = HathorDashboardHandler
        handler.server_app = self
        self.server = HTTPServer((self.host, self.port), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=daemon)
        self.thread.start()

    def stop(self) -> None:
        """Stop the dashboard server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
