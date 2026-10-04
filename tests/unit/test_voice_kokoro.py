"""Unit tests for Kokoro-82M TTS engine and voice CLI commands."""

from click.testing import CliRunner

from hath0r_cli.cli import main as cli
from hath0r_cli.voice_kokoro import KokoroTTSEngine


def test_kokoro_voice_profiles():
    """Verify built-in Kokoro voice profiles."""
    engine = KokoroTTSEngine()
    voices = engine.list_voices()
    assert len(voices) >= 6
    assert any(v["id"] == "af_heart" for v in voices)
    assert any(v["id"] == "am_adam" for v in voices)


def test_kokoro_synthesis_wav():
    """Verify WAV byte generation and metadata."""
    engine = KokoroTTSEngine()
    wav_bytes, meta = engine.synthesize("Build completed successfully.", voice_id="af_heart")
    assert len(wav_bytes) > 100
    assert wav_bytes.startswith(b"RIFF")
    assert b"WAVE" in wav_bytes[:16]
    assert meta["engine"] == "kokoro-82m"
    assert meta["voice"] == "af_heart"
    assert meta["sample_rate"] == 24000
    assert meta["duration_sec"] > 0


def test_voice_speak_cli_kokoro_dry_run():
    """Verify hath0r voice speak --engine kokoro."""
    runner = CliRunner()
    res = runner.invoke(
        cli, ["voice", "speak", "--dry-run", "--engine", "kokoro", "--voice", "am_adam", "Testing voice."]
    )
    assert res.exit_code == 0
    assert "am_adam" in res.output or "Testing voice." in res.output


def test_voice_list_voices_cli():
    """Verify hath0r voice list-voices CLI command."""
    runner = CliRunner()
    res = runner.invoke(cli, ["-o", "json", "voice", "list-voices"])
    assert res.exit_code == 0
    assert "af_heart" in res.output
    assert "am_adam" in res.output
