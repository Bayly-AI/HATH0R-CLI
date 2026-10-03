"""FinOps Token Telemetry and Histogram Analytics Bot for HATH0R CLI."""

from __future__ import annotations

import datetime
import json
import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Industry pricing benchmarks (USD per 1M tokens)
TIER_PRICING: Dict[str, Dict[str, float]] = {
    "light": {"input": 0.15, "output": 0.60},
    "standard": {"input": 3.00, "output": 15.00},
    "reasoning": {"input": 15.00, "output": 60.00},
}


@dataclass
class TokenTelemetryCLIBot:
    """Manages token telemetry ledger and generates distribution histograms."""

    cwd: Path = field(default_factory=Path.cwd)

    @property
    def ledger_path(self) -> Path:
        return self.cwd / ".hath0r" / "finops" / "token_telemetry.jsonl"

    def _ensure_dir(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        prompt: str,
        user_id: str = "default_user",
        model: str = "claude-3-5-sonnet",
        tier: str = "standard",
        completion: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        """Record an agent prompt interaction to the telemetry ledger."""
        self._ensure_dir()
        p_len = len(prompt)
        c_len = len(completion)
        p_tok = max(1, math.ceil(p_len / 4.0)) if p_len > 0 else 0
        c_tok = max(1, math.ceil(c_len / 4.0)) if c_len > 0 else 0
        tot_tok = p_tok + c_tok

        tier_key = tier.lower() if tier.lower() in TIER_PRICING else "standard"
        pricing = TIER_PRICING[tier_key]
        cost = (p_tok / 1_000_000.0) * pricing["input"] + (c_tok / 1_000_000.0) * pricing["output"]

        rec = {
            "id": f"tok_{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timestamp_ns": int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1_000_000_000),
            "user_id": user_id,
            "agent_id": "hath0r-agent",
            "session_id": session_id,
            "prompt_length_chars": p_len,
            "prompt_tokens": p_tok,
            "completion_length_chars": c_len,
            "completion_tokens": c_tok,
            "total_tokens": tot_tok,
            "model": model,
            "tier": tier,
            "cost_usd": round(cost, 8),
            "latency_ms": 0.0,
            "cached": False,
            "metadata": {},
        }

        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

        return rec

    def list_records(
        self,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
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
                    records.append(data)
                except Exception:
                    continue

        return records[-limit:] if limit > 0 else records

    def histogram(
        self,
        metric: str = "prompt_tokens",
        user_id: Optional[str] = None,
        bins_count: int = 10,
        max_bar_width: int = 25,
    ) -> Dict[str, Any]:
        """Generate statistical histogram of token telemetry records."""
        records = self.list_records(user_id=user_id, limit=10_000)
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
            bins = [{
                "bin_index": 0,
                "bin_start": v_min,
                "bin_end": v_max,
                "count": tot_recs,
                "percentage": 100.0,
                "cumulative_percentage": 100.0,
                "ascii_bar": "█" * max_bar_width,
            }]
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
                bins.append({
                    "bin_index": i,
                    "bin_start": round(st, 1),
                    "bin_end": round(en, 1),
                    "count": c,
                    "percentage": round((c / tot_recs) * 100.0, 1),
                    "cumulative_percentage": round((cum / tot_recs) * 100.0, 1),
                    "ascii_bar": "█" * bar_len,
                })

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
