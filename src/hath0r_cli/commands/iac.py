"""Infrastructure as Code (IaC), Container Hardening, Salting & EKS Fargate commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.bots.iac_bot import IaCManagingBot
from hath0r_cli.common import _build_response, _emit_response, console


@click.group(name="iac", invoke_without_command=True)
@click.pass_context
def iac(ctx: click.Context) -> None:
    """Infrastructure as Code (IaC), Container Salting & AWS EKS Fargate control plane."""
    ctx.ensure_object(dict)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@iac.command(name="audit")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.option("--sweep", "-s", is_flag=True, default=False, help="Recursively sweep all repositories under PATH.")
@click.pass_context
def iac_audit(ctx: click.Context, path: Path, sweep: bool) -> None:
    """Audit workspace or repository tree for Container, Salting, and EKS Fargate compliance."""
    bot = IaCManagingBot(workspace=path)
    res = bot.audit_workspace(path=path, sweep=sweep)

    response = _build_response(
        ctx,
        command="iac audit",
        state="ok" if res.get("compliant", res.get("compliance_rate", 0) > 0.8) else "warning",
        data=res,
    )

    def _text() -> None:
        if sweep:
            console.print("\n[bold cyan]🏗️  HATH0R Infrastructure as Code (IaC) Multi-Repo Audit[/bold cyan]\n")
            table = Table(title=f"Repositories Under {path}", show_header=True, header_style="bold magenta")
            table.add_column("Repository", style="cyan")
            table.add_column("Dockerfile", justify="center")
            table.add_column("Salting", justify="center")
            table.add_column("EKS Fargate", justify="center")
            table.add_column("Score", justify="right")
            table.add_column("Status", justify="center")

            for repo in res.get("repositories", []):
                doc_str = "[green]✓ Multi-Stage[/green]" if repo["container"]["compliant"] else (
                    "[yellow]⚠ Root/Single[/yellow]" if repo["container"]["exists"] else "[red]✗ Missing[/red]"
                )
                salt_str = "[green]✓ Salted[/green]" if repo["salting"]["compliant"] else "[red]✗ Unsalted[/red]"
                fargate_str = "[green]✓ Ready[/green]" if repo["fargate"]["compliant"] else "[red]✗ Missing[/red]"
                status_str = "[bold green]COMPLIANT[/bold green]" if repo["compliant"] else "[bold yellow]ACTION NEEDED[/bold yellow]"
                score_str = f"{repo['compliance_score']:.2f}"

                table.add_row(repo["relative_path"], doc_str, salt_str, fargate_str, score_str, status_str)

            console.print(table)
            rate_pct = int(res.get("compliance_rate", 0) * 100)
            console.print(
                Panel(
                    f"Total Repositories Audited: [bold white]{res['total_repos']}[/bold white]\n"
                    f"Compliant: [bold green]{res['compliant_repos']}[/bold green] | "
                    f"Requiring Action: [bold yellow]{res['non_compliant_repos']}[/bold yellow]\n"
                    f"IaC Compliance Rate: [bold cyan]{rate_pct}%[/bold cyan]",
                    title="IaC Governance Summary",
                    border_style="bold cyan",
                )
            )
        else:
            console.print(f"\n[bold cyan]🏗️  IaC Compliance Audit: {res['repo_name']}[/bold cyan]\n")
            c = res["container"]
            s = res["salting"]
            f = res["fargate"]

            table = Table(title="3-Pillar IaC Verification", show_header=True, header_style="bold blue")
            table.add_column("IaC Pillar", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Details", style="white")

            table.add_row(
                "1. Container Security",
                "[green]PASS[/green]" if c["compliant"] else "[red]FAIL[/red]",
                f"Multi-stage: {c['multi_stage']} | Non-root: {c['non_root']} | Healthcheck: {c['has_healthcheck']}",
            )
            table.add_row(
                "2. Cryptographic Salting",
                "[green]PASS[/green]" if s["compliant"] else "[red]FAIL[/red]",
                f"Pinned Digest: {s['pinned_digest'] or 'None'} | Signature: {s['signature_verified']}",
            )
            table.add_row(
                "3. AWS EKS Fargate",
                "[green]PASS[/green]" if f["compliant"] else "[red]FAIL[/red]",
                f"Profile: {f['has_profile']} | K8s Manifests: {f['has_k8s']} | ALB Target IP: {f['target_type_ip']}",
            )
            console.print(table)

            status_banner = "[bold green]VALID & FARGATE READY[/bold green]" if res["compliant"] else "[bold yellow]REQUIRES REMEDIATION[/bold yellow]"
            console.print(f"\nOverall Status: {status_banner} (Score: [bold cyan]{res['compliance_score']:.2f}[/bold cyan])\n")

    _emit_response(ctx, response, text_renderer=_text)


@iac.command(name="init")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.option("--tech-stack", "-t", type=click.Choice(["python", "node", "go", "static"]), default=None, help="Target tech stack.")
@click.option("--app-name", "-n", type=str, default=None, help="Application / service name.")
@click.option("--force", "-f", is_flag=True, default=False, help="Overwrite existing IaC files.")
@click.pass_context
def iac_init(ctx: click.Context, path: Path, tech_stack: Optional[str], app_name: Optional[str], force: bool) -> None:
    """Initialize repository with hardened Dockerfile, container salting, and EKS Fargate manifests."""
    bot = IaCManagingBot(workspace=path)
    res = bot.init_iac(path=path, tech_stack=tech_stack, app_name=app_name, overwrite=force)

    response = _build_response(
        ctx,
        command="iac init",
        state="ok" if res["success"] else "error",
        data=res,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Infrastructure as Code Scaffolding Complete[/bold green]\n")
        console.print(f"Target Directory: [bold white]{res['workspace']}[/bold white]")
        console.print(f"Detected Stack:    [bold cyan]{res['tech_stack']}[/bold cyan]")
        console.print(f"Service Name:      [bold magenta]{res['app_name']}[/bold magenta]")
        console.print(f"Salted Image Ref:  [bold yellow]{res['pinned_ref']}[/bold yellow]\n")

        table = Table(title="Generated IaC Artifacts", show_header=True, header_style="bold green")
        table.add_column("Artifact", style="cyan")
        table.add_column("Description", style="white")

        descriptions = {
            "Dockerfile": "Hardened multi-stage build, non-root user (UID 10001), HEALTHCHECK",
            ".dockerignore": "Excludes git, virtual environments, node_modules, and secret credentials",
            "fargate-profile.yaml": "AWS EKS Fargate profile spec matching namespace/labels",
            "k8s/deployment.yaml": "Kubernetes Deployment with Fargate resource brackets and salted image",
            "k8s/service.yaml": "ClusterIP Service definition",
            "k8s/ingress.yaml": "AWS ALB Ingress with target-type: ip annotation",
            "k8s/serviceaccount.yaml": "IAM Roles for Service Accounts (IRSA) role binding",
            ".hath0r/iac/spec.yaml": "Declarative Hath0r IaC specification contract",
            ".hath0r/iac/salting-receipt.json": "Cryptographic SHA-256 digest and SLSA provenance receipt",
        }

        for f in res["files_scaffolded"]:
            table.add_row(f, descriptions.get(f, "IaC Configuration"))
        console.print(table)
        console.print("\n[dim]Run 'hath0r iac validate' to verify all constraints.[/dim]\n")

    _emit_response(ctx, response, text_renderer=_text)


@iac.command(name="validate")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.pass_context
def iac_validate(ctx: click.Context, path: Path) -> None:
    """Validate repository against CR-IAC-001 (Container Security, Salting, and EKS Fargate)."""
    bot = IaCManagingBot(workspace=path)
    res = bot.validate_iac(path=path)

    response = _build_response(
        ctx,
        command="iac validate",
        state="ok" if res["valid"] else "warning",
        data=res,
    )

    def _text() -> None:
        console.print(f"\n[bold cyan]🔍 Validating IaC Compliance: {res['repo_name']}[/bold cyan]\n")
        status_str = "[bold green]PASSED (COMPLIANT)[/bold green]" if res["valid"] else "[bold yellow]FAILED (REMEDIATION REQUIRED)[/bold yellow]"
        console.print(f"Overall Status: {status_str} | Score: [bold cyan]{res['score']:.2f}[/bold cyan]\n")

        p = res["pillars"]
        c = p["container_security"]
        s = p["cryptographic_salting"]
        f = p["eks_fargate_readiness"]

        console.print("[bold green]1. Container Security:[/bold green]")
        console.print(f"  • Multi-stage build:    {'[green]✓[/green]' if c['multi_stage'] else '[red]✗[/red]'}")
        console.print(f"  • Non-root user:        {'[green]✓[/green]' if c['non_root'] else '[red]✗[/red]'}")
        console.print(f"  • HEALTHCHECK probe:    {'[green]✓[/green]' if c['has_healthcheck'] else '[red]✗[/red]'}")

        console.print("\n[bold yellow]2. Cryptographic Salting:[/bold yellow]")
        console.print(f"  • Digest pinned:        {'[green]✓[/green]' if s['compliant'] else '[red]✗[/red]'}")
        console.print(f"  • Digest value:         [cyan]{s['pinned_digest'] or 'Not salted'}[/cyan]")
        console.print(f"  • Signature verified:   {'[green]✓[/green]' if s['signature_verified'] else '[yellow]Pending[/yellow]'}")

        console.print("\n[bold magenta]3. AWS EKS Fargate Readiness:[/bold magenta]")
        console.print(f"  • Fargate profile:      {'[green]✓[/green]' if f['has_profile'] else '[red]✗[/red]'}")
        console.print(f"  • Kubernetes manifests: {'[green]✓[/green]' if f['has_k8s'] else '[red]✗[/red]'}")
        console.print(f"  • ALB Target Type IP:   {'[green]✓[/green]' if f['target_type_ip'] else '[red]✗[/red]'}")
        console.print(f"  • Privileged disabled:  {'[green]✓[/green]' if not f['privileged_detected'] else '[red]✗ Detected[/red]'}\n")

        if res["diagnostics"]:
            console.print("[bold red]Action Items:[/bold red]")
            for diag in res["diagnostics"]:
                console.print(f"  • [{diag['pillar']}] {diag['message']}")
            console.print()

    _emit_response(ctx, response, text_renderer=_text)


@iac.command(name="salt")
@click.argument("image", type=str)
@click.option("--workspace", "-w", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.pass_context
def iac_salt(ctx: click.Context, image: str, workspace: Path) -> None:
    """Cryptographically salt container image, generate SHA-256 digest pin, and emit SLSA provenance receipt."""
    bot = IaCManagingBot(workspace=workspace)
    receipt = bot.salt_container(image=image, workspace=workspace)

    response = _build_response(
        ctx,
        command="iac salt",
        state="ok",
        data=receipt,
    )

    def _text() -> None:
        console.print("\n[bold green]✓ Container Image Cryptographically Salted[/bold green]\n")
        table = Table(title="Salting & Provenance Receipt", show_header=True, header_style="bold green")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="bold white")

        table.add_row("Mutable Tag", receipt["mutable_tag"])
        table.add_row("Pinned Digest", receipt["pinned_digest"])
        table.add_row("Immutable Ref", receipt["pinned_ref"])
        table.add_row("Signature Provider", receipt["attestation"]["signature_provider"])
        table.add_row("Attestation Format", receipt["attestation"]["predicate_type"])
        table.add_row("Secret Provider", receipt["secret_salting"]["provider"])
        console.print(table)
        console.print("\n[dim]Receipt saved to .hath0r/iac/salting-receipt.json[/dim]\n")

    _emit_response(ctx, response, text_renderer=_text)


@iac.command(name="render")
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path), default=".")
@click.option("--env", "-e", "environment", type=click.Choice(["development", "testing", "staging", "master"]), default="development", help="Target promotion environment.")
@click.pass_context
def iac_render(ctx: click.Context, path: Path, environment: str) -> None:
    """Render parameterized Kubernetes manifests targeting canonical environment."""
    bot = IaCManagingBot(workspace=path)
    res = bot.render_manifests(path=path, environment=environment)

    response = _build_response(
        ctx,
        command="iac render",
        state="ok",
        data=res,
    )

    def _text() -> None:
        console.print(f"\n[bold green]✓ Rendered {res['count']} Manifests for Environment: [bold yellow]{environment}[/bold yellow][/bold green]\n")
        console.print(f"Output Directory: [bold cyan]{res['output_directory']}[/bold cyan]\n")
        for f in res["rendered_files"]:
            console.print(f"  • {Path(f).name}")
        console.print()

    _emit_response(ctx, response, text_renderer=_text)
