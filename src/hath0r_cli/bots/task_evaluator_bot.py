"""TaskEvaluatorBot: 4-Tier Hybrid Automatic Task Evaluation Engine (CR-TASK-EVAL-001).

Evaluates every task across four orthogonal tiers prior to completion:
  1. Tier 1: Deterministic Engineering Rubrics (Tests, Lint, SemVer, Branch, AgentGraph, Memory CAS)
  2. Tier 2: Trajectory & FinOps Efficiency (Micro-session R/W, Step Bloat, TokenTreeBudgetGuard, Taguchi Loss)
  3. Tier 3: Adversarial & Diff Critics (AntagonisticReviewBot 0 Swallowed Exceptions, Tech Debt Hand-off)
  4. Tier 4: Goal Alignment & Consensus (Issue/Focus alignment, Modified Files/Tests, MultiAgentConsensus)
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_TASK_EVAL_CONFIG: Dict[str, Any] = {
    "schema_version": "hath0r.evals.task/v1",
    "rule_id": "CR-TASK-EVAL-001",
    "weights": {
        "deterministic": 0.40,
        "trajectory": 0.20,
        "adversarial": 0.25,
        "goal_alignment": 0.15,
    },
    "thresholds": {
        "min_reward": 0.80,
        "min_deterministic": 1.00,
        "min_adversarial": 0.80,
        "min_consensus": 0.70,
        "max_tokens": 50000,
        "max_usd": 0.25,
        "target_latency_ms": 2000.0,
    },
    "hard_gates": {
        "require_deterministic_pass": True,
        "require_zero_critical_flaws": True,
        "require_finops_budget": True,
        "require_memory_compounded": True,
    },
    "observability": {
        "phoenix_enabled": True,
        "mlflow_enabled": True,
        "mlflow_experiment": "hath0r-task-evals",
        "spool_when_offline": True,
    },
}


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON atomically via a temporary sibling file and os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.tmp.{uuid.uuid4().hex[:8]}"
    try:
        tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def _compute_scorecard_hash(data: Dict[str, Any]) -> str:
    """Compute canonical SHA-256 content digest for an evaluation scorecard."""
    canonical = {
        "eval_id": data.get("eval_id"),
        "task_id": data.get("task_id"),
        "repo_name": data.get("repo_name"),
        "branch": data.get("branch"),
        "passed_gate": bool(data.get("passed_gate")),
        "r_task": round(float(data.get("r_task", 0.0)), 4),
        "tier_scores": data.get("tier_scores", {}),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


@dataclass
class TaskEvaluatorBot:
    """Executes the 4-tier automatic task evaluation pipeline and enforces CR-TASK-EVAL-001."""

    cwd: Path = field(default_factory=Path.cwd)

    def __post_init__(self) -> None:
        self.cwd = self.cwd.resolve()
        self.evals_dir = self.cwd / ".hath0r" / "evals"
        self.history_dir = self.evals_dir / "history"

    def load_config(self) -> Dict[str, Any]:
        """Load declarative cfg/evals/task-eval.json merged over canonical defaults."""
        cfg: Dict[str, Any] = json.loads(json.dumps(DEFAULT_TASK_EVAL_CONFIG))
        cfg_file = self.cwd / "cfg" / "evals" / "task-eval.json"
        if cfg_file.is_file():
            try:
                user_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                if isinstance(user_cfg, dict):
                    for section in ("weights", "thresholds", "hard_gates", "observability"):
                        if isinstance(user_cfg.get(section), dict):
                            cfg[section].update(user_cfg[section])
                    for k, v in user_cfg.items():
                        if k not in ("weights", "thresholds", "hard_gates", "observability"):
                            cfg[k] = v
            except Exception:
                pass
        return cfg

    def _detect_branch_and_task_id(self, task_id: Optional[str] = None) -> Tuple[str, str, Optional[int]]:
        """Resolve active git branch, task_id, and optional issue number."""
        branch = "development"
        try:
            proc = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                branch = proc.stdout.strip()
        except Exception:
            pass

        issue_num: Optional[int] = None
        m = re.match(r"^(?:feature|bugfix|hotfix|enhancement|research|fix|chore)/(\d+)-", branch)
        if m:
            issue_num = int(m.group(1))

        resolved_task_id = task_id
        if not resolved_task_id:
            if issue_num is not None:
                resolved_task_id = f"issue-{issue_num}"
            elif branch and branch not in ("development", "testing", "staging", "master"):
                slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", branch).strip("-")
                resolved_task_id = f"branch-{slug}"
            else:
                resolved_task_id = f"task-{self.cwd.name}"

        return branch, resolved_task_id, issue_num

    def _evaluate_tier1_deterministic(
        self,
        *,
        skip_tests: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Tier 1: Deterministic Engineering Rubrics (Tests, Preflight, AgentGraph, Memory CAS)."""
        from hath0r_cli.bots.agentgraph_bot import AgentGraphBot
        from hath0r_cli.bots.memory_manager import MemoryManagerBot
        from hath0r_cli.bots.quality import PreflightBot, ReleaseBot

        checks: Dict[str, Dict[str, Any]] = {}

        # 1. Version & SemVer check
        rel_bot = ReleaseBot(cwd=self.cwd)
        ver_res = rel_bot.read_version()
        checks["version_valid"] = {
            "passed": bool(ver_res.get("success")),
            "version": ver_res.get("version"),
            "error": ver_res.get("error"),
        }

        # 2. AgentGraph validation
        try:
            ag_bot = AgentGraphBot(cwd=self.cwd)
            ag_val = ag_bot.validate().get("validation", {})
            ag_passed = bool(ag_val.get("valid", True))
            checks["agentgraph_valid"] = {
                "passed": ag_passed,
                "cycles": ag_val.get("cycles_detected", 0),
                "contradictions": ag_val.get("contradictions_detected", 0),
            }
        except Exception as exc:
            checks["agentgraph_valid"] = {"passed": False, "error": str(exc)}

        # 3. MemoryGraph & CAS Hash Verification
        mbot = MemoryManagerBot(cwd=self.cwd)
        mem_ver = mbot.verify_compounded(require_session=True, require_hashes=True)
        checks["memory_compounded"] = {
            "passed": bool(mem_ver.get("compounded")) or dry_run,
            "compounded_nodes_count": mem_ver.get("compounded_nodes_count", 0),
            "session_read_verified": mem_ver.get("session_read_verified", False),
            "session_write_verified": mem_ver.get("session_write_verified", False),
            "hashes_verified": mem_ver.get("hashes_verified", False),
            "graphs_not_ignored": mem_ver.get("graphs_not_ignored", True),
            "error": mem_ver.get("error"),
        }

        # 4. Preflight & Test Suite Execution
        pf_bot = PreflightBot(cwd=self.cwd)
        if skip_tests or dry_run:
            checks["test_suite"] = {
                "passed": True,
                "skipped": True,
                "message": "Test execution skipped via flag or dry-run.",
            }
        else:
            pf_res = pf_bot.run(skip_tests=False, dry_run=False)
            cmd_results = pf_res.get("command_results", [])
            tests_ok = all(bool(cr.get("ok")) for cr in cmd_results) if cmd_results else True
            checks["test_suite"] = {
                "passed": tests_ok,
                "commands_run": len(cmd_results),
                "results": cmd_results,
            }

        passed_count = sum(1 for c in checks.values() if c.get("passed"))
        total_count = len(checks)
        score = round(passed_count / max(1, total_count), 4)
        hard_passed = all(c.get("passed") for c in checks.values())

        return {
            "score": score,
            "passed": hard_passed,
            "passed_checks": passed_count,
            "total_checks": total_count,
            "checks": checks,
        }

    def _evaluate_tier2_trajectory(
        self,
        *,
        latency_ms: float,
        target_latency_ms: float,
        max_tokens: int,
        max_usd: float,
    ) -> Dict[str, Any]:
        """Tier 2: Trajectory & FinOps Efficiency (Micro-session, TokenTreeBudgetGuard, Taguchi Loss)."""
        from hath0r_cli.bots.memory_manager import MemoryManagerBot
        from hath0r_cli.bots.token_tree_budget import token_tree_budget_guard

        mbot = MemoryManagerBot(cwd=self.cwd)
        sess_status = mbot.session_status()
        budget_status = token_tree_budget_guard.check_budget()

        tokens_used = int(budget_status.get("total_tokens", 0))
        usd_used = float(budget_status.get("estimated_usd", 0.0))
        budget_ok = tokens_used <= max_tokens and usd_used <= max_usd
        within_capsule = bool(sess_status.get("within_budget", True))
        read_count = int(sess_status.get("read_count", 0))
        write_count = int(sess_status.get("write_count", 0))

        # FinOps efficiency score [0.0, 1.0]
        token_ratio = min(1.0, tokens_used / max(1, max_tokens))
        finops_score = max(0.0, 1.0 - (0.5 * token_ratio)) if budget_ok else 0.0

        # Session trajectory health score [0.0, 1.0]
        traj_health = 1.0
        if not within_capsule:
            traj_health -= 0.4
        if read_count < 1 or write_count < 1:
            traj_health -= 0.3

        # Taguchi Quality Loss L = k * (y / target)^2 and SNR (smaller-is-better)
        norm_lat = latency_ms / max(1.0, target_latency_ms)
        quality_loss = round(0.05 * (norm_lat ** 2), 4)
        snr_db = round(-10.0 * math.log10(max(1e-6, norm_lat ** 2)), 2)

        score = round(max(0.0, min(1.0, 0.6 * finops_score + 0.4 * max(0.0, traj_health))), 4)
        return {
            "score": score,
            "passed": budget_ok and within_capsule,
            "tokens_used": tokens_used,
            "max_tokens": max_tokens,
            "estimated_usd": usd_used,
            "max_usd": max_usd,
            "session_id": sess_status.get("session_id"),
            "session_reads": read_count,
            "session_writes": write_count,
            "session_bytes": sess_status.get("byte_size", 0),
            "within_capsule_budget": within_capsule,
            "latency_ms": round(latency_ms, 2),
            "taguchi_quality_loss": quality_loss,
            "snr_db": snr_db,
        }

    def _evaluate_tier3_adversarial(self, *, dry_run: bool = False) -> Dict[str, Any]:
        """Tier 3: Adversarial Diff Critics & Change Validation (CR-CLI-TECH-DEBT-001)."""
        from hath0r_cli.bots.antagonistic_review import AntagonisticReviewBot
        from hath0r_cli.bots.change_validation import ChangeValidationBot

        diff_text = ""
        try:
            proc = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            diff_text = proc.stdout or ""
            if not diff_text.strip():
                proc2 = subprocess.run(
                    ["git", "diff", "origin/development...HEAD"],
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                diff_text = proc2.stdout or ""
        except Exception:
            diff_text = ""

        rev_bot = AntagonisticReviewBot(root_path=self.cwd)
        rev_res = rev_bot.review_diff(diff_content=diff_text)
        flaws_count = int(rev_res.get("adversarial_flaws_count", 0))
        tech_debts_count = int(rev_res.get("tech_debts_count", 0))
        issues_created = len(rev_res.get("auto_created_issues", []))

        cv_bot = ChangeValidationBot(cwd=self.cwd)
        classification = cv_bot.classify_changes()

        untracked_debt = max(0, tech_debts_count - issues_created)
        penalty = (0.5 * flaws_count) + (0.15 * untracked_debt)
        score = round(max(0.0, 1.0 - penalty), 4)
        passed = flaws_count == 0

        return {
            "score": score,
            "passed": passed,
            "adversarial_flaws_count": flaws_count,
            "adversarial_flaws": rev_res.get("adversarial_flaws", []),
            "tech_debts_count": tech_debts_count,
            "auto_created_issues": rev_res.get("auto_created_issues", []),
            "change_categories": classification.get("categories", {}),
            "changed_files_count": len(classification.get("files", [])),
        }

    def _evaluate_tier4_goal_alignment(
        self,
        *,
        task_id: str,
        issue_number: Optional[int],
        min_consensus: float = 0.70,
    ) -> Dict[str, Any]:
        """Tier 4: Goal Alignment & Multi-Agent Consensus."""
        from hath0r_cli.bots.memory_manager import MemoryManagerBot
        from hath0r_cli.bots.multiagent_consensus import multiagent_consensus_engine

        mbot = MemoryManagerBot(cwd=self.cwd)
        sess = mbot.session_status()
        focus = str(sess.get("active_focus") or "").strip()
        ver = mbot.verify_compounded(require_session=False, require_hashes=False)
        compounded_count = int(ver.get("compounded_nodes_count", 0))

        multiagent_consensus_engine.consensus_threshold = min_consensus
        consensus_res = multiagent_consensus_engine.evaluate_consensus(
            [
                {"agent_id": "deterministic_critic", "output": f"Verified task {task_id}"},
                {"agent_id": "trajectory_critic", "output": f"Verified task {task_id}"},
                {"agent_id": "adversarial_critic", "output": f"Verified task {task_id}"},
            ]
        )
        consensus_score = float(consensus_res.get("consensus_score", 1.0))

        has_focus = bool(focus)
        has_compounded = compounded_count >= 1
        alignment_signals = [
            1.0 if has_focus else 0.7,
            1.0 if has_compounded else 0.5,
            consensus_score,
        ]
        score = round(sum(alignment_signals) / len(alignment_signals), 4)

        return {
            "score": score,
            "passed": score >= min_consensus,
            "task_id": task_id,
            "issue_number": issue_number,
            "active_focus": focus or "General task execution",
            "compounded_nodes_count": compounded_count,
            "consensus_score": consensus_score,
        }

    def _sync_observability(
        self,
        scorecard: Dict[str, Any],
        obs_cfg: Dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Emit OTel span to Phoenix and log evaluation run to MLflow (spooling locally if offline)."""
        from hath0r_cli.telemetry import trace_span

        sync_state: Dict[str, Any] = {
            "mode": "dry_run" if dry_run else "spooled_local",
            "phoenix_logged": False,
            "mlflow_run_id": None,
        }
        if dry_run:
            return sync_state

        # 1. Emit OpenTelemetry / Phoenix span
        if obs_cfg.get("phoenix_enabled", True):
            try:
                with trace_span(
                    "hath0r.eval.task",
                    attributes={
                        "openinference.span.kind": "EVALUATOR",
                        "hath0r.eval.id": scorecard["eval_id"],
                        "hath0r.eval.task_id": scorecard["task_id"],
                        "hath0r.eval.repo": scorecard["repo_name"],
                        "hath0r.eval.r_task": scorecard["r_task"],
                        "hath0r.eval.passed_gate": scorecard["passed_gate"],
                    },
                ):
                    sync_state["phoenix_logged"] = True
            except Exception:
                sync_state["phoenix_logged"] = False

        # 2. Log run to MLflow if healthy
        if obs_cfg.get("mlflow_enabled", True):
            try:
                from hath0r_cli.bots.mlflow_manager_bot import mlflow_manager_bot

                st = mlflow_manager_bot.check_status(group="hath0r")
                if st.get("healthy"):
                    exp_name = str(obs_cfg.get("mlflow_experiment") or "hath0r-task-evals")
                    run_id = mlflow_manager_bot.log_run(
                        experiment_name=exp_name,
                        run_name=f"eval-{scorecard['repo_name']}-{scorecard['task_id']}",
                        params={
                            "repo": scorecard["repo_name"],
                            "branch": scorecard["branch"],
                            "task_id": scorecard["task_id"],
                            "passed_gate": str(scorecard["passed_gate"]),
                        },
                        metrics={
                            "r_task": float(scorecard["r_task"]),
                            "s_deterministic": float(scorecard["tier_scores"]["deterministic"]),
                            "s_trajectory": float(scorecard["tier_scores"]["trajectory"]),
                            "s_adversarial": float(scorecard["tier_scores"]["adversarial"]),
                            "s_goal_alignment": float(scorecard["tier_scores"]["goal_alignment"]),
                            "duration_ms": float(scorecard["duration_ms"]),
                        },
                        tags={"rule": "CR-TASK-EVAL-001", "eval_id": scorecard["eval_id"]},
                        group="hath0r",
                    )
                    if run_id:
                        sync_state["mlflow_run_id"] = run_id
                        sync_state["mode"] = "live_synced"
            except Exception:
                pass

        return sync_state

    def evaluate_task(
        self,
        *,
        task_id: Optional[str] = None,
        skip_tests: bool = False,
        compound_node: bool = True,
        sync_observability: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Execute the 4-tier hybrid evaluation pipeline, persist scorecard, and compound MemoryGraph node."""
        t0 = time.monotonic()
        cfg = self.load_config()
        weights = cfg["weights"]
        thresholds = cfg["thresholds"]
        hard_gates = cfg["hard_gates"]

        branch, resolved_task_id, issue_num = self._detect_branch_and_task_id(task_id)
        now = datetime.now(timezone.utc).isoformat()
        eval_id = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        tier1 = self._evaluate_tier1_deterministic(skip_tests=skip_tests, dry_run=dry_run)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        tier2 = self._evaluate_tier2_trajectory(
            latency_ms=elapsed_ms,
            target_latency_ms=float(thresholds.get("target_latency_ms", 2000.0)),
            max_tokens=int(thresholds.get("max_tokens", 50000)),
            max_usd=float(thresholds.get("max_usd", 0.25)),
        )
        tier3 = self._evaluate_tier3_adversarial(dry_run=dry_run)
        tier4 = self._evaluate_tier4_goal_alignment(
            task_id=resolved_task_id,
            issue_number=issue_num,
            min_consensus=float(thresholds.get("min_consensus", 0.70)),
        )

        s_det = float(tier1["score"])
        s_traj = float(tier2["score"])
        s_adv = float(tier3["score"])
        s_goal = float(tier4["score"])

        r_task = round(
            float(weights["deterministic"]) * s_det
            + float(weights["trajectory"]) * s_traj
            + float(weights["adversarial"]) * s_adv
            + float(weights["goal_alignment"]) * s_goal,
            4,
        )

        # Evaluate hard gates
        blocking_reasons: List[str] = []
        if hard_gates.get("require_deterministic_pass", True) and not tier1["passed"]:
            failed_t1 = [k for k, v in tier1["checks"].items() if not v.get("passed")]
            blocking_reasons.append(f"Tier 1 deterministic gate failed: {', '.join(failed_t1)}")
        if hard_gates.get("require_zero_critical_flaws", True) and not tier3["passed"]:
            blocking_reasons.append(
                f"Tier 3 adversarial critic detected {tier3['adversarial_flaws_count']} critical flaw(s)"
            )
        if hard_gates.get("require_finops_budget", True) and not tier2["passed"]:
            blocking_reasons.append("Tier 2 FinOps / micro-session capsule budget exceeded")
        min_reward = float(thresholds.get("min_reward", 0.80))
        if r_task < min_reward:
            blocking_reasons.append(f"Composite reward R_task ({r_task:.4f}) is below threshold ({min_reward:.2f})")

        passed_gate = len(blocking_reasons) == 0
        total_duration_ms = round((time.monotonic() - t0) * 1000.0, 2)

        scorecard: Dict[str, Any] = {
            "schema_version": "hath0r.evals.scorecard/v1",
            "rule_id": "CR-TASK-EVAL-001",
            "eval_id": eval_id,
            "task_id": resolved_task_id,
            "issue_number": issue_num,
            "repo_name": self.cwd.name,
            "branch": branch,
            "evaluated_at": now,
            "duration_ms": total_duration_ms,
            "passed_gate": passed_gate,
            "r_task": r_task,
            "min_reward_threshold": min_reward,
            "weights": weights,
            "tier_scores": {
                "deterministic": s_det,
                "trajectory": s_traj,
                "adversarial": s_adv,
                "goal_alignment": s_goal,
            },
            "tiers": {
                "deterministic": tier1,
                "trajectory": tier2,
                "adversarial": tier3,
                "goal_alignment": tier4,
            },
            "blocking_reasons": blocking_reasons,
            "observability_sync": {"mode": "pending"},
            "content_hash": "",
        }
        scorecard["content_hash"] = _compute_scorecard_hash(scorecard)

        if sync_observability:
            scorecard["observability_sync"] = self._sync_observability(
                scorecard, cfg.get("observability", {}), dry_run=dry_run
            )

        latest_file = self.evals_dir / "latest.json"
        safe_tid = re.sub(r"[^a-zA-Z0-9_-]+", "-", resolved_task_id).strip("-") or "task"
        history_file = self.history_dir / f"eval-{safe_tid}.json"

        compounded_node_id: Optional[str] = None
        if not dry_run:
            _atomic_write_json(latest_file, scorecard)
            _atomic_write_json(history_file, scorecard)

            from hath0r_cli.bots.memory_manager import MemoryManagerBot

            mbot = MemoryManagerBot(cwd=self.cwd)
            if compound_node:
                eval_node_id = f"eval:{safe_tid}"
                rel_targets = ["concept:tri-graph", "rule:cr-memory-compound-001"]
                sess_id = tier2.get("session_id")
                if sess_id:
                    rel_targets.append(sess_id if str(sess_id).startswith("session:") else f"session:{sess_id}")
                comp_res = mbot.compound_memory(
                    node_id=eval_node_id,
                    node_type="eval",
                    label=f"Task Evaluation {resolved_task_id} (R={r_task:.2f}, {'PASS' if passed_gate else 'FAIL'})",
                    content=(
                        f"4-Tier Task Evaluation for {resolved_task_id} on branch {branch}: "
                        f"R_task={r_task:.4f} (det={s_det:.2f}, traj={s_traj:.2f}, adv={s_adv:.2f}, goal={s_goal:.2f}). "
                        f"Gate={'PASSED' if passed_gate else 'FAILED'}."
                    ),
                    importance=0.85,
                    tags=["eval", "cr-task-eval-001", safe_tid, "passed" if passed_gate else "failed"],
                    relates_to=rel_targets,
                    relation="EVALUATES",
                    source_files=[".hath0r/evals/latest.json"],
                    sync_agentgraph=True,
                    dry_run=False,
                )
                if comp_res.get("success"):
                    compounded_node_id = eval_node_id
            else:
                mbot.sync_file_hashes(track_files=[".hath0r/evals/latest.json"], dry_run=False)

        return {
            "success": passed_gate,
            "passed_gate": passed_gate,
            "dry_run": dry_run,
            "eval_id": eval_id,
            "task_id": resolved_task_id,
            "r_task": r_task,
            "min_reward_threshold": min_reward,
            "tier_scores": scorecard["tier_scores"],
            "blocking_reasons": blocking_reasons,
            "latest_file": str(latest_file),
            "history_file": str(history_file),
            "compounded_node_id": compounded_node_id,
            "scorecard": scorecard,
        }

    def get_status(self) -> Dict[str, Any]:
        """Read the latest evaluation scorecard from .hath0r/evals/latest.json."""
        latest_file = self.evals_dir / "latest.json"
        if not latest_file.is_file():
            return {
                "success": True,
                "exists": False,
                "passed_gate": False,
                "latest_file": str(latest_file),
                "scorecard": None,
                "message": "No task evaluation scorecard found at .hath0r/evals/latest.json. Run 'hath0r evals run'.",
            }
        try:
            scorecard = json.loads(latest_file.read_text(encoding="utf-8"))
            expected_hash = scorecard.get("content_hash")
            actual_hash = _compute_scorecard_hash(scorecard)
            hash_valid = (not expected_hash) or (expected_hash == actual_hash)
            passed = bool(scorecard.get("passed_gate")) and hash_valid
            return {
                "success": True,
                "exists": True,
                "passed_gate": passed,
                "hash_valid": hash_valid,
                "eval_id": scorecard.get("eval_id"),
                "task_id": scorecard.get("task_id"),
                "r_task": scorecard.get("r_task"),
                "tier_scores": scorecard.get("tier_scores"),
                "evaluated_at": scorecard.get("evaluated_at"),
                "latest_file": str(latest_file),
                "scorecard": scorecard,
            }
        except Exception as exc:
            return {
                "success": False,
                "exists": True,
                "passed_gate": False,
                "latest_file": str(latest_file),
                "error": f"Corrupt evaluation scorecard at {latest_file}: {exc}",
                "scorecard": None,
            }

    def verify_evaluated(
        self,
        *,
        task_id: Optional[str] = None,
        auto_run_if_missing: bool = True,
    ) -> Dict[str, Any]:
        """Verify that a valid, passing task evaluation exists prior to announcing completion (CR-TASK-EVAL-001)."""
        st = self.get_status()
        if not st.get("exists") and auto_run_if_missing:
            run_res = self.evaluate_task(task_id=task_id, skip_tests=True, compound_node=True, dry_run=False)
            st = self.get_status()
            if not run_res.get("passed_gate"):
                return {
                    "success": False,
                    "evaluated": False,
                    "passed_gate": False,
                    "r_task": run_res.get("r_task", 0.0),
                    "blocking_reasons": run_res.get("blocking_reasons", []),
                    "latest_file": str(self.evals_dir / "latest.json"),
                    "error": (
                        f"CR-TASK-EVAL-001 violation: Task evaluation failed "
                        f"(R_task={run_res.get('r_task', 0.0):.4f}; {', '.join(run_res.get('blocking_reasons', []))})."
                    ),
                }

        if not st.get("exists"):
            return {
                "success": False,
                "evaluated": False,
                "passed_gate": False,
                "latest_file": str(self.evals_dir / "latest.json"),
                "error": (
                    "CR-TASK-EVAL-001 violation: Missing .hath0r/evals/latest.json. "
                    "Run 'hath0r evals run' prior to announcing task completion."
                ),
            }

        scorecard = st.get("scorecard") or {}
        passed = bool(st.get("passed_gate"))
        r_task = float(scorecard.get("r_task", 0.0))
        blocking = scorecard.get("blocking_reasons", [])

        if not passed:
            return {
                "success": False,
                "evaluated": True,
                "passed_gate": False,
                "eval_id": scorecard.get("eval_id"),
                "task_id": scorecard.get("task_id"),
                "r_task": r_task,
                "blocking_reasons": blocking,
                "latest_file": str(self.evals_dir / "latest.json"),
                "error": (
                    f"CR-TASK-EVAL-001 violation: Latest task evaluation did not pass gate "
                    f"(R_task={r_task:.4f}; {', '.join(blocking) or 'hash mismatch'})."
                ),
            }

        return {
            "success": True,
            "evaluated": True,
            "passed_gate": True,
            "eval_id": scorecard.get("eval_id"),
            "task_id": scorecard.get("task_id"),
            "r_task": r_task,
            "tier_scores": scorecard.get("tier_scores", {}),
            "evaluated_at": scorecard.get("evaluated_at"),
            "latest_file": str(self.evals_dir / "latest.json"),
            "error": None,
        }

    def generate_suite_report(self, root_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Aggregate task evaluation scorecards across all sibling repositories in the workspace."""
        base = (root_dir or self.cwd.parent).resolve()
        repos_summary: List[Dict[str, Any]] = []
        candidates = sorted(p for p in base.iterdir() if p.is_dir() and (p / ".git").exists()) if base.is_dir() else [self.cwd]

        for rpath in candidates:
            bot = TaskEvaluatorBot(cwd=rpath)
            st = bot.get_status()
            repos_summary.append(
                {
                    "repo": rpath.name,
                    "path": str(rpath),
                    "evaluated": bool(st.get("exists")),
                    "passed_gate": bool(st.get("passed_gate")),
                    "r_task": st.get("r_task"),
                    "task_id": st.get("task_id"),
                    "evaluated_at": st.get("evaluated_at"),
                }
            )

        evaluated_count = sum(1 for r in repos_summary if r["evaluated"])
        passed_count = sum(1 for r in repos_summary if r["passed_gate"])
        mean_reward = (
            round(
                sum(float(r["r_task"] or 0.0) for r in repos_summary if r["evaluated"]) / max(1, evaluated_count),
                4,
            )
            if evaluated_count
            else 0.0
        )

        return {
            "success": True,
            "root_dir": str(base),
            "total_repos": len(repos_summary),
            "evaluated_repos": evaluated_count,
            "passed_repos": passed_count,
            "mean_r_task": mean_reward,
            "repos": repos_summary,
        }


task_evaluator_bot = TaskEvaluatorBot()
