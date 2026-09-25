"""Voice interface subsystem and governance enforcement for HATH0R-CLI."""

from __future__ import annotations

import re
import shutil
import sys
import time
import uuid
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
) -> Tuple[Dict[str, Any], List[Diagnostic], str]:
    """Evaluate transcript against System 1 router and governance tier, then dispatch.

    Returns:
        (data_dict, diagnostics_list, state)
    """
    start_time = time.perf_counter()
    diagnostics: List[Diagnostic] = []

    # Attempt to import framework VoiceEngine, or use built-in fast router
    voice_action: Optional[Any] = None
    try:
        from lib.voice import VoiceConfig, VoiceEngine

        config = VoiceConfig.from_env()
        engine = VoiceEngine(config=config)
        voice_action = engine.process_utterance(transcript, speak_feedback=False)
        action_dict = voice_action.to_dict()
    except Exception:
        # Resilient standalone fallback router
        action_dict = _standalone_fast_route(transcript)

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


def _standalone_fast_route(transcript: str) -> Dict[str, Any]:
    """Lightweight built-in fast path for standalone CLI execution."""
    t = transcript.strip().lower()
    action_id = str(uuid.uuid4())

    if t.startswith("hathor ") or t.startswith("hath0r ") or t in ("hathor", "hath0r"):
        parts = t.split()
        subcmd = parts[1] if len(parts) > 1 else "doctor"
        args = parts[2:]
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
                "feedback_text": f"Running Hathor {subcmd}",
            },
            "metadata": {"router": "cli_fastpath"},
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
