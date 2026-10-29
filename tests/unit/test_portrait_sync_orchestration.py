"""PortraitSyncBot.sync: run directories, checkpoint resume and path guards."""

from __future__ import annotations

import json

import pytest

from hath0r_cli.bots import portrait_sync
from hath0r_cli.bots.portrait_sync import PortraitSyncBot

ROWS = [{"id": str(i), "bioguide_id": f"B{i:03d}", "display_name": f"Person {i}"} for i in range(5)]


@pytest.fixture
def bot(tmp_path, monkeypatch):
    (tmp_path / "cfg").mkdir()
    (tmp_path / "cfg" / "portraits.yaml").write_text(
        "output_dir: out\ncrosswalk_urls: []\nworkers: 2\nbioguide_ids: [B000, B001, B002, B003]\n", encoding="utf-8"
    )
    (tmp_path / "cfg" / "escape.yaml").write_text("output_dir: ../elsewhere\n", encoding="utf-8")
    b = PortraitSyncBot(cwd=tmp_path)
    monkeypatch.setattr(b, "read_profiles", lambda cfg: list(ROWS))
    monkeypatch.setattr(portrait_sync, "load_crosswalk", lambda fetcher, urls: {})
    monkeypatch.setattr(
        b,
        "resolve",
        lambda row, cfg, cw, f, gov: {"id": row["id"], "status": "verified" if int(row["id"]) % 2 else "missing"},
    )
    monkeypatch.setattr(b, "wikipedia_batch", lambda rows, results, cfg, cw, f, report: list(results.values()))
    monkeypatch.setattr(b, "apply", lambda cfg, results: {"written": sum(r["status"] == "verified" for r in results)})
    return b


def test_sync_new_run_then_resume(bot, tmp_path):
    first = bot.sync(limit=3, apply=True)
    assert first["profiles"] == 3 and first["counts"] == {"missing": 2, "verified": 1}
    assert first["publication"] == {"written": 1}
    run_dir = tmp_path / "out" / (tmp_path / "out" / "latest-run.txt").read_text()
    assert json.loads((run_dir / "summary.json").read_text())["profiles"] == 3

    resumed = bot.sync(resume=True)
    assert resumed["profiles"] == 4 and sum(resumed["counts"].values()) == 4
    assert len((run_dir / "portraits.jsonl").read_text().splitlines()) == 4


def test_sync_guards(bot, tmp_path):
    assert bot.sync(dry_run=True)["dry_run"] is True
    with pytest.raises(ValueError, match="Output must be inside"):
        bot.sync(config="cfg/escape.yaml")
    with pytest.raises(ValueError, match="Config must be inside"):
        bot.sync(config="../outside.yaml")
    with pytest.raises(ValueError, match="No prior checkpoint"):
        bot.sync(resume=True)
    (tmp_path / "out" / "latest-run.txt").write_text("../../etc", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid resume directory"):
        bot.sync(resume=True)
