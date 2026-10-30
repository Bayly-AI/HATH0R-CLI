"""FinOps Token Telemetry and Histogram Analytics Bot for HATH0R CLI."""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from hath0r_cli.bots.secret_pii_sanitizer import secret_pii_sanitizer

GENESIS_HASH = "0" * 64

# Industry pricing benchmarks (USD per 1M tokens)
TIER_PRICING: Dict[str, Dict[str, float]] = {
    "light": {"input": 0.15, "output": 0.60},
    "standard": {"input": 3.00, "output": 15.00},
    "reasoning": {"input": 15.00, "output": 60.00},
}


class TelemetryRateLimitExceeded(RuntimeError):
    """Raised when telemetry write rate exceeds the configured token-bucket budget."""


@dataclass
class TokenTelemetryCLIBot:
    """Manages token telemetry ledger and generates distribution histograms."""

    cwd: Path = field(default_factory=Path.cwd)
    max_writes_per_minute: int = 120
    _write_timestamps: List[float] = field(default_factory=list, repr=False)

    @property
    def ledger_path(self) -> Path:
        return self.cwd / ".hath0r" / "finops" / "token_telemetry.jsonl"

    def _ensure_dir(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def _check_rate_limit(self) -> None:
        now = time.monotonic()
        self._write_timestamps = [t for t in self._write_timestamps if now - t < 60.0]
        if len(self._write_timestamps) >= self.max_writes_per_minute:
            raise TelemetryRateLimitExceeded(
                f"Telemetry write rate limit exceeded ({self.max_writes_per_minute} writes/min)"
            )
        self._write_timestamps.append(now)

    @staticmethod
    def _compute_record_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
        body = {k: v for k, v in payload.items() if k not in ("prev_hash", "hash")}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(f"{prev_hash}:{canonical}".encode("utf-8")).hexdigest()

    def _last_hash(self) -> str:
        if not self.ledger_path.exists():
            return GENESIS_HASH
        last_line = ""
        with self.ledger_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()
        if not last_line:
            return GENESIS_HASH
        try:
            data = json.loads(last_line)
            return str(data.get("hash") or self._compute_record_hash(GENESIS_HASH, data))
        except Exception:
            return GENESIS_HASH

    def record(
        self,
        prompt: str,
        user_id: str = "default_user",
        model: str = "claude-3-5-sonnet",
        tier: str = "standard",
        completion: str = "",
        session_id: str = "",
        agent_id: str = "hath0r-agent",
        latency_ms: float = 0.0,
        cached: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record an agent prompt interaction to the tamper-evident SHA-256 hash-chained ledger."""
        self._check_rate_limit()
        self._ensure_dir()
        sanitized_prompt = secret_pii_sanitizer.redact_text(prompt).sanitized_text
        sanitized_completion = secret_pii_sanitizer.redact_text(completion).sanitized_text
        sanitized_meta = secret_pii_sanitizer.redact_payload(metadata or {})

        p_len = len(sanitized_prompt)
        c_len = len(sanitized_completion)
        p_tok = max(1, math.ceil(p_len / 4.0)) if p_len > 0 else 0
        c_tok = max(1, math.ceil(c_len / 4.0)) if c_len > 0 else 0
        tot_tok = p_tok + c_tok

        tier_key = tier.lower() if tier.lower() in TIER_PRICING else "standard"
        pricing = TIER_PRICING[tier_key]
        cost = (p_tok / 1_000_000.0) * pricing["input"] + (c_tok / 1_000_000.0) * pricing["output"]
        if cached:
            cost = 0.0

        prev_hash = self._last_hash()
        rec: Dict[str, Any] = {
            "id": f"tok_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timestamp_ns": int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1_000_000_000),
            "user_id": user_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "prompt_length_chars": p_len,
            "prompt_tokens": p_tok,
            "completion_length_chars": c_len,
            "completion_tokens": c_tok,
            "total_tokens": tot_tok,
            "model": model,
            "tier": tier,
            "cost_usd": round(cost, 8),
            "latency_ms": round(latency_ms, 2),
            "cached": cached,
            "metadata": sanitized_meta,
            "prev_hash": prev_hash,
        }
        rec["hash"] = self._compute_record_hash(prev_hash, rec)

        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

        return rec

    def verify_ledger(self) -> Dict[str, Any]:
        """Verify cryptographic SHA-256 hash chain integrity across the JSONL telemetry ledger."""
        if not self.ledger_path.exists():
            return {
                "valid": True,
                "records_checked": 0,
                "chain_head_hash": GENESIS_HASH,
                "tampered_records": [],
            }

        expected_prev = GENESIS_HASH
        checked = 0
        tampered: List[Dict[str, Any]] = []

        with self.ledger_path.open("r", encoding="utf-8") as f:
            for line_num, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                checked += 1
                try:
                    rec = json.loads(line)
                except Exception:
                    tampered.append({"line": line_num, "reason": "malformed_json"})
                    continue

                if "hash" not in rec:
                    # Legacy record prior to hash chaining: advance chain deterministically
                    expected_prev = self._compute_record_hash(GENESIS_HASH, rec)
                    continue

                actual_prev = str(rec.get("prev_hash", ""))
                actual_hash = str(rec.get("hash", ""))
                computed_hash = self._compute_record_hash(actual_prev, rec)

                if actual_prev != expected_prev:
                    tampered.append(
                        {
                            "line": line_num,
                            "id": rec.get("id"),
                            "reason": "prev_hash_mismatch",
                            "expected_prev_hash": expected_prev,
                            "actual_prev_hash": actual_prev,
                        }
                    )
                elif actual_hash != computed_hash:
                    tampered.append(
                        {
                            "line": line_num,
                            "id": rec.get("id"),
                            "reason": "record_hash_tampered",
                            "expected_hash": computed_hash,
                            "actual_hash": actual_hash,
                        }
                    )
                expected_prev = actual_hash

        return {
            "valid": len(tampered) == 0,
            "records_checked": checked,
            "chain_head_hash": expected_prev,
            "tampered_records": tampered,
        }

    def list_records(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tier: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List records from the telemetry ledger."""
        if not self.ledger_path.exists():
            return []

        records: List[Dict[str, Any]] = []
        with self.ledger_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if user_id and data.get("user_id") != user_id:
                        continue
                    if model and data.get("model") != model:
                        continue
                    if agent_id and data.get("agent_id") != agent_id:
                        continue
                    if session_id and data.get("session_id") != session_id:
                        continue
                    if tier and data.get("tier") != tier:
                        continue
                    records.append(data)
                except Exception:
                    continue

        return records[-limit:] if limit > 0 else records

    def histogram(
        self,
        metric: str = "prompt_tokens",
        user_id: Optional[str] = None,
        model: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tier: Optional[str] = None,
        bins_count: int = 10,
        max_bar_width: int = 25,
    ) -> Dict[str, Any]:
        """Generate statistical histogram of token telemetry records."""
        records = self.list_records(
            user_id=user_id,
            model=model,
            agent_id=agent_id,
            session_id=session_id,
            tier=tier,
            limit=10_000,
        )
        tot_recs = len(records)
        tot_tok = sum(r.get("total_tokens", 0) for r in records)
        tot_cost = round(sum(r.get("cost_usd", 0.0) for r in records), 6)

        values: List[float] = []
        for r in records:
            values.append(float(r.get(metric, r.get("prompt_tokens", 0))))

        if not values:
            return {
                "metric": metric,
                "total_records": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "stats": {"min": 0, "max": 0, "mean": 0, "median": 0, "p95": 0, "p99": 0, "std_dev": 0},
                "bins": [],
                "user_distribution": {},
                "model_distribution": {},
            }

        s_vals = sorted(values)
        n = len(s_vals)
        v_min = s_vals[0]
        v_max = s_vals[-1]
        mean = sum(s_vals) / n

        def _p(q: float) -> float:
            idx = int(round(q * (n - 1)))
            return s_vals[max(0, min(n - 1, idx))]

        median = _p(0.50)
        p95 = _p(0.95)
        p99 = _p(0.99)
        variance = sum((x - mean) ** 2 for x in s_vals) / n
        std_dev = math.sqrt(variance)

        stats = {
            "min": round(v_min, 2),
            "max": round(v_max, 2),
            "mean": round(mean, 2),
            "median": round(median, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "std_dev": round(std_dev, 2),
        }

        user_dist: Dict[str, Dict[str, Any]] = {}
        model_dist: Dict[str, Dict[str, Any]] = {}
        for r in records:
            u = r.get("user_id", "unknown")
            m = r.get("model", "unknown")
            if u not in user_dist:
                user_dist[u] = {"count": 0, "tokens": 0, "cost_usd": 0.0}
            user_dist[u]["count"] += 1
            user_dist[u]["tokens"] += r.get("total_tokens", 0)
            user_dist[u]["cost_usd"] = round(user_dist[u]["cost_usd"] + r.get("cost_usd", 0.0), 6)

            if m not in model_dist:
                model_dist[m] = {"count": 0, "tokens": 0, "cost_usd": 0.0}
            model_dist[m]["count"] += 1
            model_dist[m]["tokens"] += r.get("total_tokens", 0)
            model_dist[m]["cost_usd"] = round(model_dist[m]["cost_usd"] + r.get("cost_usd", 0.0), 6)

        if v_min == v_max:
            bins = [
                {
                    "bin_index": 0,
                    "bin_start": v_min,
                    "bin_end": v_max,
                    "count": tot_recs,
                    "percentage": 100.0,
                    "cumulative_percentage": 100.0,
                    "ascii_bar": "█" * max_bar_width,
                }
            ]
        else:
            bin_width = (v_max - v_min) / float(bins_count)
            bin_counts = [0] * bins_count
            for v in values:
                idx = int((v - v_min) / bin_width)
                if idx >= bins_count:
                    idx = bins_count - 1
                bin_counts[idx] += 1

            max_cnt = max(bin_counts) if bin_counts else 1
            cum = 0
            bins = []
            for i in range(bins_count):
                st = v_min + i * bin_width
                en = v_min + (i + 1) * bin_width
                c = bin_counts[i]
                cum += c
                bar_len = int((c / max_cnt) * max_bar_width) if max_cnt > 0 else 0
                bins.append(
                    {
                        "bin_index": i,
                        "bin_start": round(st, 1),
                        "bin_end": round(en, 1),
                        "count": c,
                        "percentage": round((c / tot_recs) * 100.0, 1),
                        "cumulative_percentage": round((cum / tot_recs) * 100.0, 1),
                        "ascii_bar": "█" * bar_len,
                    }
                )

        return {
            "metric": metric,
            "total_records": tot_recs,
            "total_tokens": tot_tok,
            "total_cost_usd": tot_cost,
            "stats": stats,
            "bins": bins,
            "user_distribution": user_dist,
            "model_distribution": model_dist,
        }
