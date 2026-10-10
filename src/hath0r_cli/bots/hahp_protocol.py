"""Structured Hath0r Agent Handoff Protocol (HAHP) & State Serialization."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
        """Create a new validated HAHP envelope."""
        envelope = HAHPEnvelope(
            sender_agent=sender_agent,
            recipient_agent=recipient_agent,
            scratchpad_delta=scratchpad_delta,
            state_variables=state_variables or {},
            tool_outputs=tool_outputs or [],
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

    def sync_to_session_store(self, envelope: HAHPEnvelope) -> Dict[str, Any]:
        """Synchronize envelope state to the session store.

        No session backend (Redis/DynamoDB) is wired up yet, so envelopes are kept in the
        in-process journal only; the response says so rather than reporting a remote sync.
        """
        return {
            "status": "journaled_only",
            "handoff_id": envelope.handoff_id,
            "session_backend": None,
            "timestamp": time.time(),
        }

    def list_handoffs(self) -> List[Dict[str, Any]]:
        """List active journaled handoffs."""
        return [env.model_dump() for env in self._journal]


hahp_manager = HAHPProtocolManager()
