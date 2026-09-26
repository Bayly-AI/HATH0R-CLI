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
        raw_bin = base_dir / "hath0r-listen"
        if raw_bin.is_file() and os.access(raw_bin, os.X_OK):
            return raw_bin
        app_bin = base_dir / "Hath0rListen.app" / "Contents" / "MacOS" / "hath0r-listen"
        if app_bin.is_file() and os.access(app_bin, os.X_OK):
            return app_bin
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

        # Attempt native microphone audio capture & STT
        listener_bin = self._find_listener_binary() if enable_microphone else None
        if listener_bin and sys.platform == "darwin":
            try:
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp:
                    tmp_audio_path = tmp.name

                print("  🎙️  Recording from microphone... (speak now)", flush=True)
                subprocess.run(
                    [str(listener_bin), str(min(timeout, 8.0)), tmp_audio_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout + 3.0,
                )
                captured = ""
                audio_file = Path(tmp_audio_path)
                if audio_file.is_file() and audio_file.stat().st_size > 500:
                    print("  ⚡ Transcribing audio...", flush=True)
                    captured = transcribe_audio(audio_file) or ""
                    audio_file.unlink(missing_ok=True)
                elif audio_file.is_file():
                    audio_file.unlink(missing_ok=True)

                if captured and captured.upper() not in ("EMPTY", "EMPTY."):
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
                "transcript": "",
                "mode": "non_interactive",
                "key": selected_key,
            }

        # Standard terminal line capture fallback
        try:
            transcript = input("You > ").strip()
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


def find_gemini_api_key() -> Optional[str]:
    """Locate Gemini API key from environment or standard credentials store."""
    for key_var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
        val = os.environ.get(key_var)
        if val and val.strip():
            return val.strip()

    # Search credentials store
    cred_paths = [
        Path.home() / "Development" / ".credentials" / "gemini" / ".env",
        Path.home() / "Development" / ".credentials" / "google" / ".env",
        Path.home() / ".credentials" / "gemini" / ".env",
        Path.home() / ".env",
    ]
    for p in cred_paths:
        if p.is_file():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"):
                            cleaned_v = v.strip().strip("'\"")
                            if cleaned_v:
                                return cleaned_v
            except Exception:
                pass
    return None


def transcribe_audio(audio_path: Path | str, timeout: float = 10.0) -> Optional[str]:
    """Transcribe spoken audio file directly using Google Gemini Multimodal Audio."""
    api_key = find_gemini_api_key()
    if not api_key:
        return None

    path = Path(audio_path)
    if not path.is_file() or path.stat().st_size < 100:
        return None

    import base64
    import json
    import urllib.request

    try:
        audio_bytes = path.read_bytes()
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        mime = "audio/mp4" if path.suffix.lower() in (".m4a", ".mp4", ".aac") else "audio/wav"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"inlineData": {"mimeType": mime, "data": b64_audio}},
                        {
                            "text": (
                                "Transcribe this spoken audio clip verbatim. "
                                "Output ONLY the exact words spoken by the user. "
                                "If the audio is silent, background noise, or contains no speech, respond with EMPTY."
                            )
                        },
                    ]
                }
            ]
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    transcript = str(parts[0]["text"]).strip()
                    if transcript.upper() in ("EMPTY", "EMPTY.", ""):
                        return None
                    return transcript
    except Exception:
        pass
    return None


def query_standalone_llm(
    prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
    timeout: float = 10.0,
) -> Optional[str]:
    """Query Google Gemini API directly for standalone voice conversation."""
    api_key = find_gemini_api_key()
    if not api_key:
        return None

    import json
    import urllib.request

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"

    system_instruction = (
        "You are Hath0r, an autonomous AI coding and system companion. "
        "The operator is speaking to you via two-way voice. "
        "Answer concisely in 1 to 3 natural spoken sentences. "
        "Never use markdown code blocks, backticks, asterisks, bullet points, or raw symbols, "
        "as your answer will be vocalized out loud via text-to-speech."
    )

    contents = []
    if history:
        for turn in history[-4:]:
            if "user" in turn and turn["user"]:
                contents.append({"role": "user", "parts": [{"text": turn["user"]}]})
            if "agent" in turn and turn["agent"]:
                contents.append({"role": "model", "parts": [{"text": turn["agent"]}]})

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 200,
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                candidates = body.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "").strip()
                        return filter_speech_text(raw_text)
    except Exception:
        try:
            url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            req = urllib.request.Request(
                url_fallback,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    body = json.loads(resp.read().decode("utf-8"))
                    candidates = body.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "").strip()
                            return filter_speech_text(raw_text)
        except Exception:
            pass
    return None


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
            cwd=self.cwd,
        )


        action = data.get("action", {})
        intent = action.get("intent", "unresolved")
        payload = action.get("payload", {})
        feedback = payload.get("feedback_text")

        # If delegated to agent reasoning and not dry-run, attempt standalone direct LLM call
        if intent == "agent_delegate" and not dry_run:
            llm_response = query_standalone_llm(prompt=transcript, history=self.dialogue_history)
            if llm_response:
                feedback = llm_response

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

    @property
    def launchd_plist_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / "ai.bayly.hath0r-voice.plist"

    @property
    def systemd_service_path(self) -> Path:
        return Path.home() / ".config" / "systemd" / "user" / "hath0r-voice.service"

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

    def install_os_service(
        self,
        ambient: bool = True,
        trust_tier: str = TrustTier.ELEVATED.value,
        speak: bool = False,
    ) -> Dict[str, Any]:
        """Install and register Hath0r voice daemon as a native OS service (launchd on macOS / systemd on Linux)."""
        cli_entry = sys.executable
        mode_flag = "--ambient" if ambient else "--push-to-talk"

        if sys.platform == "darwin":
            plist_path = self.launchd_plist_path
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.bayly.hath0r-voice</string>
    <key>ProgramArguments</key>
    <array>
        <string>{cli_entry}</string>
        <string>-m</string>
        <string>hath0r_cli.cli</string>
        <string>voice</string>
        <string>service</string>
        <string>start</string>
        <string>--foreground</string>
        <string>{mode_flag}</string>
        <string>--trust-tier</string>
        <string>{trust_tier}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{self.cwd}</string>
    <key>StandardOutPath</key>
    <string>{self.log_file}</string>
    <key>StandardErrorPath</key>
    <string>{self.log_file}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
            plist_path.write_text(plist_content, encoding="utf-8")
            try:
                subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True, check=False)
                res = subprocess.run(
                    ["launchctl", "load", "-w", str(plist_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                loaded = res.returncode == 0
            except Exception:
                loaded = True

            if speak:
                self.synthesizer.speak("Hath0r voice OS service installed.")
            return {
                "success": True,
                "platform": "darwin",
                "service_manager": "launchd",
                "plist_path": str(plist_path),
                "loaded": loaded,
                "message": f"Installed macOS LaunchAgent at {plist_path}",
            }

        elif sys.platform.startswith("linux"):
            service_path = self.systemd_service_path
            service_path.parent.mkdir(parents=True, exist_ok=True)
            service_content = f"""[Unit]
Description=HATH0R Voice Daemon Service
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory={self.cwd}
ExecStart={cli_entry} -m hath0r_cli.cli voice service start --foreground {mode_flag} --trust-tier {trust_tier}
Restart=always
RestartSec=3
StandardOutput=append:{self.log_file}
StandardError=append:{self.log_file}

[Install]
WantedBy=default.target
"""
            service_path.write_text(service_content, encoding="utf-8")
            try:
                subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=False)
                subprocess.run(
                    ["systemctl", "--user", "enable", "--now", "hath0r-voice"],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass
            if speak:
                self.synthesizer.speak("Hath0r voice OS service installed.")
            return {
                "success": True,
                "platform": "linux",
                "service_manager": "systemd",
                "service_path": str(service_path),
                "message": f"Installed systemd user service at {service_path}",
            }

        return {
            "success": False,
            "error": f"OS service installation not supported on platform {sys.platform}",
        }

    def uninstall_os_service(self, speak: bool = False) -> Dict[str, Any]:
        """Uninstall and unload the OS-level Hath0r voice service."""
        if sys.platform == "darwin":
            plist_path = self.launchd_plist_path
            if plist_path.is_file():
                try:
                    subprocess.run(["launchctl", "unload", "-w", str(plist_path)], capture_output=True, check=False)
                except Exception:
                    pass
                plist_path.unlink(missing_ok=True)
                if speak:
                    self.synthesizer.speak("Hath0r voice OS service uninstalled.")
                return {
                    "success": True,
                    "platform": "darwin",
                    "service_manager": "launchd",
                    "message": "Unloaded and removed macOS LaunchAgent.",
                }
            return {"success": True, "message": "No LaunchAgent was installed."}

        elif sys.platform.startswith("linux"):
            service_path = self.systemd_service_path
            if service_path.is_file():
                try:
                    subprocess.run(["systemctl", "--user", "stop", "hath0r-voice"], capture_output=True, check=False)
                    subprocess.run(["systemctl", "--user", "disable", "hath0r-voice"], capture_output=True, check=False)
                except Exception:
                    pass
                service_path.unlink(missing_ok=True)
                return {
                    "success": True,
                    "platform": "linux",
                    "service_manager": "systemd",
                    "message": "Stopped and removed systemd user service.",
                }
            return {"success": True, "message": "No systemd service was installed."}

        return {"success": False, "error": f"Unsupported platform {sys.platform}"}
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
