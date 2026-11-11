"""AndonBot: stop-the-line signals for Hath0r workflows (WS6, #588, #589).

Any bot can pull the cord: ``raise_event(severity="stop"|"warn")``. Events, acknowledgements and
clears are appended to a tamper-evident SHA-256 hash-chained ledger
(``.hath0r/state/andon/events.jsonl``, same chaining as the FinOps token ledger). While any stop
is active, ``check()`` raises ``AndonStop`` so DAG runs and factory steps halt before starting
more work. A stop must be acknowledged before it can be cleared, and stops are routed to the
Decision Radar so a person sees them.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.bots.token_telemetry_bot import GENESIS_HASH, TokenTelemetryCLIBot

SEVERITIES = ("stop", "warn")


class AndonStop(RuntimeError):
    """Raised when work is attempted while an Andon stop is active."""

    def __init__(self, events: List[Dict[str, Any]]) -> None:
        self.events = events
        reasons = "; ".join(f"{e['event_id']} ({e['source']}): {e['reason']}" for e in events)
        super().__init__(f"Andon stop active: {reasons}. Run 'hath0r andon ack' then 'hath0r andon clear'.")


def _hash(prev: str, rec: Dict[str, Any]) -> str:
    return TokenTelemetryCLIBot._compute_record_hash(prev, rec)


@dataclass
class AndonBot:
    """Raises, acknowledges, clears and verifies Andon events."""

    cwd: Path = field(default_factory=Path.cwd)
    route_to_radar: bool = True

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.ledger_path = self.cwd / ".hath0r" / "state" / "andon" / "events.jsonl"

    # ------------------------------------------------------------------ ledger
    def _records(self) -> List[Dict[str, Any]]:
        if not self.ledger_path.is_file():
            return []
        out = []
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    def _append(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        records = self._records()
        prev = records[-1]["hash"] if records else GENESIS_HASH
        rec = {**rec, "timestamp": datetime.now(timezone.utc).isoformat(), "prev_hash": prev}
        rec["hash"] = _hash(prev, rec)
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        return rec

    def verify(self) -> Dict[str, Any]:
        """Check the hash chain; any edited or removed record breaks it."""
        prev = GENESIS_HASH
        tampered: List[int] = []
        records = self._records()
        for i, rec in enumerate(records):
            if rec.get("prev_hash") != prev or rec.get("hash") != _hash(prev, rec):
                tampered.append(i)
            prev = str(rec.get("hash"))
        return {"success": not tampered, "valid": not tampered, "records_checked": len(records), "tampered_records": tampered, "chain_head_hash": prev}

    # ------------------------------------------------------------------ events
    def raise_event(
        self,
        *,
        source: str,
        reason: str,
        severity: str = "stop",
        workflow_id: Optional[str] = None,
        step_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if severity not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}")
        rec = self._append(
            {
                "type": "event",
                "event_id": f"andon-{uuid.uuid4().hex[:10]}",
                "severity": severity,
                "source": source,
                "reason": reason,
                "workflow_id": workflow_id,
                "step_id": step_id,
                "details": details or {},
            }
        )
        if severity == "stop" and self.route_to_radar:
            self._route_to_radar(rec)
        return {"success": True, **rec}

    def _route_to_radar(self, rec: Dict[str, Any]) -> None:
        try:
            from hath0r_cli.bots.decision_radar_bot import DecisionRadarBot

            DecisionRadarBot(cwd=self.cwd).request_decision(
                question=f"Andon stop from {rec['source']}: {rec['reason']}. Fix the cause, then ack and clear {rec['event_id']}.",
                category="only_you_can_do_this",
                agent_id="andon-bot",
                options=["ack and investigate", "clear (cause fixed)"],
                criticality=1.0,
                context={"andon_event_id": rec["event_id"], "workflow_id": rec.get("workflow_id")},
                sync_remote=False,
            )
        except Exception as exc:  # routing is best-effort; the ledger is the record
            self._append({"type": "note", "event_id": rec["event_id"], "note": f"radar routing failed: {exc}"})

    def _find(self, event_id: str) -> Dict[str, Any]:
        state = self._fold()
        if event_id not in state:
            raise ValueError(f"unknown andon event '{event_id}'")
        return state[event_id]

    def ack(self, event_id: str, by: str = "operator", note: str = "") -> Dict[str, Any]:
        ev = self._find(event_id)
        if ev["state"] == "cleared":
            raise ValueError(f"{event_id} is already cleared")
        rec = self._append({"type": "ack", "event_id": event_id, "by": by, "note": note})
        return {"success": True, **rec}

    def clear(self, event_id: str, by: str = "operator", note: str = "") -> Dict[str, Any]:
        ev = self._find(event_id)
        if ev["state"] == "cleared":
            raise ValueError(f"{event_id} is already cleared")
        if ev["severity"] == "stop" and ev["state"] != "acknowledged":
            raise ValueError(f"{event_id} is a stop: acknowledge it first ('hath0r andon ack {event_id}')")
        rec = self._append({"type": "clear", "event_id": event_id, "by": by, "note": note})
        return {"success": True, **rec}

    def _fold(self) -> Dict[str, Dict[str, Any]]:
        state: Dict[str, Dict[str, Any]] = {}
        for rec in self._records():
            eid = str(rec.get("event_id"))
            if rec.get("type") == "event":
                state[eid] = {k: rec.get(k) for k in ("event_id", "severity", "source", "reason", "workflow_id", "step_id", "details", "timestamp")}
                state[eid]["state"] = "open"
            elif eid in state and rec.get("type") == "ack":
                state[eid]["state"] = "acknowledged"
                state[eid]["acked_by"] = rec.get("by")
            elif eid in state and rec.get("type") == "clear":
                state[eid]["state"] = "cleared"
                state[eid]["cleared_by"] = rec.get("by")
        return state

    def active(self) -> List[Dict[str, Any]]:
        return [e for e in self._fold().values() if e["state"] != "cleared"]

    def status(self) -> Dict[str, Any]:
        active = self.active()
        stops = [e for e in active if e["severity"] == "stop"]
        chain = self.verify()
        return {
            "success": True,
            "schema_version": "hath0r.andon.status/v1",
            "stopped": bool(stops),
            "active": active,
            "active_stops": len(stops),
            "active_warnings": len(active) - len(stops),
            "ledger": str(self.ledger_path),
            "ledger_valid": chain["valid"],
        }

    def check(self) -> Dict[str, Any]:
        """Raise ``AndonStop`` if any stop is active; otherwise return the status."""
        st = self.status()
        if st["stopped"]:
            raise AndonStop([e for e in st["active"] if e["severity"] == "stop"])
        return st
