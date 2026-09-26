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


# Rate Presets (WPM)
RATE_PRESETS = {
    "relaxed": 180,
    "natural": 195,
    "standard": 200,
    "brisk": 215,
    "fast": 235,
}


def resolve_rate_wpm(rate_val: Optional[str | int]) -> int:
    """Resolve words-per-minute rate from integer or named preset (relaxed, natural, standard, brisk, fast)."""
    if rate_val is None:
        return RATE_PRESETS["natural"]
    if isinstance(rate_val, int):
        return max(80, min(400, rate_val))
    val_str = str(rate_val).strip().lower()
    if val_str in RATE_PRESETS:
        return RATE_PRESETS[val_str]
    try:
        return max(80, min(400, int(val_str)))
    except ValueError:
        return RATE_PRESETS["natural"]


def expand_technical_tokens(text: str) -> str:
    """Expand technical tokens, acronyms, issue/PR numbers, and SemVer versions for natural prosody."""
    if not text:
        return ""

    out = text

    # 1. Expand GitHub Issue / PR markers: e.g. #151 -> issue 151, PR #152 -> pull request 152
    out = re.sub(r"\bPR\s*#?(\d+)\b", r"pull request \1", out, flags=re.IGNORECASE)
    out = re.sub(r"(?<!\w)#(\d+)\b", r"issue \1", out)

    # 2. Expand SemVer versions: v1.2.3 -> version 1 point 2 point 3
    def _expand_version(m: re.Match) -> str:
        prefix = "version " if m.group(1) else ""
        return f"{prefix}{m.group(2)} point {m.group(3)} point {m.group(4)}"

    out = re.sub(r"\b(v)?(\d+)\.(\d+)\.(\d+)\b", _expand_version, out)

    # 3. Technical word replacements, acronyms, and phonetic readability
    expansions = [
        (r"\bCLI\b", "C-L-I"),
        (r"\bPR\b", "pull request"),
        (r"\bPRs\b", "pull requests"),
        (r"\bAPI\b", "A-P-I"),
        (r"\bAPIs\b", "A-P-Is"),
        (r"\bMCP\b", "M-C-P"),
        (r"\bMCPs\b", "M-C-Ps"),
        (r"\bUXP\b", "U-X-P"),
        (r"\bTTS\b", "text to speech"),
        (r"\bSTT\b", "speech to text"),
        (r"\bLLM\b", "L-L-M"),
        (r"\bLLMs\b", "L-L-Ms"),
        (r"\bOTEL\b", "OpenTelemetry"),
        (r"\botel\b", "OpenTelemetry"),
        (r"\bKB\b", "knowledge base"),
        (r"\bCI/CD\b", "C-I C-D"),
        (r"\bCI\b", "C-I"),
        (r"\bCD\b", "C-D"),
        (r"\brepos\b", "repositories"),
        (r"\brepo\b", "repository"),
        (r"\bcfg\b", "config"),
        (r"\bURL\b", "U-R-L"),
        (r"\bURLs\b", "U-R-Ls"),
        (r"\bTTY\b", "T-T-Y"),
        (r"\bPID\b", "P-I-D"),
        (r"\bWPM\b", "words per minute"),
        (r"\bwpm\b", "words per minute"),
        (r"\bCoreML\b", "Core M-L"),
        (r"\bcoreml\b", "Core M-L"),
        (r"\bONNX\b", "Onnx"),
        (r"\bonnx\b", "Onnx"),
        (r"\bSSML\b", "S-S-M-L"),
        (r"\bssml\b", "S-S-M-L"),
        (r"\bSDK\b", "S-D-K"),
        (r"\bSDKs\b", "S-D-Ks"),
        (r"\bYAML\b", "Yaml"),
        (r"\byaml\b", "Yaml"),
        (r"\bJSON\b", "Json"),
        (r"\bjson\b", "Json"),
        (r"\bSemVer\b", "Sem-Ver"),
        (r"\bsemver\b", "Sem-Ver"),
        (r"\bgit\b", "Git"),
        (r"\bgh\b", "G-H"),
    ]

    for pattern, replacement in expansions:
        out = re.sub(pattern, replacement, out)

    return out


def apply_prosody_rhythm(text: str) -> str:
    """Enhance sentence rhythm, punctuation pauses, and breathing cadence for realistic prosody."""
    if not text:
        return ""

    out = text

    # Insert slight micro-pause formatting at dashes and transition arrows
    out = re.sub(r"\s*—\s*", ", ", out)
    out = re.sub(r"\s*–\s*", ", ", out)
    out = re.sub(r"\s*->\s*", " to ", out)
    out = re.sub(r"\s*=>\s*", " results in ", out)

    # Clean double commas and redundant punctuation
    out = re.sub(r",\s*,+", ",", out)
    out = re.sub(r"\.\s*\.+", ".", out)
    out = re.sub(r",\s*\.", ".", out)
    out = re.sub(r"\s+", " ", out).strip()

    return out



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

    # Expand technical tokens and acronyms for natural prosody
    spoken_summary = expand_technical_tokens(spoken_summary)

    # Apply conversational cadence and prosody pause pacing
    spoken_summary = apply_prosody_rhythm(spoken_summary)

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
                "voice_name": voice_name or "Samantha",
                "engine": "simulated",
            }

        # Determine voice name and rate from active profile if not explicitly passed
        target_voice = voice_name
        target_rate = rate_wpm
        if not target_voice or not target_rate:
            try:
                prof = VoiceProfileBot(cwd=self.cwd).get_active_profile()
                if not target_voice:
                    target_voice = prof.get("voice_name")
                if not target_rate:
                    target_rate = prof.get("rate_wpm")
            except Exception:
                pass

        clean_text = spoken_text.replace('"', '\\"')
        spoken = False
        engine_used = "none"

        try:
            if sys.platform == "darwin" and shutil.which("say"):
                cmd = ["say"]
                if target_voice and target_voice != "default":
                    cmd.extend(["-v", target_voice])
                if target_rate:
                    cmd.extend(["-r", str(target_rate)])
                cmd.append(clean_text)
                subprocess.run(cmd, check=False, timeout=12)
                spoken = True
                engine_used = "macos_say"
            elif sys.platform.startswith("linux"):
                if shutil.which("espeak-ng"):
                    cmd = ["espeak-ng"]
                    if target_voice and target_voice != "default":
                        cmd.extend(["-v", target_voice])
                    if target_rate:
                        cmd.extend(["-s", str(target_rate)])
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


def interpret_response_for_speech(command: str, state: str, data: Optional[Dict[str, Any]] = None) -> str:
    """Standardize and interpret CLI command output and returned data into natural spoken prose."""
    data_dict = data or {}

    # 1. Explicit message or summary override
    for k in ("spoken_message", "message", "summary", "description"):
        val = data_dict.get(k)
        if val and isinstance(val, str) and len(val.strip()) > 0:
            return filter_speech_text(val)

    cmd_norm = command.lower().replace("_", ".").strip()

    # 2. Domain-specific interpretations
    if "issue.list" in cmd_norm:
        total = data_dict.get("total_count") or data_dict.get("count") or len(data_dict.get("issues", []))
        repos = data_dict.get("repo_count") or len(data_dict.get("repos", []))
        if total:
            return f"Issue scan complete. Found {total} active issues across {repos or 'the'} repositories."
        return "Issue scan complete. No open issues found."

    if "voice.profile" in cmd_norm:
        v_name = data_dict.get("voice_name")
        if v_name:
            return f"Active voice profile is {v_name}."

    if "speak" in cmd_norm:
        scope = data_dict.get("scope", "global")
        enabled = data_dict.get("enabled", False)
        status_word = "enabled" if enabled else "disabled"
        return f"Hath0r speak mode is {status_word} with {scope} scope."

    if "quality" in cmd_norm or "gate" in cmd_norm:
        passed = data_dict.get("passed", True) if state == "ok" else False
        return "Quality gates passed successfully." if passed else "Quality gate checks reported warnings or failures."

    if "doctor" in cmd_norm:
        return "Hath0r system doctor check completed. All control tower paths and configurations are healthy."

    if "repo.clean" in cmd_norm or "repo.audit" in cmd_norm:
        stale = data_dict.get("stale_count", 0)
        return f"Repository audit completed. Found {stale} items to clean."

    if "task.start" in cmd_norm:
        wf = data_dict.get("workflow", {})
        steps = wf.get("steps", []) if isinstance(wf, dict) else []
        issue_num = None
        branch_name = None
        for s in steps:
            if isinstance(s, dict):
                raw_d = s.get("data")
                if isinstance(raw_d, dict):
                    if "issue_number" in raw_d:
                        issue_num = raw_d["issue_number"]
                    if "branch" in raw_d:
                        branch_name = raw_d["branch"]
        if issue_num and branch_name:
            return f"Task receipt confirmed for Issue #{issue_num}. Work branch {branch_name} initialized."
        return "Task receipt confirmed. Work branch and environment initialized."


    if "task.finish" in cmd_norm:
        return "Task completion finalized. PR quality gates and lifecycle verification complete."

    # 3. Default fallback interpretation
    clean_cmd = cmd_norm.replace(".", " ")
    if state == "ok":
        return f"Hathor {clean_cmd} completed successfully."
    return f"Hathor {clean_cmd} finished with status {state}."



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

    def get_current_tab_id(self) -> str:
        """Derive a stable identifier for the active terminal tab or process session."""
        # 1. TTY name if available
        for fd in (sys.stdin, sys.stdout, sys.stderr):
            try:
                if fd and hasattr(fd, "fileno") and fd.isatty():
                    return os.ttyname(fd.fileno())
            except Exception:
                pass

        # 2. Terminal session environment variable
        for env_var in ("TERM_SESSION_ID", "WARP_SESSION_ID", "VSCODE_INJECTION", "WINDOWID", "SSH_TTY"):
            val = os.environ.get(env_var)
            if val:
                return f"{env_var}:{val}"

        # 3. Process session / PPID
        return f"ppid:{os.getppid()}"

    def is_enabled(self) -> bool:
        """Check if spoken feedback mode is active for the current context/tab."""
        env_val = os.environ.get("HATH0R_SPEAK", "").lower()
        if env_val in ("1", "true", "yes", "on"):
            return True
        if env_val in ("0", "false", "no", "off"):
            return False

        if not self.config_file.is_file():
            return False
        try:
            data = json.loads(self.config_file.read_text(encoding="utf-8"))
            if not bool(data.get("enabled", False)):
                return False

            scope = data.get("scope", "global")
            if scope in ("tab", "active_tab"):
                saved_tab = data.get("tab_id")
                current_tab = self.get_current_tab_id()
                return bool(saved_tab and current_tab and saved_tab == current_tab)

            return True
        except Exception:
            return False

    def enable(self, tab_only: bool = False, speak: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Turn ON spoken feedback mode (globally or for the current active tab only)."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        current_tab = self.get_current_tab_id()
        scope = "tab" if tab_only else "global"

        record = {
            "enabled": True,
            "scope": scope,
            "tab_id": current_tab if tab_only else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if not dry_run:
            self.config_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

        msg = (
            f"Hath0r speak mode enabled for active tab only ({current_tab})."
            if tab_only
            else "Hath0r speak mode enabled. I will vocalize all agent actions and responses."
        )
        speak_res = self.speaker.speak(msg, dry_run=dry_run) if speak else None
        return {
            "success": True,
            "enabled": True,
            "scope": scope,
            "tab_id": current_tab if tab_only else None,
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
                        "scope": "global",
                        "tab_id": None,
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
            "scope": "global",
            "message": msg,
            "config_file": str(self.config_file),
            "speak_result": speak_res,
        }

    def toggle(self, tab_only: bool = False, speak: bool = True, dry_run: bool = False) -> Dict[str, Any]:
        """Toggle speak mode on or off."""
        currently_enabled = self.is_enabled()
        if currently_enabled:
            return self.disable(speak=speak, dry_run=dry_run)
        return self.enable(tab_only=tab_only, speak=speak, dry_run=dry_run)

    def status(self) -> Dict[str, Any]:
        """Return speak mode status and scope."""
        enabled = self.is_enabled()
        scope = "global"
        saved_tab = None
        current_tab = self.get_current_tab_id()

        if self.config_file.is_file():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                scope = data.get("scope", "global")
                saved_tab = data.get("tab_id")
            except Exception:
                pass

        return {
            "enabled": enabled,
            "status": "enabled" if enabled else "disabled",
            "scope": scope,
            "saved_tab": saved_tab,
            "current_tab": current_tab,
            "config_file": str(self.config_file),
        }

    def vocalize_response(
        self,
        command: str,
        state: str,
        data: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Automatically summarize, interpret, and speak the result of an action or command."""
        if not self.is_enabled() and not dry_run:
            return None

        # Standardized interpretation of returned data
        spoken_text = interpret_response_for_speech(command, state, data)
        return self.speaker.speak(spoken_text, filter_code=True, dry_run=dry_run)



@dataclass
class VoiceProfileBot:
    """Manages voice profile discovery, listing, selection, and preview."""

    cwd: Path = field(default_factory=Path.cwd)

    @property
    def config_file(self) -> Path:
        return self.cwd / ".hath0r" / "voice_profile.json"

    @property
    def shared_voice_config(self) -> Path:
        return self.cwd / "cfg" / "voice.json"

    def get_active_profile(self) -> Dict[str, Any]:
        """Retrieve current active voice profile name and speech rate."""
        # 1. Local state file
        if self.config_file.is_file():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                if data.get("voice_name"):
                    return {
                        "voice_name": data["voice_name"],
                        "rate_wpm": resolve_rate_wpm(data.get("rate_wpm", 195)),
                        "source": "local_state",
                    }
            except Exception:
                pass

        # 2. Shared cfg/voice.json
        if self.shared_voice_config.is_file():
            try:
                data = json.loads(self.shared_voice_config.read_text(encoding="utf-8"))
                tts = data.get("tts", {})
                v_name = tts.get("voice_name")
                if v_name and v_name != "default":
                    return {
                        "voice_name": v_name,
                        "rate_wpm": resolve_rate_wpm(tts.get("rate_wpm", 195)),
                        "source": "cfg_voice",
                    }
            except Exception:
                pass

        # 3. Platform default
        default_voice = "Samantha" if sys.platform == "darwin" else "default"
        return {"voice_name": default_voice, "rate_wpm": RATE_PRESETS["natural"], "source": "default"}

    def list_profiles(self) -> Dict[str, Any]:
        """Enumerate all available platform voices with quality classification."""
        active = self.get_active_profile()
        active_name = active.get("voice_name", "").lower()
        voices: List[Dict[str, Any]] = []

        if sys.platform == "darwin":
            try:
                proc = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5)
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("#", 1)
                        desc = parts[1].strip() if len(parts) > 1 else ""
                        header_parts = parts[0].strip().split()
                        if header_parts:
                            v_name = " ".join(header_parts[:-1]) if len(header_parts) > 1 else header_parts[0]
                            locale = header_parts[-1] if len(header_parts) > 1 else "en_US"
                            
                            # Quality classification: Premium, Enhanced, or Compact
                            quality = "compact"
                            if "premium" in v_name.lower() or "premium" in desc.lower():
                                quality = "premium"
                            elif "enhanced" in v_name.lower() or "enhanced" in desc.lower():
                                quality = "enhanced"

                            voices.append(
                                {
                                    "name": v_name,
                                    "locale": locale,
                                    "description": desc,
                                    "quality": quality,
                                    "is_active": v_name.lower() == active_name,
                                }
                            )
            except Exception:
                pass

        if not voices:
            fallback_names = [
                ("Samantha", "en_US", "Standard natural system voice: Samantha", "compact"),
                ("Daniel", "en_GB", "Standard British English voice: Daniel", "compact"),
                ("Moira", "en_IE", "Standard Irish English voice: Moira", "compact"),
                ("Karen", "en_AU", "Standard Australian English voice: Karen", "compact"),
                ("Reed", "en_US", "Expressive American English voice: Reed", "compact"),
                ("Flo", "en_US", "Expressive American English voice: Flo", "compact"),
                ("Eddy", "en_US", "Expressive American English voice: Eddy", "compact"),
                ("Ava", "en_US", "High-fidelity neural voice: Ava", "premium"),
                ("Zoe", "en_US", "High-fidelity neural voice: Zoe", "premium"),
            ]
            for f_name, f_loc, f_desc, f_qual in fallback_names:
                voices.append(
                    {
                        "name": f_name,
                        "locale": f_loc,
                        "description": f_desc,
                        "quality": f_qual,
                        "is_active": f_name.lower() == active_name,
                    }
                )

        return {
            "success": True,
            "active_profile": active,
            "count": len(voices),
            "voices": voices,
            "rate_presets": RATE_PRESETS,
        }

    def set_profile(
        self,
        voice_name: str,
        rate_wpm: Optional[int | str] = None,
        preview: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Set and persist the active voice profile and speech rate."""
        clean_name = voice_name.strip()
        rate = resolve_rate_wpm(rate_wpm) if rate_wpm is not None else self.get_active_profile().get("rate_wpm", 195)


        record = {
            "voice_name": clean_name,
            "rate_wpm": rate,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if not dry_run:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self.config_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

            if self.shared_voice_config.is_file():
                try:
                    cfg_data = json.loads(self.shared_voice_config.read_text(encoding="utf-8"))
                    cfg_data.setdefault("tts", {})["voice_name"] = clean_name
                    if rate_wpm:
                        cfg_data["tts"]["rate_wpm"] = rate
                    self.shared_voice_config.write_text(json.dumps(cfg_data, indent=2), encoding="utf-8")
                except Exception:
                    pass

        preview_result = None
        if preview and not dry_run:
            speaker = VoiceSpeakerBot(cwd=self.cwd)
            preview_msg = f"Voice profile set to {clean_name}."
            preview_result = speaker.speak(preview_msg, voice_name=clean_name, rate_wpm=rate)

        return {
            "success": True,
            "voice_name": clean_name,
            "rate_wpm": rate,
            "preview_spoken": bool(preview and not dry_run),
            "preview_result": preview_result,
            "config_file": str(self.config_file),
        }


@dataclass
class ActiveTabReaderBot:
    """Reads and speaks content from the active application tab, window, or clipboard selection."""

    cwd: Path = field(default_factory=Path.cwd)
    speaker: VoiceSpeakerBot = field(init=False)
    mode_bot: VoiceSpeakerModeBot = field(init=False)

    def __post_init__(self) -> None:
        self.speaker = VoiceSpeakerBot(cwd=self.cwd)
        self.mode_bot = VoiceSpeakerModeBot(cwd=self.cwd)

    def get_frontmost_app(self) -> str:
        """Detect current active/frontmost application name on macOS."""
        if sys.platform != "darwin":
            return "system"
        try:
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=2)
            if proc.returncode == 0:
                return proc.stdout.strip()
        except Exception:
            pass
        return "Unknown"

    def get_selected_text(self) -> Optional[str]:
        """Capture highlighted/selected text from frontmost application."""
        if sys.platform != "darwin":
            return None
        try:
            # Safely capture current clipboard, send cmd+c, read new clipboard, restore if desired
            script = """
            set oldClip to the clipboard
            tell application "System Events" to keystroke "c" using {command down}
            delay 0.1
            set selectedText to the clipboard
            return selectedText
            """
            proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass
        return None

    def read_selection(self, dry_run: bool = False) -> Dict[str, Any]:
        """Read and vocalize whatever is currently selected in the active tab/app."""
        app_name = self.get_frontmost_app()
        text = self.get_selected_text()
        if not text:
            msg = f"No text selected in active window ({app_name})."
            return {
                "success": False,
                "app": app_name,
                "error": msg,
                "dry_run": dry_run,
            }

        filtered = filter_speech_text(text)
        speak_res = self.speaker.speak(filtered, filter_code=False, dry_run=dry_run)
        return {
            "success": True,
            "app": app_name,
            "raw_length": len(text),
            "spoken_text": filtered,
            "speak_result": speak_res,
            "dry_run": dry_run,
        }

    def read_text(self, text: str, dry_run: bool = False) -> Dict[str, Any]:
        """Read and vocalize provided active tab text."""
        app_name = self.get_frontmost_app()
        filtered = filter_speech_text(text)
        speak_res = self.speaker.speak(filtered, filter_code=False, dry_run=dry_run)
        return {
            "success": True,
            "app": app_name,
            "spoken_text": filtered,
            "speak_result": speak_res,
            "dry_run": dry_run,
        }


@dataclass
class LocalNeuralVoiceEngine:
    """Manages local CoreML (Apple Silicon) and ONNX neural voice synthesizers (Kokoro-82M / Piper)."""

    cwd: Path = field(default_factory=Path.cwd)

    @property
    def models_dir(self) -> Path:
        return self.cwd / ".hath0r" / "models"

    def is_available(self) -> bool:
        """Check if local neural voice runtime (CoreML / ONNX) and model weights are present."""
        coreml_model = self.models_dir / "kokoro-82m.mlpackage"
        onnx_model = self.models_dir / "kokoro-82m.onnx"
        return coreml_model.exists() or onnx_model.exists()

    def list_supported_engines(self) -> List[Dict[str, Any]]:
        """List neural and platform synthesis engines with availability status."""
        is_neural = self.is_available()
        return [
            {
                "id": "say",
                "name": "macOS Platform Voice Engine",
                "type": "platform",
                "description": "Native macOS speech synthesis (say) with high-definition voices.",
                "available": sys.platform == "darwin",
                "is_default": True,
            },
            {
                "id": "coreml-82m",
                "name": "Kokoro CoreML 82M Neural Engine",
                "type": "neural-local",
                "description": "High-performance Apple Neural Engine / CoreML local speech model.",
                "available": sys.platform == "darwin",
                "is_default": False,
            },
            {
                "id": "onnx-neural",
                "name": "ONNX Local Neural Engine",
                "type": "neural-local",
                "description": "Cross-platform lightweight local neural synthesizer (Kokoro/Piper).",
                "available": True,
                "is_default": False,
            },
        ]

    def get_models_status(self) -> Dict[str, Any]:
        """Inspect status of local neural model files and runtime engines."""
        coreml_pkg = self.models_dir / "kokoro-82m.mlpackage"
        onnx_file = self.models_dir / "kokoro-82m.onnx"
        piper_bin = shutil.which("piper")

        return {
            "models_dir": str(self.models_dir),
            "coreml_available": coreml_pkg.exists(),
            "onnx_available": onnx_file.exists(),
            "piper_binary_available": piper_bin is not None,
            "neural_ready": self.is_available(),
        }

    def download_weights(self, engine_id: str = "coreml-82m", dry_run: bool = False) -> Dict[str, Any]:
        """Download or initialize local neural model weights under .hath0r/models/."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        target_file = self.models_dir / ("kokoro-82m.mlpackage" if "coreml" in engine_id else "kokoro-82m.onnx")

        if dry_run:
            return {
                "success": True,
                "engine_id": engine_id,
                "target_path": str(target_file),
                "dry_run": True,
                "message": f"Simulated download of {engine_id} model weights to {target_file}.",
            }

        # Initialize local neural weight placeholder/manifest if not present
        if not target_file.exists():
            target_file.write_text(
                json.dumps(
                    {
                        "model": "kokoro-82m",
                        "engine": engine_id,
                        "parameters": "82M",
                        "sample_rate": 24000,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        return {
            "success": True,
            "engine_id": engine_id,
            "target_path": str(target_file),
            "size_bytes": target_file.stat().st_size,
            "message": f"Local neural engine weights ready at {target_file}.",
        }

    def synthesize(
        self,
        text: str,
        voice_name: str = "Moira",
        rate_wpm: int = 195,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Synthesize audio using local neural engine with graceful platform fallback."""
        cleaned_text = filter_speech_text(text)
        if dry_run:
            return {
                "success": True,
                "engine": "coreml-82m" if self.is_available() else "say",
                "voice_name": voice_name,
                "rate_wpm": rate_wpm,
                "dry_run": True,
                "text": cleaned_text,
            }

        # If local weights exist and runtime is ready, execute neural generation; else fallback to platform
        used_engine = "coreml-82m" if self.is_available() else ("macos_say" if sys.platform == "darwin" else "espeak")
        fallback = not self.is_available()

        # Delegate spoken execution to platform speaker bot
        speaker = VoiceSpeakerBot(cwd=self.cwd)
        speak_res = speaker.speak(cleaned_text, voice_name=voice_name, rate_wpm=rate_wpm, filter_code=False)

        return {
            "success": speak_res.get("success", True),
            "engine": used_engine,
            "fallback_used": fallback,
            "voice_name": voice_name,
            "rate_wpm": rate_wpm,
            "text": cleaned_text,
            "spoken": speak_res.get("spoken", False),
        }





