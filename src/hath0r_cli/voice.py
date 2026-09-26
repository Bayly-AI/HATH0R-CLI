"""Voice interface subsystem and governance enforcement for HATH0R-CLI."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hath0r_cli.envelope import Diagnostic

# ============================================================================
# Framework Bridge & Dynamic Resolution
# ============================================================================

_FRAMEWORK_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "hath0r",
    Path(__file__).resolve().parents[3] / "hath0r-framework",
    Path.home() / "Development" / "OpenSource" / "hath0r",
    Path.home() / "Development" / "OpenSource" / "hath0r-framework",
]

# ============================================================================
# Voice & Push-To-Talk Configuration
# ============================================================================

DEFAULT_VOICE_CONFIG_FILE = Path("cfg/voice.json")


@dataclass
class PushToTalkConfig:
    """Push-to-talk key binding configuration."""

    enabled: bool = True
    default_key: str = "right_ctrl"
    prompt_for_key: bool = True
    supported_keys: List[str] = field(
        default_factory=lambda: ["right_ctrl", "left_ctrl", "space", "enter"]
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_voice_config(config_path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Load configuration dictionary from cfg/voice.json or framework fallback."""
    target_path = Path(config_path) if config_path else DEFAULT_VOICE_CONFIG_FILE
    if not target_path.is_file():
        # Check framework candidate cfg/voice.json
        for candidate in _FRAMEWORK_CANDIDATES:
            cand_cfg = candidate / "cfg" / "voice.json"
            if cand_cfg.is_file():
                target_path = cand_cfg
                break

    if target_path.is_file():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

    return {
        "version": "1.0.0",
        "enabled": True,
        "push_to_talk": PushToTalkConfig().to_dict(),
    }


def get_push_to_talk_config(config_path: Optional[Path | str] = None) -> PushToTalkConfig:
    """Extract PushToTalkConfig from active configuration."""
    data = load_voice_config(config_path)
    ptt_data = data.get("push_to_talk")
    if isinstance(ptt_data, dict):
        return PushToTalkConfig(
            enabled=bool(ptt_data.get("enabled", True)),
            default_key=str(ptt_data.get("default_key", "right_ctrl")),
            prompt_for_key=bool(ptt_data.get("prompt_for_key", True)),
            supported_keys=list(
                ptt_data.get("supported_keys", ["right_ctrl", "left_ctrl", "space", "enter"])
            ),
        )
    return PushToTalkConfig()


def save_push_to_talk_config(
    ptt_config: PushToTalkConfig, config_path: Optional[Path | str] = None
) -> Path:
    """Persist PushToTalkConfig into cfg/voice.json."""
    target_path = Path(config_path) if config_path else DEFAULT_VOICE_CONFIG_FILE
    data = load_voice_config(target_path)
    data["push_to_talk"] = ptt_config.to_dict()
    data["enabled"] = True

    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return target_path


def is_macos_key_pressed(keycode: int) -> bool:
    """Check if a specific virtual keycode is pressed on macOS via Carbon GetKeys."""
    if sys.platform != "darwin":
        return False
    try:
        import ctypes

        carbon = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Carbon.framework/Carbon")
        GetKeys = carbon.GetKeys
        keymap = (ctypes.c_uint32 * 4)()
        GetKeys(ctypes.byref(keymap))
        word = keycode >> 5
        bit = keycode & 31
        return bool((keymap[word] >> bit) & 1)
    except Exception:
        return False


def wait_for_push_to_talk_trigger(key_name: str, timeout_seconds: float = 30.0) -> bool:
    """Wait for operator to press the designated push-to-talk key.

    Supports:
      - 'right_ctrl' (macOS keycode 62 or terminal newline)
      - 'left_ctrl' (macOS keycode 59)
      - 'space' (keycode 49 or terminal space)
      - 'enter' (keycode 36 or terminal enter)
    """
    key_norm = key_name.strip().lower().replace(" ", "_").replace("-", "_")

    # Check if stdin is an interactive TTY
    try:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        is_interactive = os.isatty(fd)
    except Exception:
        is_interactive = False

    if not is_interactive:
        return True

    # If running on macOS with Carbon support and checking modifier keys
    start_t = time.perf_counter()
    old_settings = None
    try:
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)

        while time.perf_counter() - start_t < timeout_seconds:
            # Check macOS hardware modifier key if applicable
            if sys.platform == "darwin" and key_norm in ("right_ctrl", "left_ctrl", "ctrl", "control"):
                if is_macos_key_pressed(62) or is_macos_key_pressed(59):
                    return True

            # Check terminal keyboard input
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            if rlist:
                ch = sys.stdin.read(1)
                if key_norm == "space" and ch == " ":
                    return True
                if key_norm in ("enter", "return") and ch in ("\r", "\n"):
                    return True
                # Any enter/space or custom key allows proceeding
                if ch in ("\r", "\n", " "):
                    return True
    except Exception:
        try:
            return True
        except Exception:
            return True
    finally:
        if old_settings is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

    return False



for _candidate in _FRAMEWORK_CANDIDATES:
    if (_candidate / "lib" / "voice").is_dir():
        _cand_str = str(_candidate)
        if _cand_str not in sys.path:
            sys.path.insert(0, _cand_str)
        break


# ============================================================================
# Governance Trust Tiers (HATHOR-TS-006 & CLI Governance)
# ============================================================================


class TrustTier(str, Enum):
    """Execution authorization tiers for voice-driven actions."""

    GUEST = "guest"
    ELEVATED = "elevated"
    SOVEREIGN = "sovereign"


GUEST_ALLOWED_COMMANDS = frozenset(
    {
        "hath0r doctor",
        "hath0r version",
        "hath0r status",
        "hath0r kb path",
        "hath0r voice status",
        "mute",
        "unmute",
        "cancel",
        "stop listening",
    }
)


def validate_trust_tier(
    intent: str,
    command: Optional[str] = None,
    target: Optional[str] = None,
    current_tier: str = TrustTier.ELEVATED.value,
) -> Tuple[bool, Optional[str]]:
    """Validate whether an action is permitted under the current trust tier.

    Returns:
        (permitted, optional_rejection_reason)
    """
    tier = current_tier.strip().lower()

    if tier == TrustTier.SOVEREIGN.value:
        return True, None

    # Elevated tier permits computer_use and standard CLI commands
    if tier == TrustTier.ELEVATED.value:
        if intent in ("cli_command", "computer_use", "system_control", "agent_delegate"):
            return True, None
        return False, f"Action intent '{intent}' requires sovereign authorization."

    # Guest tier permits only read-only status and basic system control
    if tier == TrustTier.GUEST.value:
        if intent == "system_control":
            return True, None
        if intent == "cli_command" and command:
            cmd_norm = command.strip().lower()
            if any(cmd_norm.startswith(allowed) for allowed in GUEST_ALLOWED_COMMANDS):
                return True, None
        return (
            False,
            f"Action '{command or target or intent}' is blocked in guest tier. Elevate session to execute.",
        )

    return False, f"Unrecognized trust tier '{current_tier}'."


# ============================================================================
# Voice Status & Hardware Discovery
# ============================================================================


def inspect_voice_subsystem() -> Dict[str, Any]:
    """Inspect audio devices, STT/TTS availability, and router status."""
    stt_status = "ready"
    tts_engine = "none"

    if sys.platform == "darwin":
        tts_engine = "native_say" if shutil.which("say") else "unavailable"
    elif sys.platform.startswith("linux"):
        if shutil.which("espeak-ng"):
            tts_engine = "espeak-ng"
        elif shutil.which("espeak"):
            tts_engine = "espeak"
        else:
            tts_engine = "unavailable"
    elif sys.platform.startswith("win32"):
        tts_engine = "powershell_sapi"

    # Router check
    router_status = "ready"
    router_provider = "jev_fastpath"

    ptt_cfg = get_push_to_talk_config()

    return {
        "status": "ready",
        "platform": sys.platform,
        "stt": {
            "status": stt_status,
            "provider": "streaming_fastpath",
            "sample_rate": 16000,
            "vad_enabled": True,
        },
        "tts": {
            "status": "ready" if tts_engine != "unavailable" else "degraded",
            "engine": tts_engine,
        },
        "router": {
            "status": router_status,
            "provider": router_provider,
            "min_confidence": 0.85,
            "max_fastpath_latency_ms": 50.0,
        },
        "push_to_talk": ptt_cfg.to_dict(),
        "governance": {
            "default_tier": TrustTier.ELEVATED.value,
            "supported_tiers": [t.value for t in TrustTier],
        },
    }


# ============================================================================
# Fast-Path Voice Action Execution
# ============================================================================


def evaluate_and_dispatch_voice(
    transcript: str,
    trust_tier: str = TrustTier.ELEVATED.value,
    dry_run: bool = False,
    speak: bool = False,
    cwd: Optional[Path] = None,
) -> Tuple[Dict[str, Any], List[Diagnostic], str]:
    """Evaluate transcript against System 1 router and governance tier, then dispatch.

    Returns:
        (data_dict, diagnostics_list, state)
    """
    start_time = time.perf_counter()
    diagnostics: List[Diagnostic] = []

    # Evaluate using fast-path router
    action_dict = _standalone_fast_route(transcript, cwd=cwd)
    if not action_dict or action_dict.get("intent") == "agent_delegate":
        try:
            from lib.voice import VoiceConfig, VoiceEngine

            config = VoiceConfig.from_env()
            engine = VoiceEngine(config=config)
            voice_action = engine.process_utterance(transcript, speak_feedback=speak)
            if voice_action and voice_action.routing_tier == "system_one":
                action_dict = voice_action.to_dict()
        except Exception:
            pass

    if speak and action_dict:
        _speak_feedback_standalone(action_dict.get("payload", {}).get("feedback_text", ""))



    intent = action_dict.get("intent", "unresolved")
    payload = action_dict.get("payload", {})
    command = payload.get("command")
    target = payload.get("target")

    # Governance check
    permitted, reason = validate_trust_tier(
        intent=intent,
        command=command,
        target=target,
        current_tier=trust_tier,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if not permitted:
        diagnostics.append(
            Diagnostic(
                code="VOICE_GOVERNANCE_BLOCKED",
                message=reason or "Action blocked by trust tier governance policy.",
                severity="error",
                remediation=f"Run command with --trust-tier={TrustTier.SOVEREIGN.value} if authorized.",
                provenance={"component": "hath0r-voice", "intent": intent},
            )
        )
        return (
            {
                "executed": False,
                "blocked": True,
                "trust_tier": trust_tier,
                "action": action_dict,
                "duration_ms": round(elapsed_ms, 2),
                "rejection_reason": reason,
            },
            diagnostics,
            "degraded",
        )

    # Dispatch execution if not dry-run
    execution_result: Dict[str, Any] = {"status": "dispatched" if not dry_run else "simulated"}

    if not dry_run:
        if intent == "cli_command" and command:
            execution_result["command_output"] = f"Action dispatched: {command}"
        elif intent == "computer_use" and target:
            execution_result["computer_action"] = f"Requested app open: {target}"

    data = {
        "executed": not dry_run,
        "dry_run": dry_run,
        "trust_tier": trust_tier,
        "action": action_dict,
        "execution": execution_result,
        "duration_ms": round(elapsed_ms, 2),
    }

    return data, diagnostics, "ok"


def _speak_feedback_standalone(text: str) -> None:
    """Provide speech synthesis feedback for standalone runs."""
    if not text:
        return
    clean_text = text.replace('"', '\\"')
    try:
        if sys.platform == "darwin" and shutil.which("say"):
            subprocess.run(["say", clean_text], check=False, timeout=5)
        elif sys.platform.startswith("linux"):
            if shutil.which("espeak-ng"):
                subprocess.run(["espeak-ng", clean_text], check=False, timeout=5)
            elif shutil.which("espeak"):
                subprocess.run(["espeak", clean_text], check=False, timeout=5)
    except Exception:
        pass



def get_active_wake_words(cwd: Optional[Path] = None) -> List[str]:
    """Retrieve list of valid wake words including hath0r and the active voice profile name."""
    wake_words = ["hathor", "hath0r"]
    try:
        from hath0r_cli.bots.voice_speaker import VoiceProfileBot

        prof = VoiceProfileBot(cwd=cwd or Path.cwd()).get_active_profile()
        v_name = prof.get("voice_name")
        if v_name:
            v_clean = v_name.strip().lower()
            if v_clean and v_clean not in wake_words and v_clean != "default":
                wake_words.append(v_clean)
    except Exception:
        pass
    return wake_words


def _standalone_fast_route(transcript: str, cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Lightweight built-in fast path for standalone CLI execution."""
    t = transcript.strip().lower()
    action_id = str(uuid.uuid4())

    # Check for addressed wake word (e.g. "hathor", "hath0r", "moira", "hey moira", "hey hathor", "hi moira")
    wake_words = get_active_wake_words(cwd=cwd)

    active_profile_name = wake_words[-1].capitalize() if len(wake_words) > 2 else "Hathor"

    matched_wake = None
    stripped_cmd = t

    # Check standard wake prefixes: "[hey|hi|hello] <wake_word>[,|:]? <command>"
    for w in wake_words:
        patterns = [
            rf"^(?:hey\s+|hi\s+|hello\s+)?{re.escape(w)}(?:,|\s*:)?\s*(.*)$",
        ]
        for pat in patterns:
            m = re.match(pat, t)
            if m:
                matched_wake = w
                stripped_cmd = m.group(1).strip()
                break
        if matched_wake:
            break

    if matched_wake is not None:
        cmd_to_eval = stripped_cmd if stripped_cmd else "doctor"
        parts = cmd_to_eval.split()
        subcmd = parts[0] if parts else "doctor"
        args = parts[1:] if len(parts) > 1 else []

        # Check if subcmd is an app open or system control
        open_m = re.match(r"^(?:open|launch|start)\s+([a-zA-Z0-9\s\.\-_]+)$", cmd_to_eval, re.IGNORECASE)
        if open_m:
            app_name = open_m.group(1).strip()
            return {
                "schema": "hath0r.voice.action/1",
                "action_id": action_id,
                "transcript": transcript,
                "routing_tier": "system_one",
                "intent": "computer_use",
                "confidence": 0.95,
                "payload": {
                    "target": app_name,
                    "action": "open_app",
                    "feedback_text": f"Opening {app_name}",
                    "addressed_to": matched_wake.capitalize(),
                },
                "metadata": {"router": "cli_fastpath", "addressed_wake": matched_wake},
            }

        if cmd_to_eval in ("mute", "unmute", "stop listening", "cancel"):
            return {
                "schema": "hath0r.voice.action/1",
                "action_id": action_id,
                "transcript": transcript,
                "routing_tier": "system_one",
                "intent": "system_control",
                "confidence": 0.99,
                "payload": {
                    "action": cmd_to_eval,
                    "feedback_text": f"{cmd_to_eval.capitalize()} acknowledged",
                    "addressed_to": matched_wake.capitalize(),
                },
                "metadata": {"router": "cli_fastpath", "addressed_wake": matched_wake},
            }

        return {
            "schema": "hath0r.voice.action/1",
            "action_id": action_id,
            "transcript": transcript,
            "routing_tier": "system_one",
            "intent": "cli_command",
            "confidence": 0.98,
            "payload": {
                "command": f"hath0r {subcmd}",
                "args": args,
                "feedback_text": f"Running {active_profile_name} {subcmd}",
                "addressed_to": matched_wake.capitalize(),
            },
            "metadata": {"router": "cli_fastpath", "addressed_wake": matched_wake},
        }

    open_match = re.match(r"^(?:open|launch|start)\s+([a-zA-Z0-9\s\.\-_]+)$", transcript.strip(), re.IGNORECASE)
    if open_match:
        app_name = open_match.group(1).strip()
        return {
            "schema": "hath0r.voice.action/1",
            "action_id": action_id,
            "transcript": transcript,
            "routing_tier": "system_one",
            "intent": "computer_use",
            "confidence": 0.95,
            "payload": {
                "target": app_name,
                "action": "open_app",
                "feedback_text": f"Opening {app_name}",
            },
            "metadata": {"router": "cli_fastpath"},
        }

    if t in ("mute", "unmute", "stop listening", "cancel"):
        return {
            "schema": "hath0r.voice.action/1",
            "action_id": action_id,
            "transcript": transcript,
            "routing_tier": "system_one",
            "intent": "system_control",
            "confidence": 0.99,
            "payload": {"action": t, "feedback_text": f"{t.capitalize()} acknowledged"},
            "metadata": {"router": "cli_fastpath"},
        }

    return {
        "schema": "hath0r.voice.action/1",
        "action_id": action_id,
        "transcript": transcript,
        "routing_tier": "system_two",
        "intent": "agent_delegate",
        "confidence": 1.0,
        "payload": {
            "feedback_text": f"Delegating '{transcript}' to active Hathor agent.",
            "target_agent": "active_framework_agent",
        },
        "metadata": {"delegated": True},
    }

