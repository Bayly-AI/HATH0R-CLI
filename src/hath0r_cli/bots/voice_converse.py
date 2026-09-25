"""Micro-bots powering the Voice Conversational Interface Factory (`voice-converse-factory`).

Provides:
- SpeechListenerBot: Manages conversational speech capture and turn onset detection.
- AgentDialogueBot: Manages two-way dialogue, context reasoning, and intent routing.
- VoiceSynthesizerBot: Synthesizes spoken output responses using platform audio engines.
- ProactiveSpeakerBot: Enables autonomous verbal announcements, alerts, and meeting check-ins.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

    def _find_listener_binary(self) -> Optional[Path]:
        """Locate native hath0r-listen executable if present."""
        base_dir = Path(__file__).resolve().parent.parent / "bin"
        app_bin = base_dir / "Hath0rListen.app" / "Contents" / "MacOS" / "hath0r-listen"
        if app_bin.is_file() and os.access(app_bin, os.X_OK):
            return app_bin
        raw_bin = base_dir / "hath0r-listen"
        if raw_bin.is_file() and os.access(raw_bin, os.X_OK):
            return raw_bin
        return None

    def listen(
        self,
        push_to_talk: bool = True,
        key: Optional[str] = None,
        simulated_transcript: Optional[str] = None,
        timeout: float = 30.0,
        enable_microphone: bool = True,
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

        if push_to_talk:
            wait_for_push_to_talk_trigger(selected_key, timeout_seconds=timeout)

        # Attempt native microphone STT if on macOS Darwin and binary available
        listener_bin = self._find_listener_binary() if enable_microphone else None
        if listener_bin and sys.platform == "darwin":
            try:
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                    tmp_path = tmp.name

                proc = subprocess.run(
                    [str(listener_bin), str(min(timeout, 12.0)), tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout + 2.0,
                )
                captured = ""
                if Path(tmp_path).is_file():
                    try:
                        captured = Path(tmp_path).read_text(encoding="utf-8").strip()
                        Path(tmp_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                if not captured and proc.stdout:
                    captured = proc.stdout.strip()

                if captured:
                    return {
                        "success": True,
                        "transcript": captured,
                        "mode": "microphone_native",
                        "key": selected_key,
                    }
            except Exception:
                pass

        # Check if stdin is a tty
        is_tty = False
        try:
            is_tty = bool(hasattr(sys.stdin, "isatty") and sys.stdin.isatty())
        except Exception:
            is_tty = False

        if not is_tty:
            return {
                "success": True,
                "transcript": "hath0r doctor",
                "mode": "non_interactive",
                "key": selected_key,
            }

        # Standard terminal line capture fallback
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


def filter_speech_text(text: str) -> str:
    """Filter out code blocks, diffs, markdown formatting, and raw syntax.

    Ensures the speech synthesizer speaks only natural spoken language, summaries,
    and conversational lines without reading curly braces, code lines, or symbols.
    """
    if not text:
        return ""

    # Remove triple-backtick code blocks (e.g. ```python\n...\n```)
    cleaned = re.sub(r"```[\s\S]*?```", "", text)

    # Remove inline code backticks (e.g. `foo()`)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # Remove markdown link URLs (e.g. [title](url) -> title)
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)

    # Remove markdown headers (#, ##, etc)
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)

    # Remove markdown table rows and borders (e.g. | --- | --- |)
    cleaned = re.sub(r"\|.*\|", "", cleaned)

    # Remove markdown list bullets (*, -, + or 1.) at line starts
    cleaned = re.sub(r"^[\s]*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^[\s]*\d+\.\s+", "", cleaned, flags=re.MULTILINE)

    # Remove bold/italic markers (* or _)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)

    # Remove horizontal rules
    cleaned = re.sub(r"^[-=_]{3,}\s*$", "", cleaned, flags=re.MULTILINE)

    # Normalize whitespace and newlines
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    spoken_summary = " ".join(lines)
    spoken_summary = re.sub(r"\s+", " ", spoken_summary).strip()

    # If completely empty after code removal (e.g. agent produced only code)
    if not spoken_summary:
        return "I have completed the requested operation."

    return spoken_summary


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

    def speak(
        self,
        text: str,
        voice_name: Optional[str] = None,
        filter_code: bool = True,
    ) -> Dict[str, Any]:
        """Synthesize and vocalize agent response."""
        if not text:
            return {"success": True, "spoken": False, "reason": "empty_text"}

        spoken_text = filter_speech_text(text) if filter_code else text
        if not spoken_text:
            return {"success": True, "spoken": False, "reason": "empty_filtered_text"}

        clean_text = spoken_text.replace('"', '\\"')
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

        return {"success": True, "spoken": spoken, "text": spoken_text, "raw_text": text}


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


class VoiceServiceDaemonBot:
    """Manages background/daemon voice listening and conversational response service."""

    def __init__(self, cwd: Optional[Path] = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.state_dir = self.cwd / ".hath0r"
        self.pid_file = self.state_dir / "voice-daemon.pid"
        self.log_file = self.state_dir / "voice-daemon.log"
        self.listener = SpeechListenerBot(cwd=self.cwd)
        self.dialogue = AgentDialogueBot(cwd=self.cwd)
        self.synthesizer = VoiceSynthesizerBot(cwd=self.cwd)

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """Check if daemon process is currently active."""
        if not self.pid_file.is_file():
            return False, None
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            # Check if process is running (signal 0 doesn't kill)
            os.kill(pid, 0)
            return True, pid
        except (OSError, ValueError):
            # Stale PID file
            self.pid_file.unlink(missing_ok=True)
            return False, None

    def start_service(
        self,
        background: bool = True,
        ambient: bool = True,
        trust_tier: str = TrustTier.ELEVATED.value,
    ) -> Dict[str, Any]:
        """Start the voice listener service in background or foreground."""
        running, existing_pid = self.is_running()
        if running and existing_pid != os.getpid():
            return {
                "success": True,
                "status": "already_running",
                "pid": existing_pid,
                "message": f"Voice daemon service is already running (PID: {existing_pid}).",
            }

        self.state_dir.mkdir(parents=True, exist_ok=True)

        if background:
            cmd = [
                sys.executable,
                "-m",
                "hath0r_cli.cli",
                "voice",
                "service",
                "start",
                "--foreground",
            ]
            if ambient:
                cmd.append("--ambient")
            else:
                cmd.append("--push-to-talk")
            cmd.extend(["--trust-tier", trust_tier])

            with open(self.log_file, "a", encoding="utf-8") as log_f:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.cwd),
                    stdout=log_f,
                    stderr=log_f,
                    start_new_session=True,
                )
            self.pid_file.write_text(str(proc.pid), encoding="utf-8")
            self.synthesizer.speak("Voice daemon service started in background.")
            return {
                "success": True,
                "status": "started",
                "pid": proc.pid,
                "background": True,
                "ambient": ambient,
                "trust_tier": trust_tier,
                "log_file": str(self.log_file),
                "message": f"Voice daemon service started in background (PID: {proc.pid}).",
            }

        return self.run_service_loop(ambient=ambient, trust_tier=trust_tier)

    def stop_service(self) -> Dict[str, Any]:
        """Stop active background daemon."""
        running, pid = self.is_running()
        if not running or pid is None:
            return {
                "success": True,
                "status": "not_running",
                "message": "Voice daemon service is not currently running.",
            }

        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
            if self.is_running()[0]:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

        self.pid_file.unlink(missing_ok=True)
        self.synthesizer.speak("Voice daemon service stopped.")
        return {
            "success": True,
            "status": "stopped",
            "pid": pid,
            "message": f"Voice daemon service (PID: {pid}) stopped.",
        }

    def status(self) -> Dict[str, Any]:
        """Inspect service status."""
        running, pid = self.is_running()
        return {
            "running": running,
            "pid": pid,
            "status": "running" if running else "stopped",
            "log_file": str(self.log_file) if self.log_file.is_file() else None,
            "pid_file": str(self.pid_file),
        }

    def run_service_loop(
        self,
        ambient: bool = True,
        trust_tier: str = TrustTier.ELEVATED.value,
        max_iterations: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Continuous service loop processing voice statements."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")
        self.synthesizer.speak("Voice service online and listening.")

        iterations = 0
        processed_turns = []

        try:
            while max_iterations is None or iterations < max_iterations:
                iterations += 1
                listen_res = self.listener.listen(
                    push_to_talk=not ambient,
                    timeout=15.0,
                    enable_microphone=True,
                )
                transcript = listen_res.get("transcript", "").strip()
                mode = listen_res.get("mode")

                if not transcript or transcript.lower() in ("cancel", "empty"):
                    time.sleep(0.5)
                    continue

                if transcript.lower() in (
                    "shutdown voice",
                    "stop voice service",
                    "kill service",
                    "exit voice",
                    "stop listening",
                ):
                    self.synthesizer.speak("Stopping voice service.")
                    break

                reason_res = self.dialogue.reason(
                    transcript=transcript,
                    trust_tier=trust_tier,
                )
                response_text = reason_res.get("response_text", "")
                if response_text:
                    self.synthesizer.speak(response_text, filter_code=True)

                processed_turns.append(
                    {
                        "transcript": transcript,
                        "response": response_text,
                        "intent": reason_res.get("intent"),
                    }
                )

                # If non-interactive mode without microphone, back off to avoid busy spinning
                if mode == "non_interactive":
                    time.sleep(2.0)
        finally:
            self.pid_file.unlink(missing_ok=True)

        return {
            "success": True,
            "iterations": iterations,
            "turns_processed": len(processed_turns),
            "turns": processed_turns,
        }
