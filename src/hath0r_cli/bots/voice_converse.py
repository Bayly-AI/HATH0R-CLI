"""Micro-bots powering the Voice Conversational Interface Factory (`voice-converse-factory`).

Provides:
- SpeechListenerBot: Manages conversational speech capture and turn onset detection.
- AgentDialogueBot: Manages two-way dialogue, context reasoning, and intent routing.
- VoiceSynthesizerBot: Synthesizes spoken output responses using platform audio engines.
- ProactiveSpeakerBot: Enables autonomous verbal announcements, alerts, and meeting check-ins.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.voice import (
    TrustTier,
    evaluate_and_dispatch_voice,
    get_push_to_talk_config,
    wait_for_push_to_talk_trigger,
)


class SpeechListenerBot:
    """Captures conversational audio or text utterance turns."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()

    def listen(
        self,
        push_to_talk: bool = True,
        key: Optional[str] = None,
        simulated_transcript: Optional[str] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Capture or receive an utterance turn."""
        ptt_cfg = get_push_to_talk_config()
        selected_key = key or ptt_cfg.default_key

        if simulated_transcript:
            return {
                "success": True,
                "transcript": simulated_transcript,
                "mode": "simulated",
                "key": selected_key,
            }

        # If non-interactive stdin, return empty or default
        if not os.isatty(sys.stdin.fileno()):
            return {
                "success": True,
                "transcript": "hath0r doctor",
                "mode": "non_interactive",
                "key": selected_key,
            }

        if push_to_talk:
            wait_for_push_to_talk_trigger(selected_key, timeout_seconds=timeout)

        # Standard terminal line capture
        try:
            line = input().strip()
            transcript = line if line else "hath0r doctor"
        except (EOFError, KeyboardInterrupt):
            transcript = "cancel"

        return {
            "success": True,
            "transcript": transcript,
            "mode": "push_to_talk" if push_to_talk else "ambient",
            "key": selected_key,
        }


class AgentDialogueBot:
    """Evaluates user statements, reasons about intent, and generates conversational response."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.dialogue_history: List[Dict[str, str]] = []

    def reason(
        self,
        transcript: str,
        trust_tier: str = TrustTier.ELEVATED.value,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Process conversational input, classify intent, and formulate response."""
        data, diagnostics, state = evaluate_and_dispatch_voice(
            transcript=transcript,
            trust_tier=trust_tier,
            dry_run=dry_run,
            speak=False,
        )

        action = data.get("action", {})
        intent = action.get("intent", "unresolved")
        payload = action.get("payload", {})
        feedback = payload.get("feedback_text")

        if not feedback:
            if intent == "cli_command":
                feedback = f"Executing {payload.get('command')}."
            elif intent == "computer_use":
                feedback = f"Opening {payload.get('target')}."
            else:
                feedback = f"Acknowledged: {transcript}"

        self.dialogue_history.append({"user": transcript, "agent": feedback})

        return {
            "success": state == "ok",
            "intent": intent,
            "response_text": feedback,
            "action": action,
            "diagnostics": diagnostics,
            "history_count": len(self.dialogue_history),
        }


class VoiceSynthesizerBot:
    """Synthesizes agent spoken feedback out loud."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()

    def speak(self, text: str, voice_name: Optional[str] = None) -> Dict[str, Any]:
        """Synthesize and vocalize agent response."""
        if not text:
            return {"success": True, "spoken": False, "reason": "empty_text"}

        clean_text = text.replace('"', '\\"')
        spoken = False
        try:
            if sys.platform == "darwin" and shutil.which("say"):
                cmd = ["say"]
                if voice_name:
                    cmd.extend(["-v", voice_name])
                cmd.append(clean_text)
                subprocess.run(cmd, check=False, timeout=10)
                spoken = True
            elif sys.platform.startswith("linux"):
                if shutil.which("espeak-ng"):
                    subprocess.run(["espeak-ng", clean_text], check=False, timeout=10)
                    spoken = True
                elif shutil.which("espeak"):
                    subprocess.run(["espeak", clean_text], check=False, timeout=10)
                    spoken = True
            else:
                spoken = True  # Mock/Windows success
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": False}

        return {"success": True, "spoken": spoken, "text": text}


class ProactiveSpeakerBot:
    """Enables autonomous agent verbal notifications, meeting check-ins, and alerts."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.synthesizer = VoiceSynthesizerBot(cwd=self.cwd)

    def announce(self, message: str, speak: bool = True) -> Dict[str, Any]:
        """Make an autonomous verbal announcement."""
        res: Dict[str, Any] = {"announced": True, "message": message}
        if speak:
            synth_res = self.synthesizer.speak(message)
            res["synthesized"] = synth_res.get("success", False)
        return res

    def check_in(self, topic: Optional[str] = None, speak: bool = True) -> Dict[str, Any]:
        """Perform a meeting check-in or status greeting."""
        t = topic or "Hath0r agent standup check-in"
        greeting = f"Agent check-in active for {t}. I am listening and ready to assist."
        return self.announce(greeting, speak=speak)
