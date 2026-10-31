"""Structured Hath0r Agent Handoff Protocol (HAHP) & State Serialization."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

HAHP_KEY_PREFIX = "hahp:"


class HAHPEnvelope(BaseModel):
    """Hath0r Agent Handoff Protocol (HAHP) Envelope Schema."""

    handoff_id: str = Field(default_factory=lambda: f"hahp-{uuid.uuid4().hex[:8]}")
    sender_agent: str
    recipient_agent: str
    timestamp: float = Field(default_factory=time.time)
    scratchpad_delta: str = ""
    state_variables: Dict[str, Any] = Field(default_factory=dict)
    tool_outputs: List[Dict[str, Any]] = Field(default_factory=list)
    kv_cache_pointer: Optional[str] = None
    protocol_version: str = "1.0.0"


class HAHPProtocolManager:
    """Manager for serializing, deserializing, and syncing HAHP handoff envelopes."""

    def __init__(self) -> None:
        self._journal: List[HAHPEnvelope] = []

    def create_envelope(
        self,
        sender_agent: str,
        recipient_agent: str,
        scratchpad_delta: str = "",
        state_variables: Optional[Dict[str, Any]] = None,
        tool_outputs: Optional[List[Dict[str, Any]]] = None,
        kv_cache_pointer: Optional[str] = None,
    ) -> HAHPEnvelope:
        """Create a new validated HAHP envelope (pre-persist L2 secret/PII sanitized)."""
        from hath0r_cli.bots.secret_pii_sanitizer import secret_pii_sanitizer
        from hath0r_cli.bots.supercompress_bot import supercompress_bot

        sanitized_delta = secret_pii_sanitizer.redact_text(scratchpad_delta).sanitized_text
        redacted_vars = dict(secret_pii_sanitizer.redact_payload(state_variables or {}))
        if len(sanitized_delta.split()) > 150:
            sq = supercompress_bot.compress(
                query=f"{sender_agent} {recipient_agent}",
                context=sanitized_delta,
                threshold=0.5,
                force_local=True,
            )
            sanitized_delta = sq.get("compressed_text", sanitized_delta)
            redacted_vars["_supersqueeze"] = {
                "squeezed": True,
                "original_tokens": sq.get("original_tokens", 0),
                "compressed_tokens": sq.get("compressed_tokens", 0),
                "savings_pct": sq.get("savings_pct", 0.0),
                "owning_bot": "SuperSqueezeBot",
            }

        envelope = HAHPEnvelope(
            sender_agent=sender_agent,
            recipient_agent=recipient_agent,
            scratchpad_delta=sanitized_delta,
            state_variables=redacted_vars,
            tool_outputs=secret_pii_sanitizer.redact_payload(tool_outputs or []),
            kv_cache_pointer=kv_cache_pointer,
        )
        self._journal.append(envelope)
        self.sync_to_session_store(envelope)
        return envelope

    def serialize(self, envelope: HAHPEnvelope) -> str:
        """Serialize envelope to JSON string."""
        return envelope.model_dump_json(indent=2)

    def deserialize(self, json_data: str) -> HAHPEnvelope:
        """Deserialize JSON string into validated HAHP envelope."""
        data = json.loads(json_data)
        return HAHPEnvelope(**data)

    def sync_to_session_store(self, envelope: HAHPEnvelope, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Persist the envelope to the shared session store under ``hahp:<handoff_id>``.

        The envelope always stays in the in-process journal. A backend failure is logged as a
        warning and reported with ``status: "error"`` instead of claiming a sync happened.
        """
        from hath0r_cli.session_store import SessionStoreError, get_session_store

        key = f"{HAHP_KEY_PREFIX}{envelope.handoff_id}"
        try:
            store = get_session_store()
            written = store.set(key, envelope.model_dump(mode="json"), ttl_seconds=ttl_seconds)
        except SessionStoreError as exc:
            logger.warning("HAHP handoff %s not synced to session store: %s", envelope.handoff_id, exc)
            return {
                "status": "error",
                "handoff_id": envelope.handoff_id,
                "session_backend": None,
                "error": str(exc),
                "timestamp": time.time(),
            }
        return {
            "status": "synced",
            "handoff_id": envelope.handoff_id,
            "key": key,
            "session_backend": store.describe(),
            "expires_at": written.get("expires_at"),
            "timestamp": time.time(),
        }

    def load_from_session_store(self, handoff_id: str) -> Optional[HAHPEnvelope]:
        """Read a handoff envelope back from the shared session store (any process)."""
        from hath0r_cli.session_store import get_session_store

        data = get_session_store().get(f"{HAHP_KEY_PREFIX}{handoff_id}")
        return HAHPEnvelope(**data) if isinstance(data, dict) else None

    def list_handoffs(self) -> List[Dict[str, Any]]:
        """List active journaled handoffs."""
        return [env.model_dump() for env in self._journal]


hahp_manager = HAHPProtocolManager()
