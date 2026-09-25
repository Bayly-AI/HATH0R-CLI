"""Unit and workflow tests for voice-converse-factory and micro-bots."""

from pathlib import Path

from hath0r_cli.bots.voice_converse import (
    AgentDialogueBot,
    ProactiveSpeakerBot,
    SpeechListenerBot,
    VoiceSynthesizerBot,
)
from hath0r_cli.factory_validation import validate_factory_file
from hath0r_cli.step_runner import BotRegistry, execute_workflow


def test_voice_converse_factory_manifest_valid():
    manifest_path = Path("cfg/factories/voice-converse-factory.yaml")
    res = validate_factory_file(manifest_path)
    assert res.valid is True
    assert len(res.errors) == 0


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
