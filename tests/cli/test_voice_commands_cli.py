"""Text- and JSON-mode coverage for the `hath0r voice` / `hath0r speak` command surface.

Bots are replaced with a fake whose every method returns a canned result, so
these tests exercise the CLI wiring and renderers without touching audio, TTS
or OS services.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from click.testing import CliRunner

import hath0r_cli.bots.voice_converse as voice_converse
import hath0r_cli.bots.voice_daemon as voice_daemon
import hath0r_cli.bots.voice_speaker as voice_speaker
import hath0r_cli.voice as voice_mod
from hath0r_cli.cli import main


class Seq(list):
    """Successive return values for successive method calls on a FakeBot."""


class FakeBot:
    """Stand-in for any bot: every method call returns ``result`` (or the next item of a Seq)."""

    def __init__(self, result: Any) -> None:
        self._results = list(result) if isinstance(result, Seq) else None
        self._result = result

    def __getattr__(self, name: str):
        def method(*args: Any, **kwargs: Any) -> Any:
            if self._results is not None:
                return self._results.pop(0) if len(self._results) > 1 else self._results[0]
            return self._result

        return method


def _patch(monkeypatch, module, name, result):
    monkeypatch.setattr(module, name, lambda *a, **k: FakeBot(result))


def _run(*args: str, input: str | None = None):
    return CliRunner().invoke(main, list(args), input=input)


# (cli args, module, class name, results to try, expected text fragments per result)
BOT_CASES = [
    (["voice", "speak", "hello"], voice_speaker, "VoiceSpeakerBot",
     [{"success": True, "engine": "say", "text": "hello"}], ["Spoken Message (say)"]),
    (["voice", "announce", "hi"], voice_speaker, "VoiceSpeakerBot",
     [{"success": False, "text": "hi"}], ["Spoken Announcement"]),
    (["voice", "announce", "hi", "--queue", "--priority", "high"], voice_speaker, "SpokenNotificationServiceBot",
     [{"queued": True}], ["Queued spoken announcement"]),
    (["voice", "speaker", "start"], voice_speaker, "SpokenNotificationServiceBot",
     [{"success": True, "status": "started", "pid": 1}, {"status": "already_running", "pid": 2},
      {"success": False, "message": "nope"}],
     ["Speaker Bot Started", "already running", "nope"]),
    (["voice", "speaker", "stop"], voice_speaker, "SpokenNotificationServiceBot",
     [{"success": True, "status": "stopped", "pid": 1}, {"status": "not_running"}],
     ["Speaker Bot Stopped", "not currently running"]),
    (["voice", "speaker", "status"], voice_speaker, "SpokenNotificationServiceBot",
     [{"running": True, "pid": 3, "pending_count": 2}, {"running": False, "pending_count": 0}],
     ["RUNNING", "STOPPED"]),
    (["voice", "speaker", "drain", "--max-messages", "2"], voice_speaker, "SpokenNotificationServiceBot",
     [[{"text": "a"}, {"text": "b"}]], ["Drained 2"]),
    (["voice", "profile", "list"], voice_speaker, "VoiceProfileBot",
     [{"voices": [{"name": "Ava", "locale": "en_US", "quality": "premium", "is_active": True},
                  {"name": "Zoe", "locale": "en_GB"}],
       "active_profile": {"voice_name": "Ava", "rate_wpm": 180}}],
     ["Active Voice"]),
    (["voice", "profile", "list", "--all"], voice_speaker, "VoiceProfileBot",
     [{"voices": [{"name": "Thomas", "locale": "fr_FR"}], "active_profile": {}}], ["Thomas"]),
    (["voice", "profile"], voice_speaker, "VoiceProfileBot",
     [{"voices": [], "active_profile": {"voice_name": "Ava"}}], ["Active Voice"]),
    (["voice", "profile", "set", "Ava", "--rate", "brisk", "--no-preview"], voice_speaker, "VoiceProfileBot",
     [{"success": True, "voice_name": "Ava", "rate_wpm": 200, "config_file": "/tmp/v.json"}],
     ["Ava"]),
    (["voice", "profile", "status"], voice_speaker, "VoiceProfileBot",
     [{"voice_name": "Ava", "rate_wpm": 180}], ["Ava"]),
    (["voice", "read", "read me"], voice_speaker, "ActiveTabReaderBot",
     [{"success": True, "app": "Warp", "spoken_text": "read me"}, {"success": False, "error": "no window"}],
     ["Vocalized from Warp", "no window"]),
    (["voice", "read", "--selection"], voice_speaker, "ActiveTabReaderBot",
     [{"success": True, "app": "Code", "spoken_text": "sel"}], ["Vocalized from Code"]),
    (["voice", "engine", "download", "--engine", "onnx-neural", "--dry-run"], voice_speaker,
     "LocalNeuralVoiceEngine", [{"message": "Downloaded", "target_path": "/m"}], ["Downloaded"]),
    (["speak"], voice_speaker, "VoiceSpeakerModeBot",
     [{"enabled": True, "scope": "tab", "saved_tab": "tab-1"}, {"enabled": False}], ["ENABLED", "DISABLED"]),
    (["speak", "status"], voice_speaker, "VoiceSpeakerModeBot",
     [{"enabled": True, "scope": "global"}, {"enabled": False}], ["Speak", "Speak"]),
    (["speak", "on", "--tab-only", "--silent"], voice_speaker, "VoiceSpeakerModeBot",
     [{"success": True, "scope": "tab", "tab_id": "t1"}, {"success": True, "scope": "global"}],
     ["ACTIVE TAB ONLY", "GLOBAL"]),
    (["speak", "off", "--silent"], voice_speaker, "VoiceSpeakerModeBot", [{"success": True}], [""]),
    (["speak", "toggle"], voice_speaker, "VoiceSpeakerModeBot",
     [{"enabled": True, "scope": "tab"}, {"enabled": False}], ["ACTIVE TAB ONLY", ""]),
    (["voice", "service", "start", "--ambient"], voice_converse, "VoiceServiceBot",
     [{"success": True, "status": "started", "pid": 9, "log_file": "/l"}, {"status": "already_running", "pid": 9},
      {"message": "odd"}],
     ["Voice Bot Service Started", "already running", "odd"]),
    (["voice", "service", "stop"], voice_converse, "VoiceServiceBot",
     [{"success": True, "status": "stopped", "pid": 9}, {"status": "not_running"}], ["Stopped", ""]),
    (["voice", "service", "status"], voice_converse, "VoiceServiceBot",
     [{"running": True, "pid": 9, "log_file": "/l"}, {"running": False}], ["RUNNING", ""]),
    (["voice", "service", "restart"], voice_converse, "VoiceServiceBot",
     [{"success": True, "pid": 10}], ["Restarted"]),
    (["voice", "service", "install"], voice_converse, "VoiceServiceBot",
     [{"success": True, "service_manager": "launchd", "plist_path": "/p"}, {"success": False, "error": "denied"}],
     ["Installed", "denied"]),
    (["voice", "service", "uninstall"], voice_converse, "VoiceServiceBot",
     [{"success": True, "message": "removed"}, {"success": False, "error": "missing"}], ["Uninstalled", "missing"]),
    (["voice", "daemon", "start"], voice_daemon, "VoiceDaemonBot",
     [{"success": True, "status": "started", "pid": 4, "socket": "/s"}, {"status": "already_running", "pid": 4},
      {"message": "meh"}],
     ["Voice Daemon Started", "already running", "meh"]),
    (["voice", "daemon", "stop"], voice_daemon, "VoiceDaemonBot",
     [{"success": True, "status": "stopped", "pid": 4}, {"status": "idle"}], ["Stopped", "not currently running"]),
    (["voice", "daemon", "status"], voice_daemon, "VoiceDaemonBot",
     [{"running": True, "pid": 4, "socket": "/s", "uptime_seconds": 5, "events_processed": 1}, {"running": False}],
     ["RUNNING", "STOPPED"]),
    (["voice", "daemon", "emit", "task.done", "Finished", "--payload", '{"k": 1}', "--no-speak"], voice_daemon,
     "VoiceDaemonBot", [{"success": True, "ipc_delivery": "socket"}, {"success": False}], ["Event Emitted", ""]),
    (["voice", "daemon", "emit", "task.done", "Finished", "--payload", "{bad json"], voice_daemon,
     "VoiceDaemonBot", [{"success": True, "ipc_delivery": "spool"}], ["Event Emitted"]),
]


@pytest.mark.parametrize("args, module, cls, results, fragments", BOT_CASES, ids=lambda v: v if isinstance(v, str) else None)
def test_voice_bot_commands_text(monkeypatch, args, module, cls, results, fragments):
    for result, fragment in zip(results, fragments):
        _patch(monkeypatch, module, cls, result)
        res = _run("-o", "text", *args)
        assert res.exception is None or isinstance(res.exception, SystemExit), res.output
        assert fragment in res.output, (args, result, res.output)


@pytest.mark.parametrize("args, module, cls, results, fragments", BOT_CASES[:6])
def test_voice_bot_commands_json(monkeypatch, args, module, cls, results, fragments):
    _patch(monkeypatch, module, cls, results[0])
    res = _run("-o", "json", *args)
    assert json.loads(res.output)["command"].startswith(args[0])


def test_voice_status_text(monkeypatch):
    monkeypatch.setattr(
        voice_mod,
        "inspect_voice_subsystem",
        lambda: {
            "status": "ok",
            "platform": "darwin",
            "stt": {"provider": "whisper", "sample_rate": 16000, "vad_enabled": True},
            "tts": {"engine": "say"},
            "router": {"provider": "fastpath", "max_fastpath_latency_ms": 50},
            "push_to_talk": {"enabled": False},
            "governance": {"default_tier": "elevated"},
        },
    )
    res = _run("-o", "text", "voice", "status")
    assert res.exit_code == 0, res.output
    assert "Voice Subsystem Status" in res.output


@pytest.mark.parametrize(
    "data, code, fragment",
    [
        ({"blocked": True, "rejection_reason": "guest tier"}, 1, "Blocked"),
        (
            {
                "duration_ms": 3.2,
                "action": {
                    "intent": "cli_command",
                    "transcript": "hath0r doctor",
                    "confidence": 0.9,
                    "payload": {"command": "hath0r doctor", "target": "x", "feedback_text": "Running"},
                },
            },
            0,
            "Voice Action Resolved",
        ),
    ],
)
def test_voice_exec_text(monkeypatch, data, code, fragment):
    monkeypatch.setattr(voice_mod, "evaluate_and_dispatch_voice", lambda **kw: (data, [], "ok"))
    res = _run("-o", "text", "voice", "exec", "hath0r doctor", "--dry-run")
    assert res.exit_code == code
    assert fragment in res.output


def test_voice_listen_text_and_json(monkeypatch):
    calls = iter(
        [
            ({"blocked": True, "rejection_reason": "nope"}, [], "ok"),
            ({"duration_ms": 1.0, "action": {"intent": "x", "payload": {"feedback_text": "done"}}}, [], "ok"),
        ]
    )
    monkeypatch.setattr(voice_mod, "evaluate_and_dispatch_voice", lambda **kw: next(calls))
    monkeypatch.setattr(voice_mod, "wait_for_push_to_talk_trigger", lambda *a, **k: True)
    res = _run(
        "-o", "text", "voice", "listen", "--push-to-talk", "--ask-key", "--max-utterances", "2",
        input="right ctrl\n\nhath0r doctor\n\nhath0r status\n",
    )
    assert res.exit_code == 0, res.output
    assert "Blocked" in res.output and "Dispatched" in res.output

    monkeypatch.setattr(
        voice_mod, "evaluate_and_dispatch_voice", lambda **kw: ({"action": {"intent": "x"}}, [], "ok")
    )
    res = _run("-o", "json", "voice", "listen", "--max-utterances", "1", input="hath0r doctor\n")
    assert json.loads(res.output)["data"]["captured_count"] == 1


class _Listener:
    def __init__(self, transcripts):
        self._t = iter(transcripts)

    def listen(self, **kw):
        return {"transcript": next(self._t, "")}


@pytest.mark.parametrize("mode", ["text", "json"])
def test_voice_converse(monkeypatch, mode):
    monkeypatch.setattr(voice_converse, "SpeechListenerBot", lambda **k: _Listener(["status please", "bye"]))
    _patch(monkeypatch, voice_converse, "AgentDialogueBot", {"response_text": "All green."})
    _patch(monkeypatch, voice_converse, "VoiceSynthesizerBot", {"success": True})
    res = _run("-o", mode, "voice", "converse", "--max-turns", "3")
    assert res.exit_code == 0, res.output
    if mode == "json":
        assert json.loads(res.output)["data"]["turns_count"] == 1
    else:
        assert "All green." in res.output and "Conversation ended" in res.output


def test_voice_meeting(monkeypatch):
    _patch(monkeypatch, voice_converse, "ProactiveSpeakerBot", {"spoken": True})
    res = _run("-o", "json", "voice", "meeting", "--mode", "review")
    assert json.loads(res.output)["data"]["mode"] == "review"


def test_voice_engine_list_text(monkeypatch):
    _patch(
        monkeypatch,
        voice_speaker,
        "LocalNeuralVoiceEngine",
        Seq([
            [{"id": "coreml-82m", "type": "neural", "available": True, "description": "d"},
             {"id": "say", "type": "platform", "available": False, "description": "d"}],
            {"models_dir": "/models"},
        ]),
    )
    res = _run("-o", "text", "voice", "engine", "list")
    assert res.exit_code == 0, res.output
    assert "/models" in res.output


def test_voice_list_voices_text(monkeypatch):
    import hath0r_cli.voice_kokoro as kokoro

    voices = [{"id": "af", "name": "Bella", "gender": "f", "accent": "us", "description": "warm"}]
    _patch(monkeypatch, kokoro, "KokoroTTSEngine", voices)
    res = _run("-o", "text", "voice", "list-voices")
    assert res.exit_code == 0, res.output
    assert "Bella" in res.output
