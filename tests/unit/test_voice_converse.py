"""Unit and workflow tests for voice-converse-factory and micro-bots."""

from pathlib import Path

from hath0r_cli.bots.voice_converse import (
    AgentDialogueBot,
    ProactiveSpeakerBot,
    SpeechListenerBot,
    VoiceServiceDaemonBot,
    VoiceSynthesizerBot,
    filter_speech_text,
)
from hath0r_cli.factory_validation import validate_factory_file
from hath0r_cli.step_runner import BotRegistry, execute_workflow


def test_voice_converse_factory_manifest_valid():
    manifest_path = Path("cfg/factories/voice-converse-factory.yaml")
    res = validate_factory_file(manifest_path)
    assert res.valid is True
    assert len(res.errors) == 0


def test_filter_speech_text():
    # Test stripping markdown code blocks
    markdown_with_code = """
Here is the solution to your issue:
```python
def calculate_sum(a, b):
    return a + b
```
Let me know if you need anything else!
"""
    spoken = filter_speech_text(markdown_with_code)
    assert "def calculate_sum" not in spoken
    assert "Here is the solution to your issue:" in spoken
    assert "Let me know if you need anything else!" in spoken

    # Test stripping markdown headers, bullet points, links, and inline code
    markdown_complex = """
### System Diagnostics
* Check status at [docs](https://antigravity.google)
* Run `hath0r doctor` to verify paths.
"""
    spoken2 = filter_speech_text(markdown_complex)
    assert "###" not in spoken2
    assert "https://" not in spoken2
    assert "Check status at docs" in spoken2
    assert "Run hath0r doctor to verify paths." in spoken2

    # Test pure code block fallback
    pure_code = "```\nimport os\nos.listdir()\n```"
    spoken_fallback = filter_speech_text(pure_code)
    assert spoken_fallback == "I have completed the requested operation."


def test_voice_synthesizer_bot_filter_code():
    synth = VoiceSynthesizerBot()
    res = synth.speak("```python\nprint('hello')\n```\nAll systems operational.")
    assert res["success"] is True
    assert "print('hello')" not in res["text"]
    assert "All systems operational." in res["text"]


def test_voice_service_daemon_bot_lifecycle(tmp_path: Path):
    bot = VoiceServiceDaemonBot(cwd=tmp_path)
    # Status before starting
    st1 = bot.status()
    assert st1["running"] is False

    # Start foreground with max_iterations=1 (simulated)
    loop_res = bot.run_service_loop(ambient=True, max_iterations=1)
    assert loop_res["success"] is True
    assert loop_res["iterations"] == 1

    # Check status after loop
    st2 = bot.status()
    assert st2["running"] is False


def test_voice_service_daemon_stop_when_not_running(tmp_path: Path):
    bot = VoiceServiceDaemonBot(cwd=tmp_path)
    res = bot.stop_service()
    assert res["success"] is True
    assert res["status"] == "not_running"


def test_workflow_voice_daemon_service_dry_run():
    registry = BotRegistry()
    wf_def = {
        "id": "voice-daemon-service",
        "name": "Autonomous Background Voice Daemon Service",
        "steps": [
            {
                "bot": "voice-service-daemon-bot",
                "action": "start-service",
                "args": {"background": True, "ambient": True},
                "on_failure": "continue",
            }
        ],
    }
    wf_res = execute_workflow(wf_def, registry=registry, dry_run=True)
    assert wf_res.success is True
    assert len(wf_res.steps) == 1
    assert wf_res.steps[0].data["status"] == "dry_run_started"


def test_speech_listener_bot_simulated(tmp_path: Path):
    bot = SpeechListenerBot(cwd=tmp_path)
    res = bot.listen(simulated_transcript="hath0r status")
    assert res["success"] is True
    assert res["transcript"] == "hath0r status"
    assert res["mode"] == "simulated"


def test_agent_dialogue_bot_reason(tmp_path: Path):
    bot = AgentDialogueBot(cwd=tmp_path)
    res = bot.reason(transcript="hath0r version", dry_run=True)
    assert res["success"] is True
    assert res["intent"] == "cli_command"
    assert "version" in res["response_text"].lower()
    assert res["history_count"] == 1


def test_voice_synthesizer_bot_empty():
    synth = VoiceSynthesizerBot()
    res = synth.speak("")
    assert res["success"] is True
    assert res["spoken"] is False


def test_proactive_speaker_bot_announce():
    speaker = ProactiveSpeakerBot()
    res = speaker.announce("Task finished successfully", speak=False)
    assert res["announced"] is True
    assert res["message"] == "Task finished successfully"


def test_proactive_speaker_bot_checkin():
    speaker = ProactiveSpeakerBot()
    res = speaker.check_in(topic="Sprint Planning", speak=False)
    assert res["announced"] is True
    assert "Sprint Planning" in res["message"]


def test_workflow_proactive_announcement_dry_run():
    registry = BotRegistry()
    wf_def = {
        "id": "proactive-announcement",
        "name": "Proactive Task Announcement",
        "steps": [
            {
                "bot": "proactive-speaker-bot",
                "action": "announce",
                "args": {"message": "All unit tests passed."},
                "on_failure": "continue",
            }
        ],
    }
    wf_res = execute_workflow(wf_def, registry=registry, dry_run=True)
    assert wf_res.success is True
    assert len(wf_res.steps) == 1
    assert wf_res.steps[0].data["announced"] is True


def test_speech_listener_bot_binary_discovery(tmp_path: Path):
    bot = SpeechListenerBot(cwd=tmp_path)
    bin_path = bot._find_listener_binary()
    if bin_path is not None:
        assert bin_path.is_file()


def test_find_gemini_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_12345")
    from hath0r_cli.bots.voice_converse import find_gemini_api_key

    key = find_gemini_api_key()
    assert key == "test_key_12345"


def test_query_standalone_llm_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_AI_API_KEY", raising=False)
    from hath0r_cli.bots.voice_converse import query_standalone_llm

    res = query_standalone_llm("What is Hathor?")
    # Without real key in mocked unit test, gracefully returns None
    assert res is None or isinstance(res, str)


def test_os_service_plist_generation(tmp_path: Path, monkeypatch):
    bot = VoiceServiceDaemonBot(cwd=tmp_path)
    # Redirect LaunchAgents path to tmp_path
    monkeypatch.setattr(
        VoiceServiceDaemonBot,
        "launchd_plist_path",
        property(lambda self: tmp_path / "ai.bayly.hath0r-voice.plist"),
    )
    res = bot.install_os_service(ambient=True)
    assert res["success"] is True
    assert (tmp_path / "ai.bayly.hath0r-voice.plist").is_file()

    un_res = bot.uninstall_os_service()
    assert un_res["success"] is True
    assert not (tmp_path / "ai.bayly.hath0r-voice.plist").is_file()




