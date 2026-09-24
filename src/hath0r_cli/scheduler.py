"""Factory workflow automation scheduler integration and GitHub Actions sync engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ScheduledWorkflow:
    """Declared scheduled workflow inside a factory."""

    factory_id: str
    factory_name: str
    workflow_id: str
    workflow_name: str
    schedule: str
    next_run: str | None = None
    factory_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {
            "factory_id": self.factory_id,
            "factory_name": self.factory_name,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "schedule": self.schedule,
        }
        if self.next_run:
            res["next_run"] = self.next_run
        if self.factory_file:
            res["factory_file"] = self.factory_file
        return res


def compute_next_run(cron_expr: str, base_time: datetime | None = None) -> str | None:
    """Compute the next ISO UTC execution timestamp for a 5-field cron expression."""
    now = base_time or datetime.now(timezone.utc)
    try:
        from croniter import croniter  # type: ignore[import-untyped]

        itr = croniter(cron_expr, now)
        next_dt: datetime = itr.get_next(datetime)
        if next_dt.tzinfo is None:
            next_dt = next_dt.replace(tzinfo=timezone.utc)
        return next_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def discover_scheduled_workflows(group_root: Path | None = None) -> list[ScheduledWorkflow]:
    """Inspect all factory manifests and return all workflows with declared schedules."""
    cli_repo_root = Path(__file__).resolve().parents[2]
    candidate_dirs: list[Path] = [cli_repo_root / "cfg" / "factories"]
    if group_root:
        candidate_dirs.insert(0, group_root / "cfg" / "factories")

    scheduled: list[ScheduledWorkflow] = []
    seen: set[tuple[str, str]] = set()

    for d in candidate_dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                fid = str(data.get("factory_id", ""))
                fname = str(data.get("name", fid))
                workflows = data.get("workflows", [])
                for wf in workflows:
                    if not isinstance(wf, dict):
                        continue
                    sched = wf.get("schedule")
                    wfid = str(wf.get("id", ""))
                    wfname = str(wf.get("name", wfid))
                    if sched and (fid, wfid) not in seen:
                        seen.add((fid, wfid))
                        sched_str = str(sched).strip()
                        next_iso = compute_next_run(sched_str)
                        scheduled.append(
                            ScheduledWorkflow(
                                factory_id=fid,
                                factory_name=fname,
                                workflow_id=wfid,
                                workflow_name=wfname,
                                schedule=sched_str,
                                next_run=next_iso,
                                factory_file=str(f),
                            )
                        )
            except Exception:
                continue

    return scheduled


def generate_github_workflow_content(
    item: ScheduledWorkflow,
    repo: str | None = None,
) -> str:
    """Generate YAML content for a standalone GitHub Actions cron workflow."""
    wf_title = f"Factory Schedule: {item.factory_name} - {item.workflow_name}"
    target_repo = repo or "${{ github.repository }}"
    cron_expr = item.schedule

    content = f"""name: "{wf_title}"

on:
  schedule:
    - cron: "{cron_expr}"
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write
  issues: write

concurrency:
  group: factory-{item.factory_id}-{item.workflow_id}
  cancel-in-progress: false

jobs:
  run-factory-workflow:
    name: Execute {item.workflow_id}
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install HATH0R-CLI
        run: |
          python -m pip install --upgrade pip
          pip install -e .

      - name: Run Factory Workflow
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
          SLACK_WEBHOOK_URL: ${{{{ secrets.SLACK_WEBHOOK_URL }}}}
        run: |
          hath0r factory run {item.factory_id} --workflow {item.workflow_id} --repo {target_repo}
"""
    return content


def sync_factory_schedules_to_github(
    target_repo_dir: Path,
    group_root: Path | None = None,
    *,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Generate and write GitHub Actions schedule workflows in .github/workflows/."""
    scheduled = discover_scheduled_workflows(group_root=group_root)
    workflows_dir = target_repo_dir / ".github" / "workflows"

    if not dry_run:
        workflows_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    for item in scheduled:
        filename = f"factory-schedule-{item.factory_id}-{item.workflow_id}.yml"
        file_path = workflows_dir / filename
        content = generate_github_workflow_content(item)

        existed = file_path.is_file()
        action = "updated" if existed else "created"

        if not dry_run:
            file_path.write_text(content, encoding="utf-8")

        results.append({
            "factory_id": item.factory_id,
            "workflow_id": item.workflow_id,
            "schedule": item.schedule,
            "file": str(file_path),
            "filename": filename,
            "action": f"[DRY-RUN] would {action}" if dry_run else action,
            "dry_run": dry_run,
        })

    return results
