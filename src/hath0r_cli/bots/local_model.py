"""Local LLM runtime adapter bot supporting Ollama and Apple MLX.

Enables offline agent inference and JEV decision guarding without cloud dependencies.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LocalRuntimeStatus:
    """Status snapshot of local hardware and model acceleration backends."""

    os_name: str
    architecture: str
    has_metal: bool
    has_cuda: bool
    ollama_running: bool
    ollama_url: str
    installed_models: List[str] = field(default_factory=list)
    mlx_available: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class LocalModelBot:
    """Manages local model inference, hardware detection, and runtime execution."""

    def __init__(self, ollama_url: str = "http://localhost:11434") -> None:
        self.ollama_url = ollama_url.rstrip("/")

    def detect_hardware(self) -> LocalRuntimeStatus:
        """Inspect host operating system and GPU acceleration capabilities."""
        system_os = platform.system()
        machine = platform.machine()
        has_metal = system_os == "Darwin" and machine in ("arm64", "aarch64")
        has_cuda = False

        # Check CUDA via nvidia-smi if not on macOS
        if not has_metal:
            try:
                res = subprocess.run(
                    ["nvidia-smi"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=2,
                )
                has_cuda = res.returncode == 0
            except Exception:
                has_cuda = False

        # Check MLX availability
        mlx_available = False
        if has_metal:
            try:
                import importlib.util

                mlx_available = importlib.util.find_spec("mlx_lm") is not None
            except Exception:
                mlx_available = False

        # Check Ollama
        ollama_running, models = self.check_ollama()

        return LocalRuntimeStatus(
            os_name=system_os,
            architecture=machine,
            has_metal=has_metal,
            has_cuda=has_cuda,
            ollama_running=ollama_running,
            ollama_url=self.ollama_url,
            installed_models=models,
            mlx_available=mlx_available,
        )

    def check_ollama(self) -> tuple[bool, List[str]]:
        """Query Ollama server API for running status and installed models."""
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", headers={"User-Agent": "Hath0r-CLI"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                    return True, models
        except Exception:
            pass
        return False, []

    def generate(
        self,
        prompt: str,
        model: str = "llama3.2",
        system: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Execute local completion via Ollama HTTP API with fallback simulation."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        start_time = time.time()
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "Hath0r-CLI"},
            )
            with urllib.request.urlopen(req, timeout=60.0) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    latency = time.time() - start_time
                    eval_count = res_json.get("eval_count", 0)
                    eval_duration_ns = res_json.get("eval_duration", 1)
                    tok_per_sec = (eval_count / (eval_duration_ns / 1e9)) if eval_duration_ns > 0 else 0.0

                    return {
                        "response": res_json.get("response", ""),
                        "model": model,
                        "backend": "ollama",
                        "prompt_tokens": res_json.get("prompt_eval_count", 0),
                        "completion_tokens": eval_count,
                        "latency_seconds": round(latency, 3),
                        "tokens_per_second": round(tok_per_sec, 2),
                        "status": "success",
                    }
        except Exception as e:
            # Fallback simulator for offline testing / development
            latency = time.time() - start_time
            simulated_resp = f"[LocalModelBot (Offline Mock: {model})] Received prompt: {prompt[:80]}..."
            return {
                "response": simulated_resp,
                "model": model,
                "backend": "offline-fallback",
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(simulated_resp.split()),
                "latency_seconds": round(latency, 3),
                "tokens_per_second": 45.0,
                "status": "simulated",
                "error": str(e),
            }
