"""Tests for contracts validation, parity checking, and sync capabilities."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hath0r_cli.bots.contracts_bot import ContractsBot
from hath0r_cli.cli import main


def test_contracts_bot_validate_and_sync(tmp_path: Path) -> None:
    canon_dir = tmp_path / "canonical" / "contracts" / "schemas"
    canon_dir.mkdir(parents=True)
    schema1 = canon_dir / "test-schema-v1.json"
    schema1.write_text(
        json.dumps({"$schema": "http://json-schema.org/draft-07/schema#", "title": "Test1"}), encoding="utf-8"
    )

    member_dir = tmp_path / "member_repo"
    member_schemas = member_dir / "contracts" / "schemas"
    member_schemas.mkdir(parents=True)

    bot = ContractsBot(cwd=member_dir, canonical_dir=canon_dir)

    # 1. Validate should report missing_local
    val1 = bot.validate_contracts(target_dir=member_dir)
    assert val1["success"] is True
    assert val1["state"] == "drift_detected"
    assert val1["summary"]["missing_local"] == 1

    # 2. Dry-run sync
    dry_res = bot.sync_contracts(target_dir=member_dir, dry_run=True)
    assert dry_res["success"] is True
    assert dry_res["synced_count"] == 1
    assert not (member_schemas / "test-schema-v1.json").exists()

    # 3. Real sync
    sync_res = bot.sync_contracts(target_dir=member_dir, dry_run=False)
    assert sync_res["success"] is True
    assert (member_schemas / "test-schema-v1.json").exists()

    # 4. Re-validate after sync -> should be in_sync
    val2 = bot.validate_contracts(target_dir=member_dir)
    assert val2["state"] == "ok"
    assert val2["summary"]["in_sync"] == 1
    assert val2["summary"]["drifted"] == 0


def test_cli_contracts_validate_and_sync_commands(tmp_path: Path) -> None:
    canon_dir = tmp_path / "canonical" / "contracts" / "schemas"
    canon_dir.mkdir(parents=True)
    schema1 = canon_dir / "hath0r-test-v1.json"
    schema1.write_text(json.dumps({"title": "CLI Test Schema"}), encoding="utf-8")

    member_dir = tmp_path / "member_repo"
    runner = CliRunner()

    # CLI Validate
    res_val = runner.invoke(
        main,
        [
            "--output",
            "json",
            "contracts",
            "validate",
            "--canonical-dir",
            str(canon_dir),
            "--target-dir",
            str(member_dir),
        ],
    )
    assert res_val.exit_code == 0
    data_val = json.loads(res_val.output)
    assert "data" in data_val
    assert data_val["data"]["success"] is True

    # CLI Sync (dry-run)
    res_dry = runner.invoke(
        main,
        [
            "--output",
            "json",
            "contracts",
            "sync",
            "--canonical-dir",
            str(canon_dir),
            "--target-dir",
            str(member_dir),
            "--dry-run",
        ],
    )
    assert res_dry.exit_code == 0
    data_dry = json.loads(res_dry.output)
    assert data_dry["data"]["dry_run"] is True

    # CLI Sync (real)
    res_sync = runner.invoke(
        main,
        ["contracts", "sync", "--canonical-dir", str(canon_dir), "--target-dir", str(member_dir)],
    )
    assert res_sync.exit_code == 0
    assert "Synced" in res_sync.output or "up to date" in res_sync.output
