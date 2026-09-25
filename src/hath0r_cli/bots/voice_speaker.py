"""Dedicated Voice Speaker and Spoken Notification Service Bots for Hath0r.

Phase 1 (Agent Speech Output):
- VoiceSpeakerBot: Vocalizes messages, notifications, and summaries with markdown/code filtering.
- SpokenNotificationServiceBot: Manages asynchronous spool-driven voice announcements.
- filter_speech_text: Natural language cleaner removing raw code, diffs, tables, and markup.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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


@dataclass
class VoiceSpeakerBot:
    """Synthesizes agent spoken feedback out loud via system speech engines."""

    cwd: Path = field(default_factory=Path.cwd)

    def speak(
        self,
        text: str,
        voice_name: Optional[str] = None,
        rate_wpm: Optional[int] = None,
        filter_code: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Synthesize and vocalize text response."""
        if not text:
            return {"success": True, "spoken": False, "reason": "empty_text", "text": ""}

        spoken_text = filter_speech_text(text) if filter_code else text
        if not spoken_text:
            return {"success": True, "spoken": False, "reason": "empty_filtered_text", "text": ""}

        if dry_run:
            return {
                "success": True,
                "spoken": False,
                "dry_run": True,
                "text": spoken_text,
                "engine": "simulated",
            }

        clean_text = spoken_text.replace('"', '\\"')
        spoken = False
        engine_used = "none"

        try:
            if sys.platform == "darwin" and shutil.which("say"):
                cmd = ["say"]
                if voice_name:
                    cmd.extend(["-v", voice_name])
                if rate_wpm:
                    cmd.extend(["-r", str(rate_wpm)])
                cmd.append(clean_text)
                subprocess.run(cmd, check=False, timeout=12)
                spoken = True
                engine_used = "macos_say"
            elif sys.platform.startswith("linux"):
                if shutil.which("espeak-ng"):
                    cmd = ["espeak-ng"]
                    if voice_name:
                        cmd.extend(["-v", voice_name])
                    if rate_wpm:
                        cmd.extend(["-s", str(rate_wpm)])
                    cmd.append(clean_text)
                    subprocess.run(cmd, check=False, timeout=12)
                    spoken = True
                    engine_used = "espeak_ng"
                elif shutil.which("espeak"):
                    cmd = ["espeak"]
                    if voice_name:
                        cmd.extend(["-v", voice_name])
                    if rate_wpm:
                        cmd.extend(["-s", str(rate_wpm)])
                    cmd.append(clean_text)
                    subprocess.run(cmd, check=False, timeout=12)
                    spoken = True
                    engine_used = "espeak"
        except Exception as exc:
            return {"success": False, "spoken": False, "error": str(exc), "text": spoken_text}

        return {
            "success": True,
            "spoken": spoken,
            "engine": engine_used,
            "text": spoken_text,
        }

    def announce_task_status(
        self,
        task_name: str,
        status: str = "completed",
        details: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Announce lifecycle task status out loud."""
        status_map = {
            "started": f"Task {task_name} has started.",
            "completed": f"Task {task_name} completed successfully.",
            "passed": f"All checks for {task_name} have passed.",
            "failed": f"Warning: Task {task_name} encountered an error.",
            "blocked": f"Task {task_name} is blocked and requires operator review.",
        }
        base_msg = status_map.get(status.lower(), f"Task {task_name} status is {status}.")
        if details:
            clean_details = filter_speech_text(details)
            full_msg = f"{base_msg} {clean_details}"
        else:
            full_msg = base_msg

        return self.speak(full_msg, filter_code=False, dry_run=dry_run)


@dataclass
class SpokenNotificationServiceBot:
    """Manages asynchronous voice announcement queues and background speaker worker."""

    cwd: Path = field(default_factory=Path.cwd)
    speaker: VoiceSpeakerBot = field(init=False)

    def __post_init__(self) -> None:
        self.speaker = VoiceSpeakerBot(cwd=self.cwd)

    @property
    def spool_dir(self) -> Path:
        return self.cwd / ".hath0r" / "spool"

    @property
    def queue_file(self) -> Path:
        return self.spool_dir / "voice_queue.jsonl"

    @property
    def pid_file(self) -> Path:
        return self.cwd / ".hath0r" / "speaker-daemon.pid"

    @property
    def log_file(self) -> Path:
        return self.cwd / ".hath0r" / "speaker-daemon.log"

    def queue_message(
        self,
        message: str,
        priority: str = "normal",
        category: str = "notification",
    ) -> Dict[str, Any]:
        """Enqueue spoken announcement to spool."""
        self.spool_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "id": f"msg-{int(time.time()*1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "priority": priority,
            "category": category,
        }
        with open(self.queue_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        return {
            "success": True,
            "queued": True,
            "message_id": record["id"],
            "queue_file": str(self.queue_file),
        }

    def drain_queue(self, max_messages: Optional[int] = None, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Read and vocalize all queued announcements."""
        if not self.queue_file.is_file():
            return []

        try:
            lines = self.queue_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []

        if not lines:
            return []

        self.queue_file.unlink(missing_ok=True)

        processed = []
        for line in lines[:max_messages] if max_messages else lines:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                msg = record.get("message", "")
                if msg:
                    speak_res = self.speaker.speak(msg, dry_run=dry_run)
                    processed.append({"record": record, "result": speak_res})
            except Exception:
                pass

        return processed

    def is_running(self) -> Tuple[bool, Optional[int]]:
        """Check if background speaker worker is running."""
        if not self.pid_file.is_file():
            return False, None
        try:
            pid = int(self.pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return True, pid
        except (OSError, ValueError):
            self.pid_file.unlink(missing_ok=True)
            return False, None

    def start_daemon(self, background: bool = True, poll_interval: float = 1.0) -> Dict[str, Any]:
        """Start background speaker daemon."""
        running, existing_pid = self.is_running()
        if running and existing_pid != os.getpid():
            return {
                "success": True,
                "status": "already_running",
                "pid": existing_pid,
                "message": f"Speaker daemon is already running (PID: {existing_pid}).",
            }

        (self.cwd / ".hath0r").mkdir(parents=True, exist_ok=True)

        if background:
            cmd = [
                sys.executable,
                "-m",
                "hath0r_cli.cli",
                "voice",
                "speaker",
                "start",
                "--foreground",
            ]
            with open(self.log_file, "a", encoding="utf-8") as log_f:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.cwd),
                    stdout=log_f,
                    stderr=log_f,
                    start_new_session=True,
                )
            self.pid_file.write_text(str(proc.pid), encoding="utf-8")
            return {
                "success": True,
                "status": "started",
                "pid": proc.pid,
                "background": True,
                "message": f"Voice speaker daemon started (PID: {proc.pid}).",
            }

        # Foreground worker loop
        self.pid_file.write_text(str(os.getpid()), encoding="utf-8")
        try:
            while True:
                self.drain_queue()
                time.sleep(poll_interval)
        finally:
            self.pid_file.unlink(missing_ok=True)

    def stop_daemon(self) -> Dict[str, Any]:
        """Stop running speaker daemon."""
        running, pid = self.is_running()
        if not running or pid is None:
            return {
                "success": True,
                "status": "not_running",
                "message": "Speaker daemon is not currently running.",
            }

        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.3)
            if self.is_running()[0]:
                os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

        self.pid_file.unlink(missing_ok=True)
        return {
            "success": True,
            "status": "stopped",
            "pid": pid,
            "message": f"Speaker daemon (PID: {pid}) stopped.",
        }

    def status(self) -> Dict[str, Any]:
        """Check daemon worker status."""
        running, pid = self.is_running()
        queue_count = 0
        if self.queue_file.is_file():
            try:
                queue_count = len([l for l in self.queue_file.read_text(encoding="utf-8").splitlines() if l.strip()])
            except Exception:
                pass

        return {
            "running": running,
            "pid": pid,
            "status": "running" if running else "stopped",
            "queue_file": str(self.queue_file),
            "pending_count": queue_count,
            "log_file": str(self.log_file) if self.log_file.is_file() else None,
        }


@dataclass
class VoiceSpeakerModeBot:
    """Manages persistent hath0r-speak mode to vocalize all agent responses and outputs."""

    cwd: Path = field(default_factory=Path.cwd)
    speaker: VoiceSpeakerBot = field(init=False)

    def __post_init__(self) -> None:
        self.speaker = VoiceSpeakerBot(cwd=self.cwd)

    @property
    def config_file(self) -> Path:
        return self.cwd / ".hath0r" / "speak_mode.json"

    def is_enabled(self) -> bool:
        """Check if global spoken feedback mode is currently active."""
        if os.environ.get("HATH0R_SPEAK", "").lower() in ("1", "true", "yes", "on"):
            return True
        if not self.config_file.is_file():
            return False
        try:
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
            return bool(data.get("enabled", False))
        except Exception:
            return False

    def enable(self, speak: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Turn ON global spoken feedback mode."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            self.config_file.write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        msg = "Hath0r speak mode enabled. I will vocalize all agent actions and responses."
        speak_res = self.speaker.speak(msg, dry_run=dry_run) if speak else None
        return {
            "success": True,
            "enabled": True,
            "message": msg,
            "config_file": str(self.config_file),
            "speak_result": speak_res,
        }

    def disable(self, speak: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Turn OFF global spoken feedback mode."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            self.config_file.write_text(
                json.dumps(
                    {
                        "enabled": False,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        msg = "Hath0r speak mode disabled."
        speak_res = self.speaker.speak(msg, dry_run=dry_run) if speak else None
        return {
            "success": True,
            "enabled": False,
            "message": msg,
            "config_file": str(self.config_file),
            "speak_result": speak_res,
        }

    def toggle(self, speak: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Toggle speak mode on or off."""
        currently_enabled = self.is_enabled()
        if currently_enabled:
            return self.disable(speak=speak, dry_run=dry_run)
        return self.enable(speak=speak, dry_run=dry_run)

    def status(self) -> Dict[str, Any]:
        """Return speak mode status."""
        enabled = self.is_enabled()
        return {
            "enabled": enabled,
            "status": "enabled" if enabled else "disabled",
            "config_file": str(self.config_file),
        }

    def vocalize_response(
        self,
        command: str,
        state: str,
        data: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Automatically summarize and speak the result of an action or command."""
        if not self.is_enabled() and not dry_run:
            return None

        # Build concise spoken sentence
        data_dict = data or {}
        custom_msg = data_dict.get("message")
        if custom_msg and isinstance(custom_msg, str):
            spoken_text = filter_speech_text(custom_msg)
        elif state == "ok":
            spoken_text = f"Hathor {command.replace('.', ' ')} completed successfully."
        else:
            spoken_text = f"Hathor {command.replace('.', ' ')} reported status {state}."

        return self.speaker.speak(spoken_text, filter_code=True, dry_run=dry_run)

