"""Apache Airflow Hook for HATH0R Operator CLI."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from airflow.hooks.base import BaseHook  # type: ignore[import-untyped]
except ImportError:
    class BaseHook:  # type: ignore[no-redef]
        """Fallback shim when apache-airflow is not installed."""
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass


class Hath0rHook(BaseHook):
    """Airflow Hook to interface with the HATH0R Operator CLI."""

    conn_name_attr = "hath0r_conn_id"
    default_conn_name = "hath0r_default"
    conn_type = "hath0r"
    hook_name = "HATH0R"

    def __init__(
        self,
        cli_path: Optional[str] = None,
        workspace_root: Optional[str] = None,
        hath0r_conn_id: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.cli_path = cli_path or self._resolve_cli_path()
        self.workspace_root = workspace_root or os.getcwd()
        self.hath0r_conn_id = hath0r_conn_id

    @staticmethod
    def _resolve_cli_path() -> str:
        """Locate the hath0r binary in PATH or standard system locations."""
        found = shutil.which("hath0r")
        if found:
            return found
        candidates = [
            "/usr/local/bin/hath0r",
            os.path.expanduser("~/.local/bin/hath0r"),
            "/opt/hath0r/bin/hath0r",
        ]
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "hath0r"

    def execute_cli(
        self,
        args: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        parse_json: bool = True,
        check: bool = True,
    ) -> Dict[str, Any]:
        """Execute a HATH0R CLI command and capture output."""
        working_dir = cwd or self.workspace_root
        cmd = [self.cli_path] + args

        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        proc = subprocess.run(
            cmd,
            cwd=working_dir,
            env=merged_env,
            capture_output=True,
            text=True,
        )

        parsed_data = None
        if parse_json and proc.stdout:
            try:
                parsed_data = json.loads(proc.stdout)
            except Exception:
                # Not JSON or mixed text output
                parsed_data = None

        result = {
            "command": " ".join(cmd),
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "parsed_json": parsed_data,
        }

        if check and proc.returncode != 0:
            err_msg = f"Hath0r CLI execution failed (exit code {proc.returncode}): {proc.stderr or proc.stdout}"
            raise RuntimeError(err_msg)

        return result
