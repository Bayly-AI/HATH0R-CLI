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


def test_voice_speaker_mode_bot_tab_scoping(tmp_path: Path):
    from hath0r_cli.bots.voice_speaker import VoiceSpeakerModeBot

    bot = VoiceSpeakerModeBot(cwd=tmp_path)
    current_tab = bot.get_current_tab_id()
    assert current_tab is not None

    # Enable with tab_only=True
    en_res = bot.enable(tab_only=True, speak=False)
    assert en_res["enabled"] is True
    assert en_res["scope"] == "tab"
    assert en_res["tab_id"] == current_tab

    # Status check
    st = bot.status()
    assert st["enabled"] is True
    assert st["scope"] == "tab"
    assert st["saved_tab"] == current_tab

    # Verify is_enabled() in matching tab
    assert bot.is_enabled() is True



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


def test_voice_profile_bot_lifecycle(tmp_path: Path):
    from hath0r_cli.bots.voice_speaker import VoiceProfileBot

    bot = VoiceProfileBot(cwd=tmp_path)
    # List profiles
    profiles_res = bot.list_profiles()
    assert profiles_res["success"] is True
    assert "voices" in profiles_res
    assert isinstance(profiles_res["voices"], list)

    # Get active profile (default Samantha)
    active = bot.get_active_profile()
    assert active["voice_name"] == "Samantha"

    # Set new profile (e.g. Daniel with rate 190)
    set_res = bot.set_profile("Daniel", rate_wpm=190, preview=False, dry_run=False)
    assert set_res["success"] is True
    assert set_res["voice_name"] == "Daniel"
    assert set_res["rate_wpm"] == 190

    # Verify active profile is now Daniel
    active_now = bot.get_active_profile()
    assert active_now["voice_name"] == "Daniel"
    assert active_now["rate_wpm"] == 190



def test_workflow_voice_profiles(tmp_path: Path):
    registry = BotRegistry(cwd=tmp_path)
    # Test list workflow
    wf_list = {
        "id": "list-voice-profiles",
        "name": "List Voice Profiles Workflow",
        "steps": [
            {
                "bot": "voice-profile-bot",
                "action": "list-profiles",
                "args": {},
                "on_failure": "abort",
            }
        ],
    }
    res_list = execute_workflow(wf_list, registry=registry, dry_run=True)
    assert res_list.success is True
    assert "voices" in res_list.steps[0].data

    # Test set workflow
    wf_set = {
        "id": "set-voice-profile",
        "name": "Set Voice Profile Workflow",
        "steps": [
            {
                "bot": "voice-profile-bot",
                "action": "set-profile",
                "args": {"voice_name": "Karen", "rate_wpm": 185, "preview": False},
                "on_failure": "abort",
            }
        ],
    }
    res_set = execute_workflow(wf_set, registry=registry, dry_run=True)
    assert res_set.success is True
    assert res_set.steps[0].data["voice_name"] == "Karen"


def test_active_tab_reader_bot(tmp_path: Path):
    from hath0r_cli.bots.voice_speaker import ActiveTabReaderBot

    bot = ActiveTabReaderBot(cwd=tmp_path)
    # Check frontmost app detection (returns non-empty string or 'system'/'Unknown')
    app = bot.get_frontmost_app()
    assert isinstance(app, str)
    assert len(app) > 0

    # Read text with dry run
    sample_text = "# Current Status\n\n```python\nprint('code')\n```\nAll unit tests passed successfully."
    res = bot.read_text(sample_text, dry_run=True)
    assert res["success"] is True
    assert res["dry_run"] is True
    assert "All unit tests passed successfully." in res["spoken_text"]
    assert "```" not in res["spoken_text"]


def test_workflow_voice_read_active_tab(tmp_path: Path):
    registry = BotRegistry(cwd=tmp_path)
    wf_read = {
        "id": "voice-read-active-tab",
        "name": "Voice Read Active Tab Workflow",
        "steps": [
            {
                "bot": "active-tab-reader-bot",
                "action": "read-text",
                "args": {"text": "Agent response from active tab ready."},
                "on_failure": "continue",
            }
        ],
    }
    res_wf = execute_workflow(wf_read, registry=registry, dry_run=True)
    assert res_wf.success is True
    assert res_wf.steps[0].data["spoken_text"] == "Agent response from active tab ready."


def test_interpret_response_for_speech():
    from hath0r_cli.bots.voice_speaker import interpret_response_for_speech

    # 1. Issue list interpretation
    t1 = interpret_response_for_speech("issue.list", "ok", {"total_count": 5, "repo_count": 16})
    assert "Found 5 active issues across 16 repositories" in t1

    # 2. Quality gate interpretation
    t2 = interpret_response_for_speech("quality.check", "ok", {"passed": True})
    assert "Quality gates passed successfully." in t2

    # 3. Doctor interpretation
    t3 = interpret_response_for_speech("doctor", "ok", {})
    assert "doctor check completed" in t3

    # 4. Explicit message override with code block filtering
    t4 = interpret_response_for_speech("any.command", "ok", {"message": "Summary: ```sh\nls\n``` All good."})
    assert "Summary: All good." in t4
    assert "```" not in t4

    # 5. Task start receipt confirmation
    t5 = interpret_response_for_speech(
        "task.start",
        "ok",
        {
            "workflow": {
                "steps": [
                    {"data": {"issue_number": 151, "open": True}},
                    {"data": {"branch": "feature/151-voice-speaker"}},
                ]
            }
        },
    )
    assert "Task receipt confirmed for Issue #151" in t5
    assert "feature/151-voice-speaker" in t5





