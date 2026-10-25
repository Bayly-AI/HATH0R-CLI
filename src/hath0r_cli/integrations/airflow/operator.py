"""Apache Airflow Operator for executing HATH0R Operator CLI commands."""

from __future__ import annotations

import shlex
from typing import Any, Dict, List, Optional, Sequence

try:
    from airflow.models.baseoperator import BaseOperator  # type: ignore[import-untyped]
except ImportError:
    class BaseOperator:  # type: ignore[no-redef]
        """Fallback shim when apache-airflow is not installed."""
        template_fields: Sequence[str] = ()

        def __init__(self, task_id: str, *args: Any, **kwargs: Any) -> None:
            self.task_id = task_id

from .hook import Hath0rHook


class Hath0rCliOperator(BaseOperator):
    """Executes HATH0R CLI commands inside an Apache Airflow DAG.

    Examples:
        run_factory = Hath0rCliOperator(
            task_id="run_onboarding_factory",
            command="factory run onboarding-factory",
            json_output=True,
        )

        calibrate_runtime = Hath0rCliOperator(
            task_id="calibrate_substrate",
            command="cicccdct calibrate",
        )
    """

    template_fields: Sequence[str] = ("command", "command_args", "cwd")

    def __init__(
        self,
        task_id: str,
        command: Optional[str] = None,
        command_args: Optional[List[str]] = None,
        cli_path: Optional[str] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        json_output: bool = True,
        hath0r_conn_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, **kwargs)
        self.command = command
        self.command_args = command_args or []
        self.cli_path = cli_path
        self.cwd = cwd
        self.env = env
        self.json_output = json_output
        self.hath0r_conn_id = hath0r_conn_id

    def execute(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the configured Hath0r CLI command."""
        hook = Hath0rHook(
            cli_path=self.cli_path,
            workspace_root=self.cwd,
            hath0r_conn_id=self.hath0r_conn_id,
        )

        args: List[str] = []
        if self.command:
            args = shlex.split(self.command)
        elif self.command_args:
            args = list(self.command_args)
        else:
            raise ValueError("Either 'command' or 'command_args' must be provided to Hath0rCliOperator.")

        if self.json_output and "-o" not in args and "--output" not in args:
            args.extend(["-o", "json"])

        res = hook.execute_cli(
            args=args,
            cwd=self.cwd,
            env=self.env,
            parse_json=self.json_output,
            check=True,
        )

        # Return parsed JSON data if available, otherwise raw stdout
        if res.get("parsed_json") is not None:
            return dict(res["parsed_json"])
        return res
