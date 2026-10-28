"""Legacy --json / --format options must honour the global -o/--output mode."""

import json

from click.testing import CliRunner

from hath0r_cli.cli import main


def test_global_json_enables_legacy_json_flag():
    result = CliRunner().invoke(main, ["-o", "json", "--quiet", "mesh", "status"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "ONLINE"


def test_global_text_keeps_rich_table():
    result = CliRunner().invoke(main, ["-o", "text", "--quiet", "mesh", "status"])
    assert result.exit_code == 0
    assert "GAIN Mesh Node Status" in result.output


def test_explicit_json_flag_wins_over_text_mode():
    result = CliRunner().invoke(main, ["-o", "text", "--quiet", "mesh", "peers", "--json"])
    assert result.exit_code == 0
    assert any(p["peer_id"] == "peer-poc" for p in json.loads(result.output))


def test_auto_mode_non_tty_resolves_to_json():
    # CliRunner stdout is not a TTY, so auto → json.
    result = CliRunner().invoke(main, ["--quiet", "mesh", "peers"])
    assert result.exit_code == 0
    assert isinstance(json.loads(result.output), list)


def test_pmat_stats_format_follows_global_json(tmp_path):
    result = CliRunner().invoke(main, ["-o", "json", "--quiet", "pmat", "stats", "--target", str(tmp_path)])
    assert result.exit_code == 0
    assert isinstance(json.loads(result.output), dict)
