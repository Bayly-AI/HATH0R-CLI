"""RootCauseBot: Pareto, Ishikawa (fishbone) and 5 Whys for Hath0r failures (WS9, #591).

Failed eval gates (and any failure tagged by hand: CI, red-team, Andon) get a cause category from
``cfg/quality/cause-categories.yaml`` (the 6M adapted to agents). ``pareto`` ranks categories and
gates so effort goes to the vital few; ``fishbone`` and ``why`` record the analysis for one issue
in ``.hath0r/rca/<issue>.json``, and every completed 5 Whys is compounded as an insight node.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from hath0r_cli.qa.paths import write_state_json

CATEGORIES_FILE = Path("cfg") / "quality" / "cause-categories.yaml"
FALLBACK_CATEGORIES = ["method", "model", "material", "measurement", "machine", "operator"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


@dataclass
class RootCauseBot:
    """Tags failures with causes, builds Pareto tables and stores fishbone and 5 Whys records."""

    cwd: Path = field(default_factory=Path.cwd)

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.rca_dir = self.cwd / ".hath0r" / "rca"
        self.tags_path = self.rca_dir / "tags.json"

    # ----------------------------------------------------------- categories
    def categories(self) -> List[Dict[str, Any]]:
        for base in (self.cwd, Path(__file__).resolve().parents[3]):
            path = base / CATEGORIES_FILE
            if path.is_file():
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                return list(data.get("categories") or [])
        return [{"id": c, "label": c.title(), "keywords": []} for c in FALLBACK_CATEGORIES]

    def _category_ids(self) -> List[str]:
        return [c["id"] for c in self.categories()]

    def classify(self, text: str) -> str:
        low = f" {text.lower()} "
        for cat in self.categories():
            if any(str(k).lower() in low for k in cat.get("keywords") or []):
                return str(cat["id"])
        return "unclassified"

    # ----------------------------------------------------------------- tags
    def _tags(self) -> List[Dict[str, Any]]:
        if not self.tags_path.is_file():
            return []
        return list(json.loads(self.tags_path.read_text(encoding="utf-8")))

    def _write_json(self, name: str, payload: Any) -> None:
        write_state_json(self.rca_dir, name, payload)

    def tag(self, *, source: str, ref: str, summary: str, category: Optional[str] = None, gate: Optional[str] = None, issue: Optional[int] = None) -> Dict[str, Any]:
        """Tag one failure. ``category`` defaults to keyword classification of ``summary``."""
        cat = category or self.classify(summary)
        valid = self._category_ids() + ["unclassified"]
        if cat not in valid:
            raise ValueError(f"unknown cause category '{cat}'. Choose one of: {', '.join(valid)}")
        tags = self._tags()
        existing = next((t for t in tags if t["source"] == source and t["ref"] == ref and t.get("gate") == gate), None)
        if existing:
            if category:
                existing["category"] = category
                existing["classified_by"] = "operator"
            self._write_json(self.tags_path.name, tags)
            return {"success": True, "created": False, **existing}
        rec = {
            "id": f"rca-{uuid.uuid4().hex[:8]}",
            "source": source,
            "ref": ref,
            "gate": gate,
            "summary": summary,
            "category": cat,
            "classified_by": "operator" if category else "keywords",
            "issue": issue,
            "tagged_at": _now().isoformat(),
        }
        tags.append(rec)
        self._write_json(self.tags_path.name, tags)
        return {"success": True, "created": True, **rec}

    @staticmethod
    def _gate_name(reason: str) -> str:
        m = re.search(r"(tier\s*\d)[^a-z]*([a-z_]+)?", reason.lower())
        if m:
            return (m.group(1).replace(" ", "") + (f":{m.group(2)}" if m.group(2) else "")).strip(":")
        return reason.lower().split(":")[0][:40].strip() or "gate"

    def auto_tag(self) -> Dict[str, Any]:
        """Tag every blocking reason of every failed scorecard in the eval history (idempotent)."""
        hist = self.cwd / ".hath0r" / "evals" / "history"
        created = 0
        seen = 0
        for f in sorted(hist.glob("*.json")) if hist.is_dir() else []:
            try:
                card = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if card.get("passed_gate", True):
                continue
            reasons = card.get("blocking_reasons") or ["gate failed with no reason recorded"]
            for reason in reasons:
                seen += 1
                res = self.tag(source="eval", ref=str(card.get("eval_id", f.stem)), summary=str(reason), gate=self._gate_name(str(reason)))
                created += int(res["created"])
        return {"success": True, "failures_seen": seen, "tags_created": created}

    # --------------------------------------------------------------- pareto
    def pareto(self, since_days: Optional[int] = 30, by: str = "category", refresh: bool = True) -> Dict[str, Any]:
        if by not in ("category", "gate", "source"):
            raise ValueError("by must be category, gate or source")
        if refresh:
            self.auto_tag()
        cutoff = _now() - timedelta(days=since_days) if since_days else None
        rows = [t for t in self._tags() if not cutoff or ((_parse_ts(t.get("tagged_at", "")) or _now()) >= cutoff)]
        counts: Dict[str, int] = {}
        for t in rows:
            key = str(t.get(by) or "unknown")
            counts[key] = counts.get(key, 0) + 1
        total = sum(counts.values())
        table: List[Dict[str, Any]] = []
        cum = 0
        for key, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            cum += n
            table.append({by: key, "count": n, "pct": round(100.0 * n / total, 2), "cumulative_pct": round(100.0 * cum / total, 2)})
        vital = []
        for row in table:
            vital.append(row[by])
            if float(row["cumulative_pct"]) >= 80.0:
                break
        out = {
            "success": True,
            "schema_version": "hath0r.rca.pareto/v1",
            "by": by,
            "since_days": since_days,
            "total": total,
            "table": table,
            "vital_few": vital if total else [],
            "top": table[0][by] if table else None,
            "unclassified": counts.get("unclassified", 0) if by == "category" else None,
            "generated_at": _now().isoformat(),
        }
        self._write_json("pareto-latest.json", out)
        return out

    # ------------------------------------------------------- fishbone / whys
    def _record_path(self, issue: int) -> Path:
        return self.rca_dir / f"{int(issue)}.json"

    def record(self, issue: int) -> Dict[str, Any]:
        path = self._record_path(issue)
        if path.is_file():
            return dict(json.loads(path.read_text(encoding="utf-8")))
        return {"schema_version": "hath0r.rca/v1", "issue": int(issue), "problem": None, "fishbone": {c: [] for c in self._category_ids()}, "whys": None, "created_at": _now().isoformat()}

    def fishbone(self, issue: int, problem: Optional[str] = None, category: Optional[str] = None, cause: Optional[str] = None) -> Dict[str, Any]:
        """Show, or add a cause to, the Ishikawa diagram for an issue."""
        rec = self.record(issue)
        if problem:
            rec["problem"] = problem
        if cause:
            cat = category or self.classify(cause)
            if cat not in rec["fishbone"]:
                raise ValueError(f"unknown cause category '{cat}'. Choose one of: {', '.join(rec['fishbone'])}")
            if cause not in rec["fishbone"][cat]:
                rec["fishbone"][cat].append(cause)
        if problem or cause:
            rec["updated_at"] = _now().isoformat()
            self._write_json(f"{int(issue)}.json", rec)
        return {"success": True, **rec}

    def why(self, issue: int, problem: str, whys: List[str], root_cause: Optional[str] = None, category: Optional[str] = None, compound: bool = True) -> Dict[str, Any]:
        """Record a 5 Whys chain. Needs 3 to 5 answers; the last answer is the root cause unless given."""
        chain = [w.strip() for w in whys if w and w.strip()]
        if not 3 <= len(chain) <= 5:
            raise ValueError("a 5 Whys record needs 3 to 5 answers")
        rec = self.record(issue)
        root = root_cause or chain[-1]
        cat = category or self.classify(root)
        rec["problem"] = rec.get("problem") or problem
        rec["whys"] = {"problem": problem, "chain": chain, "root_cause": root, "category": cat, "recorded_at": _now().isoformat()}
        if cat in rec["fishbone"] and root not in rec["fishbone"][cat]:
            rec["fishbone"][cat].append(root)
        self._write_json(f"{int(issue)}.json", rec)
        if compound:
            try:
                from hath0r_cli.bots.memory_manager import MemoryManagerBot

                MemoryManagerBot(cwd=self.cwd).compound_memory(
                    node_id=f"insight:rca:{int(issue)}",
                    node_type="insight",
                    label=f"Root cause of #{int(issue)} ({cat}): {root}",
                    content=f"Problem: {problem}. Whys: " + " -> ".join(chain),
                    tags=["rca", "5-whys", cat],
                    source_files=[f".hath0r/rca/{int(issue)}.json"],
                    sync_agentgraph=False,
                )
            except Exception as exc:  # the RCA record is the source of truth
                rec["warning"] = f"memory compounding failed: {exc}"
        return {"success": True, **rec}

    def gate(self) -> Dict[str, Any]:
        """Workflow step after a failed eval: tag the failure so the monthly Pareto sees it."""
        res = self.auto_tag()
        return {"success": True, **res}

    def status(self) -> Dict[str, Any]:
        return {"success": True, "bot_id": "root-cause-bot", "tags": len(self._tags()), "records": len(list(self.rca_dir.glob("[0-9]*.json"))) if self.rca_dir.is_dir() else 0}
