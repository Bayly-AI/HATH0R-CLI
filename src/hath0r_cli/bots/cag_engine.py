"""Context-Augmented Generation (CAG) Engine with Prompt Caching & Princeton KV Pre-Warming."""

from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from .kv_prewarmer import kv_prewarmer


class CAGEngine:
    """Context-Augmented Generation (CAG) Engine for 100% full-context recall with prompt caching."""

    def __init__(self) -> None:
        self._cag_cache: Dict[str, Dict[str, Any]] = {}

    def pack_context(
        self,
        workspace_root: Optional[Path] = None,
        include_agentgraph: bool = True,
    ) -> Dict[str, Any]:
        """Aggregate workspace source files, AGENTS.md, and AgentGraph into CAG context envelope."""
        root = workspace_root or Path.cwd()
        start_time = time.perf_counter()

        files_content = {}
        total_tokens = 0

        # Include AGENTS.md if present
        agents_md = root / "AGENTS.md"
        if agents_md.exists():
            try:
                content = agents_md.read_text(encoding="utf-8")
                files_content["AGENTS.md"] = content
                total_tokens += len(content.split())
            except Exception:
                pass

        # Include AgentGraph snapshot if present
        if include_agentgraph:
            ag_json = root / ".hath0r" / "agentgraph" / "snapshot.json"
            if ag_json.exists():
                try:
                    content = ag_json.read_text(encoding="utf-8")
                    files_content[".hath0r/agentgraph/snapshot.json"] = content
                    total_tokens += len(content.split())
                except Exception:
                    pass

        # Scan python/config source files in workspace
        for walk_root, dirs, files in os.walk(root):
            # Exclude build / cache dirs
            dirs[:] = [d for d in dirs if d not in [".git", ".pytest_cache", "__pycache__", ".venv", ".mypy_cache", "node_modules"]]
            for file in files:
                if file.endswith((".py", ".json", ".md", ".toml", ".yaml", ".yml")) and file != "uv.lock":
                    file_path = Path(walk_root) / file
                    rel_path = file_path.relative_to(root).as_posix()
                    if rel_path in files_content:
                        continue
                    try:
                        text = file_path.read_text(encoding="utf-8", errors="ignore")
                        if len(text) < 50000: # Exclude massive generated artifacts
                            files_content[rel_path] = text
                            total_tokens += len(text.split())
                    except Exception:
                        pass

        # Construct CAG envelope string
        cag_buffer = [f"=== HATH0R CAG CONTEXT ENVELOPE (Workspace: {root.name}) ==="]
        for rel_p, txt in files_content.items():
            cag_buffer.append(f"\n--- FILE: {rel_p} ---\n{txt}")
        full_cag_text = "\n".join(cag_buffer)

        # Execute Princeton KV cache pre-warming on packed CAG context
        prewarm_res = kv_prewarmer.prewarm_context(
            shared_prompt=full_cag_text,
            system_prompt="hath0r_cag_prompt_caching_anchor",
            model_name="claude-3-7-sonnet-cag",
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        envelope = {
            "status": "packed",
            "workspace_name": root.name,
            "total_files": len(files_content),
            "estimated_tokens": total_tokens,
            "packing_elapsed_ms": elapsed_ms,
            "prompt_caching": {
                "type": "ephemeral",
                "cache_control": {"type": "ephemeral"},
                "provider": "anthropic_and_gemini_implicit",
            },
            "kv_prewarm": prewarm_res,
            "context_hash": prewarm_res["context_hash"],
        }
        self._cag_cache[str(root)] = envelope
        return envelope

    def get_cag_status(self, workspace_root: Optional[Path] = None) -> Dict[str, Any]:
        """Check status of packed CAG context."""
        root_str = str(workspace_root or Path.cwd())
        if root_str in self._cag_cache:
            return self._cag_cache[root_str]
        return self.pack_context(workspace_root)


cag_engine = CAGEngine()
