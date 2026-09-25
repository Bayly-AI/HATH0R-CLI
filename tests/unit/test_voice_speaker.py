"""Unit and workflow tests for Phase 1 Voice Speaker and Spoken Notifications."""

from pathlib import Path

from hath0r_cli.bots.voice_speaker import (
    SpokenNotificationServiceBot,
    VoiceSpeakerBot,
    filter_speech_text,
)
from hath0r_cli.factory_validation import validate_factory_file
from hath0r_cli.step_runner import BotRegistry, execute_workflow


def test_voice_speaker_factory_manifest_valid():
    manifest_path = Path("cfg/factories/voice-speaker-factory.yaml")
    res = validate_factory_file(manifest_path)
    assert res.valid is True
    assert len(res.errors) == 0


def test_filter_speech_text_cleaner():
    raw_markdown = """
Here is the summary of your task:
```python
def example():
    return 42
```
* Status: `PASS`
* Documentation at [link](https://hath0r.dev)
| Column 1 | Column 2 |
| --- | --- |
| Data | 100 |
"""
    filtered = filter_speech_text(raw_markdown)
    assert "def example" not in filtered
    assert "```" not in filtered
    assert "https://" not in filtered
    assert "| Column" not in filtered
    assert "Here is the summary of your task:" in filtered
    assert "Status: PASS" in filtered


def test_voice_speaker_bot_speak_dry_run():
    speaker = VoiceSpeakerBot()
    res = speaker.speak("All integration tests have passed.", dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert res["text"] == "All integration tests have passed."


def test_voice_speaker_bot_announce_task_status():
    speaker = VoiceSpeakerBot()
    res = speaker.announce_task_status(
        task_name="PR Validation",
        status="completed",
        details="```python\ncode\n``` All 10 quality checks passed.",
        dry_run=True,
    )
    assert res["success"] is True
    assert res["dry_run"] is True
    assert "Task PR Validation completed successfully." in res["text"]
    assert "All 10 quality checks passed." in res["text"]
    assert "```" not in res["text"]


def test_spoken_notification_service_queue_and_drain(tmp_path: Path):
    bot = SpokenNotificationServiceBot(cwd=tmp_path)
    # Queue two messages
    q1 = bot.queue_message("First announcement", priority="high")
    assert q1["success"] is True
    assert q1["queued"] is True

    q2 = bot.queue_message("Second announcement", priority="normal")
    assert q2["success"] is True

    st = bot.status()
    assert st["running"] is False
    assert st["pending_count"] == 2

    # Drain queue
    drained = bot.drain_queue(dry_run=True)
    assert len(drained) == 2
    assert drained[0]["record"]["message"] == "First announcement"
    assert drained[1]["record"]["message"] == "Second announcement"

    # Queue should now be empty
    assert bot.status()["pending_count"] == 0


def test_spoken_notification_service_daemon_status_and_stop(tmp_path: Path):
    bot = SpokenNotificationServiceBot(cwd=tmp_path)
    st = bot.status()
    assert st["running"] is False

    stop_res = bot.stop_daemon()
    assert stop_res["success"] is True
    assert stop_res["status"] == "not_running"


def test_workflow_voice_speak_message_dry_run():
    registry = BotRegistry()
    wf_def = {
        "id": "voice-speak-message",
        "name": "Voice Speak Message Workflow",
        "steps": [
            {
                "bot": "voice-speaker-bot",
                "action": "speak",
                "args": {"text": "Phase 1 speaker bot is operational."},
                "on_failure": "continue",
            }
        ],
    }
    wf_res = execute_workflow(wf_def, registry=registry, dry_run=True)
    assert wf_res.success is True
    assert len(wf_res.steps) == 1
    assert wf_res.steps[0].data["dry_run"] is True
    assert wf_res.steps[0].data["text"] == "Phase 1 speaker bot is operational."


def test_workflow_voice_task_announcement_dry_run():
    registry = BotRegistry()
    wf_def = {
        "id": "voice-task-announcement",
        "name": "Voice Task Announcement Workflow",
        "steps": [
            {
                "bot": "voice-speaker-bot",
                "action": "announce-task-status",
                "args": {"task_name": "Build Pipeline", "status": "passed"},
                "on_failure": "continue",
            }
        ],
    }
    wf_res = execute_workflow(wf_def, registry=registry, dry_run=True)
    assert wf_res.success is True
    assert len(wf_res.steps) == 1
    assert "All checks for Build Pipeline have passed." in wf_res.steps[0].data["text"]


def test_voice_speaker_mode_bot_lifecycle(tmp_path: Path):
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

    bot = VoiceSpeakerModeBot(cwd=tmp_path)
    # Default is disabled
    assert bot.is_enabled() is False

    # Enable
    en_res = bot.enable(speak=False)
    assert en_res["success"] is True
    assert en_res["enabled"] is True
    assert bot.is_enabled() is True

    # Vocalize response summary
    voc_res = bot.vocalize_response("doctor", "ok", {"message": "All checks passed."}, dry_run=True)
    assert voc_res is not None
    assert voc_res["dry_run"] is True
    assert "All checks passed." in voc_res["text"]

    # Toggle to disable
    tog_res = bot.toggle(speak=False)
    assert tog_res["enabled"] is False
    assert bot.is_enabled() is False

    # Disable explicitly
    dis_res = bot.disable(speak=False)
    assert dis_res["enabled"] is False


def test_workflow_enable_disable_speak_mode():
    registry = BotRegistry()
    wf_on = {
        "id": "enable-speak-mode",
        "name": "Enable Global Spoken Feedback Mode",
        "steps": [
            {
                "bot": "voice-speaker-mode-bot",
                "action": "enable",
                "args": {"speak": False},
                "on_failure": "abort",
            }
        ],
    }
    res_on = execute_workflow(wf_on, registry=registry, dry_run=True)
    assert res_on.success is True
    assert res_on.steps[0].data["enabled"] is True

    wf_off = {
        "id": "disable-speak-mode",
        "name": "Disable Global Spoken Feedback Mode",
        "steps": [
            {
                "bot": "voice-speaker-mode-bot",
                "action": "disable",
                "args": {"speak": False},
                "on_failure": "abort",
            }
        ],
    }
    res_off = execute_workflow(wf_off, registry=registry, dry_run=True)
    assert res_off.success is True
    assert res_off.steps[0].data["enabled"] is False

