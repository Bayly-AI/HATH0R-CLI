"""Tests for Apache Airflow Hook, Operator, and Provider info in HATH0R-CLI."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from hath0r_cli.integrations.airflow.hook import Hath0rHook
from hath0r_cli.integrations.airflow.operator import Hath0rCliOperator
from hath0r_cli.integrations.airflow.provider import get_provider_info


class TestAirflowIntegration:
    """Test suite for Airflow integration components."""

    def test_provider_info(self):
        info = get_provider_info()
        assert info["package-name"] == "apache-airflow-providers-hath0r"
        assert "hath0r_cli.integrations.airflow.hook.Hath0rHook" in info["hook-class-names"]

    def test_hook_resolution(self):
        hook = Hath0rHook(cli_path="/custom/path/hath0r")
        assert hook.cli_path == "/custom/path/hath0r"

    @patch("subprocess.run")
    def test_hook_execute_cli_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({"status": "success", "data": 42})
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        hook = Hath0rHook(cli_path="hath0r")
        res = hook.execute_cli(args=["factory", "list", "-o", "json"], parse_json=True)

        assert res["returncode"] == 0
        assert res["parsed_json"] == {"status": "success", "data": 42}
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_hook_execute_cli_failure_raises(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = ""
        mock_proc.stderr = "Command not recognized"
        mock_run.return_value = mock_proc

        hook = Hath0rHook(cli_path="hath0r")
        with pytest.raises(RuntimeError, match="Hath0r CLI execution failed"):
            hook.execute_cli(args=["invalid-command"], check=True)

    @patch("subprocess.run")
    def test_operator_execute(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = json.dumps({"factory_id": "test-factory", "status": "executed"})
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        operator = Hath0rCliOperator(
            task_id="test_task",
            command="factory run test-factory",
            cli_path="hath0r",
            json_output=True,
        )

        output = operator.execute(context={})
        assert output == {"factory_id": "test-factory", "status": "executed"}
        # Ensure -o json was appended
        call_args = mock_run.call_args[0][0]
        assert "-o" in call_args and "json" in call_args
