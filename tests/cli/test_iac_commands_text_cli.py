"""Text-mode CLI tests for `hath0r iac`, run against a scratch repository."""

from __future__ import annotations

import json

from click.testing import CliRunner

from hath0r_cli.cli import main


def _run(*args: str):
    return CliRunner().invoke(main, ["-o", "text", "iac", *args])


def test_iac_lifecycle_text(tmp_path):
    repo = tmp_path / "svc"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='svc'\n", encoding="utf-8")

    before = _run("validate", str(repo))
    assert before.exit_code == 0, before.output
    assert "REMEDIATION REQUIRED" in before.output and "Action Items" in before.output

    init = _run("init", str(repo), "--tech-stack", "python", "--app-name", "svc")
    assert init.exit_code == 0, init.output
    assert "Scaffolding Complete" in init.output and "Dockerfile" in init.output

    audit = _run("audit", str(repo))
    assert audit.exit_code == 0, audit.output
    assert "3-Pillar IaC Verification" in audit.output

    validate = _run("validate", str(repo))
    assert "Validating IaC Compliance" in validate.output

    salt = _run("salt", "ghcr.io/bayly-ai/svc:1.0", "--workspace", str(repo))
    assert salt.exit_code == 0, salt.output
    assert "Cryptographically Salted" in salt.output

    render = _run("render", str(repo), "--env", "staging")
    assert render.exit_code == 0, render.output
    assert "Manifests for Environment" in render.output


def test_iac_sweep_text(tmp_path):
    for name in ("a", "b"):
        (tmp_path / name / ".git").mkdir(parents=True)
    _run("init", str(tmp_path / "a"), "--tech-stack", "static", "--app-name", "a")
    res = _run("audit", str(tmp_path), "--sweep")
    assert res.exit_code == 0, res.output
    assert "IaC Governance Summary" in res.output


def test_iac_group_help_and_json(tmp_path):
    assert "Infrastructure as Code" in CliRunner().invoke(main, ["iac"]).output
    res = CliRunner().invoke(main, ["-o", "json", "iac", "audit", str(tmp_path)])
    assert json.loads(res.output)["command"] == "iac audit"
