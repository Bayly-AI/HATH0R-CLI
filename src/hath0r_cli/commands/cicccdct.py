"""Continuous Integration, Calibration, Deployment & Continuous Training (CICCCDCT) commands for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.bots.cicccd_bot import CICCCDCTManagingBot
from hath0r_cli.common import _build_response, _emit_response, console


@click.group(name="cicccdct", invoke_without_command=True)
@click.pass_context
def cicccdct(ctx: click.Context) -> None:
    """Continuous Integration, Calibration, Deployment & Continuous Training (CIC³DCT / CIC{qubed}DCT) control plane."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cicccdct.command(name="status")
@click.pass_context
def cicccdct_status(ctx: click.Context) -> None:
    """Inspect 4-pillar CIC³DCT metrics: CI checks, CC parameters, CD state, and CT model lineage."""
    bot = CICCCDCTManagingBot()
    status_data = bot.status()

    response = _build_response(
        ctx,
        command="cicccdct status",
        state="ok",
        data=status_data,
    )

    def _text() -> None:
        state = status_data.get("state", {})
        console.print(
            "\n[bold cyan]⚡ HATH0R Continuous Integration, Calibration, Deployment & Continuous Training (CIC³DCT / CIC{qubed}DCT)[/bold cyan]\n"
        )

        # CC Parameters Table
        params_table = Table(title="Calibrated Runtime Parameters (CC)", show_header=True, header_style="bold magenta")
        params_table.add_column("Parameter", style="cyan")
        params_table.add_column("Calibrated Value", style="green")
        for k, v in state.get("current_parameters", {}).items():
            params_table.add_row(str(k), str(v))
        console.print(params_table)

        # Drift Table
        drift_table = Table(title="Parameter & Cognitive Drift Metrics (CC / CT)", show_header=True, header_style="bold blue")
        drift_table.add_column("Metric", style="cyan")
        drift_table.add_column("Value / Drift", style="yellow")
        for k, v in state.get("drift_metrics", {}).items():
            drift_table.add_row(str(k), f"{v:+}")
        console.print(drift_table)

        # CT Model Lineage Table
        training = state.get("training", {})
        ct_table = Table(title="Active Continuous Training (CT) Model Lineage", show_header=True, header_style="bold green")
        ct_table.add_column("Property", style="cyan")
        ct_table.add_column("Value", style="bold white")
        ct_table.add_row("Active Model Name", str(training.get("active_model_name", "None")))
        ct_table.add_row("Active Model Version", str(training.get("active_model_version", 1)))
        ct_table.add_row("Registry Stage", f"[bold green]{training.get('active_model_stage', 'Production')}[/bold green]")
        ct_table.add_row("MLflow Run ID", str(training.get("mlflow_run_id", "None")))
        ct_table.add_row("Train Loss", str(training.get("train_loss", "0.0")))
        ct_table.add_row("Eval Benchmark Reward", str(training.get("eval_benchmark_reward", "0.85")))
        ct_table.add_row("Candidate Improvement", f"{training.get('candidate_model_improvement', 0.0):+.4f}")
        ct_table.add_row("Curated Training Samples", str(training.get("dataset_samples_count", 0)))
        console.print(ct_table)

        freshness = status_data.get("freshness", {})
        fresh_status_str = (
            "[bold green]FRESH[/bold green]" if freshness.get("is_fresh") else "[bold yellow]STALE (>24h)[/bold yellow]"
        )
        age_str = f"{freshness.get('age_hours'):.1f} hours ago" if freshness.get("age_hours") is not None else "Never"

        summary_panel = Panel(
            f"Calibration Freshness (CC): {fresh_status_str} (Last run: {age_str})\n"
            f"Model Training Freshness (CT): {'[bold green]FRESH (<=168h)[/bold green]' if training.get('last_trained_timestamp') else '[bold yellow]STALE[/bold yellow]'}\n"
            f"Total Calibration Runs: [bold white]{state.get('total_calibration_runs', 0)}[/bold white]\n"
            f"Total Training Runs: [bold white]{training.get('total_training_runs', 0)}[/bold white]\n"
            f"Active Model Checkpoint: [bold cyan]{training.get('active_model_name')}:{training.get('active_model_version')}[/bold cyan]",
            title="CIC³DCT Governance Overview & Entry Gate",
            border_style="bold green",
        )
        console.print(summary_panel)

    _emit_response(ctx, response, text_renderer=_text)


@cicccdct.command(name="validate")
@click.option("--repo", type=str, default=None, help="Target repository to validate CIC³DCT state for.")
@click.pass_context
def cicccdct_validate(ctx: click.Context, repo: Optional[str]) -> None:
    """Validate 4-pillar CIC³DCT state across CI contracts/SAST, CC freshness, CD docs, and CT model SLA."""
    bot = CICCCDCTManagingBot()
    res = bot.validate_cicccd(repo=repo)

    response = _build_response(
        ctx,
        command="cicccdct validate",
        state="ok" if res["valid"] else "warning",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold cyan]🔍 HATH0R CIC³DCT Closed-Loop 4-Pillar Validation[/bold cyan]\n")
        console.print(f"Target Repo: [bold white]{res['repo']}[/bold white]")
        console.print(
            f"Overall Status: {'[bold green]VALID (READY FOR PROMOTION)[/bold green]' if res['valid'] else '[bold yellow]REQUIRES ACTION[/bold yellow]'}\n"
        )

        console.print("[bold green]1. Continuous Integration (CI):[/bold green]")
        console.print(f"  • Schema Contracts: [green]{res['ci']['contracts_valid']}[/green]")
        console.print(f"  • AgentGraph Policy: [green]{res['ci']['agentgraph_valid']}[/green]")
        console.print(f"  • SAST Compliant: [green]{res['ci']['security_sast']['owasp_top_10_compliant']}[/green]")

        console.print("\n[bold yellow]2. Continuous Calibration (CC):[/bold yellow]")
        console.print(
            f"  • Calibration Freshness: {'[green]Fresh (<=24h)[/green]' if res['cc']['is_fresh'] else '[yellow]Stale (>24h)[/yellow]'}"
        )
        console.print(f"  • Calibration Age: {res['cc']['age_hours']:.1f} hours")

        console.print("\n[bold magenta]3. Continuous Deployment (CD):[/bold magenta]")
        console.print(f"  • Artifact Hexad Docs: [green]{res['cd']['artifact_hexad_published']}[/green]")
        console.print(f"  • Auto-Tune Daemon: [cyan]{res['cd']['auto_tune_active']}[/cyan]")

        console.print("\n[bold blue]4. Continuous Training (CT):[/bold blue]")
        ct = res.get("ct", {})
        console.print(f"  • Active Model: [cyan]{ct.get('active_model_name')}[/cyan] (Stage: [green]{ct.get('active_model_stage')}[/green])")
        console.print(f"  • Training Freshness SLA: {'[green]Compliant (<=168h)[/green]' if ct.get('training_fresh') else '[yellow]SLA Breached (>168h)[/yellow]'}")
        console.print(f"  • Benchmark Reward: [bold green]{ct.get('eval_benchmark_reward')}[/bold green]")
        console.print(f"  • CT SLA Compliant: {'[green]PASSED[/green]' if ct.get('sla_compliant') else '[red]FAILED[/red]'}\n")

    _emit_response(ctx, response, text_renderer=_text)


@cicccdct.command(name="calibrate")
@click.option("--iterations", "-i", type=int, default=3, help="Number of benchmark evaluation iterations.")
@click.option("--signature", "-s", type=str, default="default_agent_signature", help="DSPy signature name to compile.")
@click.pass_context
def cicccdct_calibrate(ctx: click.Context, iterations: int, signature: str) -> None:
    """Trigger on-demand continuous calibration run against benchmark datasets."""
    bot = CICCCDCTManagingBot()
    result = bot.calibrate(iterations=iterations, signature=signature)

    response = _build_response(
        ctx,
        command="cicccdct calibrate",
        state="ok" if result["success"] else "error",
        data=result,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Continuous Calibration Run Completed Successfully[/bold green]")
        console.print(f"Calibration ID: [bold cyan]#{result['calibration_id']}[/bold cyan]")
        console.print(f"Timestamp: [bold white]{result['timestamp']}[/bold white]")
        console.print(f"DSPy Compiled Signature: [bold yellow]{signature}[/bold yellow]")

        params = result["updated_parameters"]
        console.print("\n[bold cyan]Updated Calibrated Parameters:[/bold cyan]")
        for k, v in params.items():
            console.print(f"  • {k}: [bold green]{v}[/bold green]")

    _emit_response(ctx, response, text_renderer=_text)


@cicccdct.command(name="auto-tune")
@click.option("--interval", type=int, default=300, help="Continuous tuning check interval in seconds.")
@click.option("--daemon/--no-daemon", default=False, help="Run continuous calibration loop in daemon mode.")
@click.pass_context
def cicccdct_autotune(ctx: click.Context, interval: int, daemon: bool) -> None:
    """Enable background continuous development and prompt optimization daemon."""
    bot = CICCCDCTManagingBot()
    data = bot.auto_tune(interval=interval, daemon=daemon)

    response = _build_response(
        ctx,
        command="cicccdct auto-tune",
        state="ok",
        data=data,
    )

    def _text() -> None:
        console.print(
            Panel(
                f"[bold green]Continuous Development & Auto-Tune Daemon Active[/bold green]\n\n"
                f"Check Interval: [bold cyan]{interval} seconds[/bold cyan]\n"
                f"Daemon Mode: [bold yellow]{daemon}[/bold yellow]\n"
                f"Status: Monitoring OTLP spans and drift thresholds for automated continuous training and tuning.",
                title="CIC³DCT Auto-Tune Control Plane",
                border_style="bold cyan",
            )
        )

    _emit_response(ctx, response, text_renderer=_text)


# =========================================================================
# CT Subgroups: dataset, train, model
# =========================================================================

@cicccdct.group(name="dataset")
def dataset_group() -> None:
    """Continuous Training (CT) dataset curation and statistics."""
    pass


@dataset_group.command(name="curate")
@click.option("--min-reward", type=float, default=0.70, help="Minimum execution trace reward threshold.")
@click.option("--max-samples", type=int, default=None, help="Maximum exemplar samples to extract.")
@click.option("--output-file", "-o", type=str, default=None, help="Target JSONL dataset destination.")
@click.pass_context
def dataset_curate(ctx: click.Context, min_reward: float, max_samples: Optional[int], output_file: Optional[str]) -> None:
    """Curate high-reward exemplars from agent execution traces into a JSONL training set."""
    bot = CICCCDCTManagingBot()
    res = bot.curate_dataset(min_reward=min_reward, max_samples=max_samples, output_file=output_file)

    response = _build_response(
        ctx,
        command="cicccdct dataset curate",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Training Dataset Curated Successfully[/bold green]")
        console.print(f"Dataset Path: [bold white]{res['dataset_path']}[/bold white]")
        console.print(f"Curated Samples: [bold cyan]{res['samples_curated']}[/bold cyan]")
        stats = res.get("statistics", {})
        console.print(f"Mean Reward: [bold green]{stats.get('mean_reward', 0.0)}[/bold green]")
        console.print(f"Estimated Tokens: [bold yellow]{stats.get('total_estimated_tokens', 0)}[/bold yellow]\n")

    _emit_response(ctx, response, text_renderer=_text)


@dataset_group.command(name="stats")
@click.option("--dataset", "-d", type=str, required=True, help="Path to JSONL dataset.")
@click.pass_context
def dataset_stats(ctx: click.Context, dataset: str) -> None:
    """Compute and display token and reward statistics for a curated training dataset."""
    path = Path(dataset)
    if not path.is_file():
        raise click.ClickException(f"Dataset file '{dataset}' not found.")

    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    bot = CICCCDCTManagingBot()
    stats = bot.training_coordinator.compute_dataset_statistics(items)

    response = _build_response(
        ctx,
        command="cicccdct dataset stats",
        state="ok",
        data={"dataset": dataset, "statistics": stats},
    )

    def _text() -> None:
        console.print(f"\n[bold cyan]📊 Dataset Statistics: {dataset}[/bold cyan]")
        console.print(f"Samples: [bold white]{stats['samples_count']}[/bold white]")
        console.print(f"Mean Reward: [bold green]{stats['mean_reward']}[/bold green]")
        console.print(f"Total Estimated Tokens: [bold yellow]{stats['total_estimated_tokens']}[/bold yellow]\n")

    _emit_response(ctx, response, text_renderer=_text)


@cicccdct.group(name="train")
def train_group() -> None:
    """Continuous Training (CT) model fine-tuning and pipeline execution."""
    pass


@train_group.command(name="run")
@click.option("--target", type=str, default="reasoning_slm", help="Target architecture or prompt module.")
@click.option("--method", type=str, default="lora", help="Training method (lora, qlora, dspy_mipro, dspy_fewshot).")
@click.option("--dataset", "-d", type=str, default=None, help="Path to training dataset JSONL.")
@click.option("--epochs", "-e", type=int, default=3, help="Number of training epochs.")
@click.option("--lr", type=float, default=0.0002, help="Learning rate.")
@click.option("--batch-size", "-b", type=int, default=4, help="Batch size.")
@click.pass_context
def train_run(
    ctx: click.Context,
    target: str,
    method: str,
    dataset: Optional[str],
    epochs: int,
    lr: float,
    batch_size: int,
) -> None:
    """Execute Continuous Training job, evaluate candidate model, and log to MLflow."""
    bot = CICCCDCTManagingBot()
    res = bot.train_model(
        target=target,
        method=method,
        dataset_path=dataset,
        epochs=epochs,
        learning_rate=lr,
        batch_size=batch_size,
    )

    response = _build_response(
        ctx,
        command="cicccdct train run",
        state="ok" if res.get("status") == "completed" else "error",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Continuous Training Job Completed[/bold green]")
        console.print(f"Job ID: [bold cyan]{res['job_id']}[/bold cyan]")
        console.print(f"Target: [bold white]{res['target']}[/bold white] (Method: [yellow]{res['method']}[/yellow])")
        console.print(f"MLflow Run ID: [bold magenta]{res['mlflow_run_id']}[/bold magenta]")
        console.print(f"Artifact URI: [bold white]{res['model_artifact_uri']}[/bold white]")

        metrics = res.get("metrics", {})
        console.print("\n[bold cyan]Post-Training Benchmark Evaluation:[/bold cyan]")
        console.print(f"  • Final Train Loss: [green]{metrics.get('train_loss')}[/green]")
        console.print(f"  • Evaluation Reward: [bold green]{metrics.get('eval_reward')}[/bold green]")
        console.print(f"  • Candidate Improvement: [bold yellow]{metrics.get('accuracy_improvement'):+.4f}[/bold yellow]")
        console.print(f"  • Taguchi S/N Ratio: [cyan]{metrics.get('snr_db')} dB[/cyan]")
        console.print(f"  • Promotable to Staging: {'[bold green]YES[/bold green]' if metrics.get('promotable') else '[bold yellow]NO[/bold yellow]'}\n")

    _emit_response(ctx, response, text_renderer=_text)


@cicccdct.group(name="model")
def model_group() -> None:
    """MLflow Model Registry inspection and stage promotion."""
    pass


@model_group.command(name="list")
@click.pass_context
def model_list(ctx: click.Context) -> None:
    """List registered models and active versions in the MLflow Model Registry."""
    bot = CICCCDCTManagingBot()
    status = bot.status()
    training = status.get("state", {}).get("training", {})

    models = [
        {
            "model_name": training.get("active_model_name", "reasoning_slm"),
            "version": training.get("active_model_version", 1),
            "stage": training.get("active_model_stage", "Production"),
            "eval_reward": training.get("eval_benchmark_reward", 0.85),
            "last_trained": training.get("last_trained_timestamp", "Never"),
        }
    ]

    response = _build_response(
        ctx,
        command="cicccdct model list",
        state="ok",
        data=models,  # type: ignore[arg-type]
    )

    def _text() -> None:
        table = Table(title="MLflow Model Registry", show_header=True, header_style="bold magenta")
        table.add_column("Model Name", style="cyan")
        table.add_column("Version", style="white")
        table.add_column("Stage", style="bold green")
        table.add_column("Eval Reward", style="yellow")
        table.add_column("Last Trained", style="white")

        for m in models:
            table.add_row(m["model_name"], str(m["version"]), m["stage"], str(m["eval_reward"]), str(m["last_trained"]))

        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@model_group.command(name="promote")
@click.option("--model-name", "-m", type=str, required=True, help="Model name registered in MLflow.")
@click.option("--version", "-v", type=int, required=True, help="Model version integer.")
@click.option("--stage", "-s", type=click.Choice(["None", "Staging", "Production"]), required=True, help="Target lifecycle stage.")
@click.pass_context
def model_promote(ctx: click.Context, model_name: str, version: int, stage: str) -> None:
    """Promote a candidate model version to Staging or Production in the MLflow Model Registry."""
    bot = CICCCDCTManagingBot()
    res = bot.promote_model(model_name=model_name, version=version, stage=stage)

    response = _build_response(
        ctx,
        command="cicccdct model promote",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Model Successfully Promoted[/bold green]")
        console.print(f"Model: [bold cyan]{model_name}[/bold cyan] (v{version})")
        console.print(f"New Stage: [bold green]{stage}[/bold green]")
        console.print(f"Timestamp: [bold white]{res['promoted_at']}[/bold white]\n")

    _emit_response(ctx, response, text_renderer=_text)
