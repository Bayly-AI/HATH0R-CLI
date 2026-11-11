"""FMEABot: failure mode and effects analysis of Hath0r workflows (WS4, #590).

Each worksheet (``.hath0r/fmea/<process>.yaml``) lists failure modes of one factory workflow with
severity, occurrence and detection (1-10), the RPN and the AIAG-VDA style action priority
(``hath0r_cli.qa.fmea``). Worksheets are seeded from the 14-mode multi-agent failure taxonomy
(MAST: Cemri et al., 2025) mapped to the workflow's steps. Occurrence is refreshed from eval
history and the Andon ledger where a row names a data signal. High-priority rows are filed as
GitHub issues through ``IssueManagerBot`` and exported to AgentGraph as memory concept nodes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from hath0r_cli.qa.fmea import AP_ORDER, occurrence_from_rate, rank_key, score_row

SCHEMA = "hath0r.fmea/v1"

# (code, category, failure mode, effect, cause, S, O, D, detected_by, step keywords, data signal)
MAST_TAXONOMY: List[tuple] = [
    ("FM-1.1", "specification", "Disobeys the task specification", "Work does not meet the issue's acceptance criteria", "Ambiguous or ignored issue scope", 8, 5, 5, "task-evaluator-bot", ("eval", "validate"), "tier:goal_alignment"),
    ("FM-1.2", "specification", "Disobeys its role specification", "A bot acts outside its owning service", "Role prompt or RBAC not enforced", 7, 3, 6, "agentgraph-bot", ("route", "agentgraph"), None),
    ("FM-1.3", "specification", "Repeats a step", "Duplicate PRs, commits or tokens spent twice", "No idempotency check on the step", 5, 4, 5, "git-janitor-bot", ("create", "push", "pr"), None),
    ("FM-1.4", "specification", "Loses conversation history", "Decisions made earlier are contradicted", "Context not handed over in a HAHP envelope", 6, 4, 7, "memory-manager-bot", ("memory", "compound"), None),
    ("FM-1.5", "specification", "Unaware of termination conditions", "Runs past the budget or never finishes", "No stop condition or budget guard", 7, 3, 4, "token-tree-budget-guard", ("monitor", "wait"), "andon:token-tree-budget-guard"),
    ("FM-2.1", "inter-agent", "Conversation reset", "Work restarts and loses progress", "Session state not persisted", 5, 3, 6, "memory-manager-bot", ("session",), None),
    ("FM-2.2", "inter-agent", "Fails to ask for clarification", "Builds the wrong thing on a guess", "No decision-radar request on ambiguity", 7, 5, 7, "decision-radar-bot", ("decision", "plan"), "clarity:unasked"),
    ("FM-2.3", "inter-agent", "Task derailment", "Effort spent off the issue's goal", "Goal not re-checked between steps", 6, 4, 5, "task-evaluator-bot", ("eval",), "tier:goal_alignment"),
    ("FM-2.4", "inter-agent", "Withholds information", "A later step decides without a known fact", "Facts not written to memory or the envelope", 6, 3, 7, "memory-manager-bot", ("compound", "summary"), None),
    ("FM-2.5", "inter-agent", "Ignores another agent's input", "Review findings or failed checks are dropped", "Step result not read by the next step", 8, 4, 5, "antagonistic-review-bot", ("review", "checks"), "tier:adversarial"),
    ("FM-2.6", "inter-agent", "Reasoning and action mismatch", "Says one thing, changes another", "No diff check against the stated plan", 7, 4, 6, "antagonistic-review-bot", ("review", "diff"), "tier:adversarial"),
    ("FM-3.1", "verification", "Premature termination", "Announced complete before gates pass", "Announcement not gated", 9, 3, 3, "task-announcer-bot", ("announce", "merge"), "gate:escape"),
    ("FM-3.2", "verification", "No or incomplete verification", "Defects reach development", "Tests or evals skipped", 9, 4, 4, "task-evaluator-bot", ("test", "eval", "pre-deploy"), "gate:escape"),
    ("FM-3.3", "verification", "Incorrect verification", "A broken change passes the gate", "Gauge cannot discriminate good from bad", 9, 3, 6, "measurement-system-bot", ("eval", "verify"), "msa:missed_defects"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FMEABot:
    """Owns FMEA worksheets, scoring, ranking, issue sync and AgentGraph export."""

    cwd: Path = field(default_factory=Path.cwd)

    def __post_init__(self) -> None:
        self.cwd = Path(self.cwd).resolve()
        self.fmea_dir = self.cwd / ".hath0r" / "fmea"

    # --------------------------------------------------------------- storage
    def _path(self, process: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", process):
            raise ValueError(f"process name must be kebab-case, got '{process}'")
        return self.fmea_dir / f"{process}.yaml"

    def load(self, process: str) -> Dict[str, Any]:
        path = self._path(process)
        if not path.is_file():
            raise FileNotFoundError(f"No FMEA worksheet for '{process}'. Run 'hath0r fmea init {process}'.")
        return dict(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def save(self, sheet: Dict[str, Any]) -> Path:
        path = self._path(sheet["process"])
        path.parent.mkdir(parents=True, exist_ok=True)
        sheet["updated_at"] = _now()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(yaml.safe_dump(sheet, sort_keys=False, allow_unicode=True), encoding="utf-8")
        os.replace(tmp, path)
        return path

    def processes(self) -> List[str]:
        return sorted(p.stem for p in self.fmea_dir.glob("*.yaml")) if self.fmea_dir.is_dir() else []

    # ------------------------------------------------------------------ init
    def _factory_steps(self, factory: Path) -> List[Dict[str, str]]:
        if not factory.is_file():
            return []
        data = yaml.safe_load(factory.read_text(encoding="utf-8")) or {}
        steps: List[Dict[str, str]] = []
        for wf in data.get("workflows") or []:
            for i, st in enumerate(wf.get("steps") or [], start=1):
                if isinstance(st, dict):
                    steps.append({"id": str(st.get("id") or f"{wf.get('id')}-{i}"), "bot": str(st.get("bot", "")), "action": str(st.get("action", ""))})
        return steps

    def init(self, process: str, factory: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """Create a worksheet seeded with the 14 MAST failure modes mapped to the workflow's steps."""
        path = self._path(process)
        if path.is_file() and not force:
            raise FileExistsError(f"{path} exists; use --force to reseed it")
        fac = factory or f"cfg/factories/{process}-factory.yaml"
        steps = self._factory_steps(self.cwd / fac)
        rows: List[Dict[str, Any]] = []
        prefix = "".join(w[0] for w in process.split("-")).upper()
        for n, (code, cat, mode, effect, cause, s, o, d, det, keys, signal) in enumerate(MAST_TAXONOMY, start=1):
            match = next((st for st in steps if any(k in f"{st['bot']} {st['action']} {st['id']}".lower() for k in keys)), None)
            rows.append(
                {
                    "id": f"{prefix}-{n:02d}",
                    "taxonomy": code,
                    "category": cat,
                    "step": match["id"] if match else "workflow",
                    "step_bot": match["bot"] if match else None,
                    "failure_mode": mode,
                    "effect": effect,
                    "cause": cause,
                    "severity": s,
                    "occurrence": o,
                    "detection": d,
                    "detected_by": det,
                    "occurrence_signal": signal,
                    "occurrence_source": "seed",
                    "actions": [],
                    "issue": None,
                }
            )
        sheet = {"schema_version": SCHEMA, "process": process, "factory": fac, "created_at": _now(), "rows": [score_row(r) for r in rows], "history": []}
        self.save(sheet)
        return {"success": True, "process": process, "path": str(path), "rows": len(rows), "steps_mapped": sum(1 for r in rows if r["step"] != "workflow")}

    def add(self, process: str, *, step: str, failure_mode: str, effect: str, cause: str, severity: int, occurrence: int, detection: int, detected_by: str = "", signal: Optional[str] = None) -> Dict[str, Any]:
        sheet = self.load(process)
        prefix = "".join(w[0] for w in process.split("-")).upper()
        n = max([int(str(r["id"]).rsplit("-", 1)[-1]) for r in sheet["rows"] if str(r["id"]).rsplit("-", 1)[-1].isdigit()] + [0]) + 1
        row = score_row({
            "id": f"{prefix}-{n:02d}", "taxonomy": None, "category": "custom", "step": step, "step_bot": None,
            "failure_mode": failure_mode, "effect": effect, "cause": cause, "severity": severity, "occurrence": occurrence,
            "detection": detection, "detected_by": detected_by, "occurrence_signal": signal, "occurrence_source": "manual",
            "actions": [], "issue": None,
        })
        sheet["rows"].append(row)
        self.save(sheet)
        return {"success": True, "process": process, "row": row}

    def update(self, process: str, row_id: str, **changes: Any) -> Dict[str, Any]:
        """Change ratings after an action (for example detection improves when a guard lands)."""
        sheet = self.load(process)
        row = next((r for r in sheet["rows"] if r["id"] == row_id), None)
        if row is None:
            raise ValueError(f"no row '{row_id}' in {process}")
        action = changes.pop("action", None)
        row.update({k: v for k, v in changes.items() if v is not None})
        if changes.get("occurrence") is not None:
            # A hand rating holds until the row's data signal has enough samples to replace it.
            row["occurrence_source"] = "manual"
            row.pop("observed_rate", None)
        if action:
            row.setdefault("actions", []).append({"at": _now(), "action": action})
        new = score_row(row)
        row.update(new)
        self.save(sheet)
        return {"success": True, "process": process, "row": row}

    # ----------------------------------------------------------------- score
    def _signal_rate(self, signal: str) -> Optional[float]:
        hist = self.cwd / ".hath0r" / "evals" / "history"
        cards: List[Dict[str, Any]] = []
        if hist.is_dir():
            for f in hist.glob("*.json"):
                try:
                    cards.append(json.loads(f.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        if signal == "gate:escape":
            from hath0r_cli.qa.gates import escape_rate

            return escape_rate(self.cwd)
        if signal == "clarity:unasked":
            from hath0r_cli.qa.clarity import unasked_rate

            return unasked_rate(self.cwd)
        if signal == "eval_fail_rate":
            return sum(1 for c in cards if not c.get("passed_gate")) / len(cards) if cards else None
        if signal.startswith("tier:"):
            tier = signal.split(":", 1)[1]
            flags = [c.get("tiers", {}).get(tier, {}).get("passed") for c in cards]
            flags = [bool(f) for f in flags if f is not None]
            return sum(1 for f in flags if not f) / len(flags) if flags else None
        if signal.startswith("andon:"):
            src = signal.split(":", 1)[1]
            ledger = self.cwd / ".hath0r" / "state" / "andon" / "events.jsonl"
            if not ledger.is_file() or not cards:
                return None
            hits = sum(1 for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip() and json.loads(line).get("source") == src and json.loads(line).get("type") == "event")
            return hits / max(1, len(cards))
        if signal == "msa:missed_defects":
            latest = self.cwd / ".hath0r" / "evals" / "msa" / "latest.json"
            if not latest.is_file():
                return None
            aa = json.loads(latest.read_text(encoding="utf-8")).get("attribute_agreement", {})
            return float(aa.get("miss_rate", 0.0))
        return None

    def score(self, process: str, refresh: bool = True) -> Dict[str, Any]:
        """Refresh occurrence from data where a row names a signal, rescore and rank."""
        sheet = self.load(process)
        refreshed = []
        for row in sheet["rows"]:
            sig = row.get("occurrence_signal")
            if refresh and sig:
                rate = self._signal_rate(str(sig))
                if rate is not None:
                    new_o = occurrence_from_rate(rate)
                    if new_o != row["occurrence"]:
                        refreshed.append({"id": row["id"], "from": row["occurrence"], "to": new_o, "rate": round(rate, 4)})
                    row["occurrence"] = new_o
                    row["occurrence_source"] = f"data:{sig}"
                    row["observed_rate"] = round(rate, 4)
            row.update(score_row(row))
        sheet["rows"].sort(key=rank_key)
        sheet.setdefault("history", []).append({"at": _now(), "total_rpn": sum(r["rpn"] for r in sheet["rows"]), "high": sum(1 for r in sheet["rows"] if r["action_priority"] == "H")})
        sheet["history"] = sheet["history"][-50:]
        self.save(sheet)
        return {"success": True, "process": process, "refreshed": refreshed, "rows": sheet["rows"], **self._counts(sheet["rows"])}

    @staticmethod
    def _counts(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"high": sum(1 for r in rows if r["action_priority"] == "H"), "medium": sum(1 for r in rows if r["action_priority"] == "M"), "low": sum(1 for r in rows if r["action_priority"] == "L"), "total_rpn": sum(int(r["rpn"]) for r in rows)}

    def report(self, process: Optional[str] = None, top: int = 10) -> Dict[str, Any]:
        procs = [process] if process else self.processes()
        rows: List[Dict[str, Any]] = []
        sheets = {}
        for p in procs:
            sheet = self.load(p)
            sheets[p] = {**self._counts(sheet["rows"]), "factory": sheet.get("factory"), "updated_at": sheet.get("updated_at")}
            rows.extend({**r, "process": p} for r in sheet["rows"])
        rows.sort(key=rank_key)
        return {"success": True, "schema_version": SCHEMA, "processes": sheets, "top": rows[:top], **self._counts(rows)}

    # ------------------------------------------------------------ issue sync
    def _issue_body(self, process: str, row: Dict[str, Any]) -> str:
        return (
            f"## Summary\n\nFMEA row `{row['id']}` in the `{process}` worksheet has action priority "
            f"**{row['action_priority']}** (S={row['severity']}, O={row['occurrence']}, D={row['detection']}, RPN={row['rpn']}).\n\n"
            f"- Step: `{row['step']}`\n- Failure mode: {row['failure_mode']}\n- Effect: {row['effect']}\n"
            f"- Cause: {row['cause']}\n- Detected by: `{row.get('detected_by') or 'nothing yet'}`\n"
            f"- Taxonomy: {row.get('taxonomy') or 'custom'}\n\n"
            "## Acceptance Criteria\n\n"
            "- [ ] An action lowers severity, occurrence or detection for this row\n"
            f"- [ ] `hath0r fmea update {process} {row['id']} ...` records the new ratings and the action\n"
            f"- [ ] `hath0r fmea score {process}` shows this row below action priority H\n\n"
            "Filed by `fmea-bot` (epic #580, WS4)."
        )

    def sync_issues(self, process: str, repo: str = "Bayly-AI/HATH0R-CLI", min_priority: str = "H", dry_run: bool = False, issue_bot: Any = None) -> Dict[str, Any]:
        """File one GitHub issue per row at or above ``min_priority`` that has none yet."""
        if min_priority not in AP_ORDER:
            raise ValueError("min_priority must be H, M or L")
        sheet = self.load(process)
        if issue_bot is None:
            from hath0r_cli.bots.issue_manager import IssueManagerBot

            issue_bot = IssueManagerBot(cwd=self.cwd)
        created, skipped, failed = [], [], []
        for row in sheet["rows"]:
            if AP_ORDER[row["action_priority"]] < AP_ORDER[min_priority]:
                continue
            if row.get("issue"):
                skipped.append(row["id"])
                continue
            title = f"FMEA {row['action_priority']}: {process} {row['id']} {row['failure_mode']}"
            res = issue_bot.create_issue(repo=repo, title=title, body=self._issue_body(process, row), dry_run=dry_run)
            if res.get("success"):
                if not dry_run:
                    row["issue"] = res.get("issue_number") or res.get("url")
                created.append({"id": row["id"], "issue": res.get("issue_number"), "url": res.get("url"), "dry_run": dry_run})
            else:
                failed.append({"id": row["id"], "error": res.get("error")})
        if not dry_run:
            self.save(sheet)
        return {"success": not failed, "process": process, "created": created, "skipped": skipped, "failed": failed}

    # -------------------------------------------------------- agentgraph
    def export_agentgraph(self, process: str, min_priority: str = "M") -> Dict[str, Any]:
        """Compound rows at or above ``min_priority`` as memory concept nodes (ingested by AgentGraph)."""
        from hath0r_cli.bots.memory_manager import MemoryManagerBot

        sheet = self.load(process)
        mbot = MemoryManagerBot(cwd=self.cwd)
        exported = []
        for row in sheet["rows"]:
            if AP_ORDER[row["action_priority"]] < AP_ORDER[min_priority]:
                continue
            node_id = f"concept:fmea:{process}:{row['id']}"
            mbot.compound_memory(
                node_id=node_id,
                node_type="concept",
                label=f"FMEA {row['action_priority']} {process} {row['id']}: {row['failure_mode']}",
                content=f"Step {row['step']}. Effect: {row['effect']}. Cause: {row['cause']}. S{row['severity']} O{row['occurrence']} D{row['detection']} RPN {row['rpn']}. Detected by {row.get('detected_by')}.",
                tags=["fmea", process, row["action_priority"], str(row.get("taxonomy") or "custom")],
                source_files=[f".hath0r/fmea/{process}.yaml"],
                sync_agentgraph=False,
            )
            exported.append(node_id)
        return {"success": True, "process": process, "exported": exported}

    def review(self, process: str, repo: str = "Bayly-AI/HATH0R-CLI", dry_run: bool = True) -> Dict[str, Any]:
        """Factory step: score, export to AgentGraph and file issues for high-priority rows."""
        scored = self.score(process)
        exported = self.export_agentgraph(process) if not dry_run else {"exported": []}
        issues = self.sync_issues(process, repo=repo, dry_run=dry_run)
        return {"success": issues["success"], "process": process, "high": scored["high"], "exported": exported["exported"], "issues": issues}

    def status(self) -> Dict[str, Any]:
        return {"success": True, "bot_id": "fmea-bot", "worksheets": self.processes()}
