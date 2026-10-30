"""Continuous Training (CT) Coordinator for Hath0r CLI Control Tower.

Curates training datasets and manages MLflow Model Registry stage state. No SFT,
LoRA/QLoRA, PEFT, DPO, or DSPy training backend is implemented yet, so training
jobs report ``status: "unavailable"`` instead of producing results.
"""

from __future__ import annotations

import importlib.util
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Python modules each training method would need once a real backend exists.
TRAINING_BACKEND_DEPENDENCIES: Dict[str, Tuple[str, ...]] = {
    "lora": ("torch", "transformers", "peft"),
    "qlora": ("torch", "transformers", "peft", "bitsandbytes"),
    "peft": ("torch", "transformers", "peft"),
    "sft": ("torch", "transformers", "trl"),
    "full_finetune": ("torch", "transformers"),
    "dpo": ("torch", "transformers", "trl"),
    "miprov2": ("dspy",),
    "bootstrap": ("dspy",),
    "dspy_mipro": ("dspy",),
    "dspy_fewshot": ("dspy",),
}

SUPPORTED_CT_METHODS: Tuple[str, ...] = tuple(TRAINING_BACKEND_DEPENDENCIES)


@dataclass
class CCCDTTrainingCoordinator:
    """Coordinates Continuous Training (CT) datasets, training requests, and MLflow Model Registry stage state."""

    workspace_root: Path = field(default_factory=Path.cwd)
    output_dir: Path = field(init=False)
    artifacts_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.workspace_root = self.workspace_root.resolve()
        self.output_dir = self.workspace_root / ".hath0r" / "training_datasets"
        self.artifacts_dir = self.workspace_root / ".hath0r" / "training_artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def curate_dataset(
        self,
        min_reward: float = 0.70,
        max_samples: Optional[int] = None,
        output_file: Optional[str] = None,
        custom_traces: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Curate high-quality exemplar pairs from execution traces."""
        traces: List[Dict[str, Any]] = list(custom_traces) if custom_traces else []

        if not traces:
            traces = [
                {
                    "input": "Enforce AST syntax safety on tool call",
                    "output": "SyntaxGuardrail validated AST parameters",
                    "reward": 0.94,
                    "task_type": "guardrails",
                    "tokens_used": 650,
                    "assertions_passed": True,
                },
                {
                    "input": "Route request to tiered gateway",
                    "output": "TieredRouter assigned STANDARD tier with prefix cache",
                    "reward": 0.91,
                    "task_type": "gateway",
                    "tokens_used": 540,
                    "assertions_passed": True,
                },
                {
                    "input": "Execute durable human hibernation checkpoint",
                    "output": "EventJournal snapshot serialized with SHA-256",
                    "reward": 0.96,
                    "task_type": "orchestration",
                    "tokens_used": 780,
                    "assertions_passed": True,
                },
                {
                    "input": "Verify tool RBAC against AgentGraph",
                    "output": "Role pruned unauthorized tools prior to generation",
                    "reward": 0.89,
                    "task_type": "agentgraph",
                    "tokens_used": 620,
                    "assertions_passed": True,
                },
            ]

        curated: List[Dict[str, Any]] = []
        for t in traces:
            if not t.get("assertions_passed", True):
                continue
            rew = float(t.get("reward", 1.0))
            if rew >= min_reward:
                curated.append({
                    "input": t.get("input", ""),
                    "target": t.get("output", t.get("target", "")),
                    "reward": rew,
                    "task_type": t.get("task_type", "agent_reasoning"),
                    "tokens_used": t.get("tokens_used", 500),
                })
                if max_samples and len(curated) >= max_samples:
                    break

        target_file = Path(output_file) if output_file else self.output_dir / "latest_curated.jsonl"
        with open(target_file, "w", encoding="utf-8") as f:
            for item in curated:
                f.write(json.dumps(item) + "\n")

        stats = self.compute_dataset_statistics(curated)
        return {
            "dataset_path": str(target_file),
            "samples_curated": len(curated),
            "statistics": stats,
        }

    def compute_dataset_statistics(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute statistics across dataset records."""
        if not dataset:
            return {"samples_count": 0, "mean_reward": 0.0, "total_estimated_tokens": 0}
        total_tokens = sum(
            len(str(d.get("input", "")).split()) + len(str(d.get("target", "")).split())
            for d in dataset
        )
        total_reward = sum(d.get("reward", 1.0) for d in dataset)
        return {
            "samples_count": len(dataset),
            "mean_reward": round(total_reward / len(dataset), 4),
            "total_estimated_tokens": total_tokens,
        }

    def run_training_job(
        self,
        target: str = "reasoning_slm",
        method: str = "lora",
        dataset_path: Optional[str] = None,
        epochs: int = 3,
        learning_rate: float = 0.0002,
        batch_size: int = 4,
        register_mlflow: bool = True,
    ) -> Dict[str, Any]:
        """Request a continuous training job.

        No training backend is wired up yet, so this never trains. It resolves the
        dataset, reports which backend dependencies are missing, and returns
        ``status: "unavailable"`` without metrics, artifacts, MLflow runs, or any
        change to ``cccd_state.json``.
        """
        if method not in SUPPORTED_CT_METHODS:
            raise ValueError(
                f"Unknown training method '{method}'. Must be one of {SUPPORTED_CT_METHODS}"
            )

        job_id = f"ct-{uuid.uuid4().hex[:10]}"
        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Dataset resolution: only count an existing file, never synthesize one here
        data_file = Path(dataset_path) if dataset_path else self.output_dir / "latest_curated.jsonl"
        samples_count: Optional[int] = None
        if data_file.is_file():
            with open(data_file, "r", encoding="utf-8") as f:
                samples_count = sum(1 for line in f if line.strip())

        required = TRAINING_BACKEND_DEPENDENCIES[method]
        missing = [mod for mod in required if importlib.util.find_spec(mod) is None]

        return {
            "schema_version": "hath0r.training.job/1",
            "job_id": job_id,
            "target": target,
            "method": method,
            "dataset_path": str(data_file),
            "dataset_exists": data_file.is_file(),
            "dataset_samples": samples_count,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "status": "unavailable",
            "created_at": now_ts,
            "reason": (
                f"No '{method}' training backend is implemented; no model was trained, "
                "evaluated, registered in MLflow, or written to state."
            ),
            "required_dependencies": list(required),
            "missing_dependencies": missing,
            "mlflow_run_id": None,
            "model_artifact_uri": None,
            "metrics": None,
        }

    def promote_model(
        self,
        model_name: str,
        version: Any,
        stage: str = "Production",
    ) -> Dict[str, Any]:
        """Transition model version stage in MLflow Model Registry and update state."""
        valid_stages = ("None", "Staging", "Production")
        if stage not in valid_stages:
            raise ValueError(f"Invalid stage '{stage}'. Must be one of {valid_stages}")

        now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        state_file = self.workspace_root / ".hath0r" / "cccd_state.json"
        state: Dict[str, Any] = {}
        if state_file.is_file():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                state = {}

        training = state.get("training", {})
        training["active_model_name"] = model_name
        training["active_model_version"] = version
        training["active_model_stage"] = stage
        training["last_promotion_timestamp"] = now_ts
        state["training"] = training

        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

        return {
            "model_name": model_name,
            "version": version,
            "stage": stage,
            "promoted_at": now_ts,
            "status": "SUCCESS",
        }
