"""Context-Augmented Generation (CAG) Engine with Prompt Caching & Princeton KV Pre-Warming."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .kv_prewarmer import kv_prewarmer


class CAGEngine:
    """Context-Augmented Generation (CAG) Engine for 100% full-context recall with prompt caching."""

    def __init__(self) -> None:
        self._cag_cache: Dict[str, Dict[str, Any]] = {}

    def _read_file_safe(self, fp: Path, root: Path, files_content: Dict[str, str]) -> int:
        if not fp.exists():
            return 0
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
            rel_path = fp.relative_to(root).as_posix()
            files_content[rel_path] = content
            return len(content.split())
        except Exception:
            return 0

    def _scan_workspace_sources(self, root: Path, files_content: Dict[str, str]) -> int:
        added_tokens = 0
        valid_exts = (".py", ".json", ".md", ".toml", ".yaml", ".yml")
        skip_dirs = [".git", ".pytest_cache", "__pycache__", ".venv", ".mypy_cache", "node_modules"]

        for walk_root, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if file.endswith(valid_exts) and file != "uv.lock":
                    fp = Path(walk_root) / file
                    rel_path = fp.relative_to(root).as_posix()
                    if rel_path not in files_content:
                        added_tokens += self._read_file_safe(fp, root, files_content)
        return added_tokens

    def pack_context(
        self,
        workspace_root: Optional[Path] = None,
        include_agentgraph: bool = True,
    ) -> Dict[str, Any]:
        """Aggregate workspace source files, AGENTS.md, and AgentGraph into CAG context envelope."""
        root = workspace_root or Path.cwd()
        start_time = time.perf_counter()

        files_content: Dict[str, str] = {}
        total_tokens = 0

        total_tokens += self._read_file_safe(root / "AGENTS.md", root, files_content)
        if include_agentgraph:
            total_tokens += self._read_file_safe(root / ".hath0r" / "agentgraph" / "snapshot.json", root, files_content)

        total_tokens += self._scan_workspace_sources(root, files_content)


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
