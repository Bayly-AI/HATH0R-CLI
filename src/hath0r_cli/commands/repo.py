"""Repo command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
    _group_root,
    console,
)


@click.group()
def repo() -> None:
    """Repository Hygiene & Organization: audit and clean root files and configs."""


def _resolve_target_repos(target_repo: str | None, all_repos: bool) -> list[Path]:
    """Resolve list of target repositories for repo hygiene commands."""
    if target_repo:
        p = Path(target_repo).expanduser().resolve()
        if not p.is_dir():
            raise click.ClickException(f"Specified repository directory does not exist: {target_repo}")
        return [p]
    if all_repos:
        root = _group_root()
        repos = []
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / ".git").is_dir():
                repos.append(d.resolve())
        # Deduplicate symlinks
        seen = set()
        deduped = []
        for r in repos:
            real = str(r.resolve())
            if real not in seen:
                seen.add(real)
                deduped.append(r)
        return deduped
    return [Path.cwd()]


@repo.command("audit")
@click.option("--repo", "target_repo", default=None, help="Target specific repository directory.")
@click.option("--all-repos", is_flag=True, default=False, help="Audit all sibling repositories in OpenSource group.")
@click.pass_context
def repo_audit(ctx: click.Context, target_repo: str | None, all_repos: bool) -> None:
    """Audit project root, configuration placement, and knowledge modularity."""
    from hath0r_cli.bots.repo_clean import ConfigOrganizerBot, KnowledgeOrganizerBot, RepoHygieneBot

    repos = _resolve_target_repos(target_repo, all_repos)
    all_clean = True
    results_by_repo = []

    for r in repos:
        hygiene = RepoHygieneBot(cwd=r).scan_root()
        configs = ConfigOrganizerBot(cwd=r).scan_misplaced_configs()
        knowledge = KnowledgeOrganizerBot(cwd=r).audit_knowledge_structure()
        is_clean = bool(hygiene.get("clean")) and bool(configs.get("clean")) and bool(knowledge.get("organized"))
        if not is_clean:
            all_clean = False
        results_by_repo.append(
            {
                "repo": r.name,
                "path": str(r),
                "clean": is_clean,
                "hygiene": hygiene,
                "configs": configs,
                "knowledge": knowledge,
            }
        )

    status_state = "ok" if all_clean else "degraded"
    data = {
        "all_clean": all_clean,
        "repo_count": len(repos),
        "repos": results_by_repo,
    }
    response = _build_response(ctx, command="repo.audit", state=status_state, data=data)

    def _text() -> None:
        console.print(f"[bold cyan]Repository Cleanliness & Structure Audit[/bold cyan] ({len(repos)} repo(s))")
        console.print("=" * 65)

        for rep in results_by_repo:
            r_name = str(rep["repo"])
            console.print(f"\n[bold]{r_name}[/bold] ({rep['path']})")
            console.print("-" * 40)
            hyg: dict[str, Any] = rep["hygiene"] if isinstance(rep["hygiene"], dict) else {}
            cfg: dict[str, Any] = rep["configs"] if isinstance(rep["configs"], dict) else {}
            kno: dict[str, Any] = rep["knowledge"] if isinstance(rep["knowledge"], dict) else {}

            # Root files
            if hyg.get("clean"):
                console.print("  [green]✓ Project Root:[/green] Clean (no errant or unwhitelisted files)")
            else:
                console.print(f"  [red]✗ Project Root:[/red] Found {hyg.get('errant_count')} errant file(s):")
                for ef in hyg.get("errant_files", []):
                    console.print(f"    - {ef.get('name')} ({ef.get('size_bytes')} bytes)")

            # Configs
            if cfg.get("clean"):
                console.print("  [green]✓ Configuration Placement:[/green] Clean (all configs properly stored)")
            else:
                misplaced_cnt = cfg.get("misplaced_count")
                console.print(
                    f"  [yellow]! Configuration Placement:[/yellow] {misplaced_cnt} misplaced root config(s):"
                )
                for mc in cfg.get("misplaced_configs", []):
                    console.print(f"    - {mc.get('name')} -> recommended: {mc.get('recommended_dest')}")

            # Knowledge
            if kno.get("organized"):
                console.print("  [green]✓ Knowledge & Rules Modularity:[/green] Organized across topic folders")
            else:
                findings_cnt = kno.get("findings_count")
                console.print(f"  [yellow]! Knowledge & Rules Modularity:[/yellow] {findings_cnt} issue(s):")
                for f in kno.get("findings", []):
                    console.print(f"    - {f.get('file')} ({f.get('lines')} lines): {f.get('recommendation')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not all_clean:
        ctx.exit(1)


@repo.command("clean")
@click.option("--repo", "target_repo", default=None, help="Target specific repository directory.")
@click.option("--all-repos", is_flag=True, default=False, help="Clean all sibling repositories in OpenSource group.")
@click.option("--target-folder", default=".cfg", show_default=True, help="Target folder for relocated configs.")
@click.option(
    "--archive-dir",
    default=".hath0r/spool/archive",
    show_default=True,
    help="Directory to archive errant root files.",
)
@click.option("--dry-run", is_flag=True, default=False, help="Simulate actions without moving files.")
@click.pass_context
def repo_clean(
    ctx: click.Context,
    target_repo: str | None,
    all_repos: bool,
    target_folder: str,
    archive_dir: str,
    dry_run: bool,
) -> None:
    """Relocate misplaced configs to .cfg/ and clean errant root files."""
    from hath0r_cli.bots.repo_clean import ConfigOrganizerBot, RepoHygieneBot

    repos = _resolve_target_repos(target_repo, all_repos)
    results_by_repo = []

    for r in repos:
        config_res = ConfigOrganizerBot(cwd=r).organize_configs(target_folder=target_folder, dry_run=dry_run)
        hygiene_res = RepoHygieneBot(cwd=r).clean_root(dry_run=dry_run, archive_dir=archive_dir)
        results_by_repo.append(
            {
                "repo": r.name,
                "path": str(r),
                "config_relocations": config_res,
                "root_cleanup": hygiene_res,
            }
        )

    data = {
        "dry_run": dry_run,
        "repo_count": len(repos),
        "repos": results_by_repo,
    }
    response = _build_response(ctx, command="repo.clean", state="ok", dry_run=dry_run, data=data)

    def _text() -> None:
        prefix = "[DRY-RUN] " if dry_run else ""
        console.print(f"[bold cyan]{prefix}Repository Cleanup & Organization[/bold cyan] ({len(repos)} repo(s))")
        console.print("=" * 65)

        for rep in results_by_repo:
            console.print(f"\n[bold]{rep['repo']}[/bold] ({rep['path']})")
            console.print("-" * 40)
            cfg_dict: dict[str, Any] = rep["config_relocations"] if isinstance(rep["config_relocations"], dict) else {}
            hyg_dict: dict[str, Any] = rep["root_cleanup"] if isinstance(rep["root_cleanup"], dict) else {}
            cfg_rel = cfg_dict.get("relocations", [])
            hyg_act = hyg_dict.get("actions", [])

            for rel in cfg_rel:
                console.print(f"  [green]✓ Config:[/green] {rel.get('action')}")

            for cln in hyg_act:
                console.print(f"  [green]✓ Root File:[/green] {cln.get('action')}")

            if not cfg_rel and not hyg_act:
                console.print("  [green]✓ Nothing to clean. Repository root is spotless.[/green]")

    _emit_response(ctx, response, text_renderer=_text)


@repo.command("workflow")
@click.option("--repo", "target_repo", default=None, help="Target specific repository directory.")
@click.option("--all-repos", is_flag=True, default=False, help="Run clean workflow across all sibling repositories.")
@click.option("--no-commit", is_flag=True, default=False, help="Disable auto-committing uncommitted changes.")
@click.pass_context
def repo_workflow(ctx: click.Context, target_repo: str | None, all_repos: bool, no_commit: bool) -> None:
    """Execute the full 13-step Clean Repos Standard Operating Procedure."""
    from hath0r_cli.bots.repo_clean import CleanReposWorkflowBot

    repos = _resolve_target_repos(target_repo, all_repos)
    bot = CleanReposWorkflowBot()
    results = bot.run_clean_repo_workflow(target_repos=repos, auto_commit=not no_commit)

    response = _build_response(
        ctx, command="repo.workflow", state="ok" if results.get("success") else "degraded", data=results
    )

    def _text() -> None:
        console.print(f"[bold cyan]13-Step Clean Repos Standard Operating Procedure[/bold cyan] ({len(repos)} repo(s))")
        console.print("=" * 70)
        for rep in results.get("repos", []):
            console.print(f"\n[bold]{rep['repo']}[/bold] ({rep['path']})")
            console.print("-" * 45)
            steps = rep.get("steps", {})
            for step_key, step_data in sorted(steps.items()):
                console.print(f"  [green]✓[/green] [bold]{step_key}:[/bold] {step_data}")
            if rep.get("clean"):
                console.print("  [bold green]✓ Repository Clean & Fully In Sync[/bold green]")
            else:
                console.print(f"  [bold red]✗ Issues encountered:[/bold red] {rep.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)


@click.command("clean-repos")
@click.option("--repo", "target_repo", default=None, help="Target specific repository directory.")
@click.option("--all-repos", is_flag=True, default=True, help="Run clean workflow across all sibling repositories.")
@click.option("--no-commit", is_flag=True, default=False, help="Disable auto-committing uncommitted changes.")
@click.pass_context
def clean_repos_cmd(ctx: click.Context, target_repo: str | None, all_repos: bool, no_commit: bool) -> None:
    """Top-level command to execute the 13-step Clean Repos SOP."""
    ctx.invoke(repo_workflow, target_repo=target_repo, all_repos=all_repos, no_commit=no_commit)


@click.command("clean-repo")
@click.option("--repo", "target_repo", default=None, help="Target specific repository directory.")
@click.option("--all-repos", is_flag=True, default=False, help="Run clean workflow across all sibling repositories.")
@click.option("--no-commit", is_flag=True, default=False, help="Disable auto-committing uncommitted changes.")
@click.pass_context
def clean_repo_cmd(ctx: click.Context, target_repo: str | None, all_repos: bool, no_commit: bool) -> None:
    """Top-level command to execute the 13-step Clean Repo SOP on current repo."""
    ctx.invoke(repo_workflow, target_repo=target_repo, all_repos=all_repos, no_commit=no_commit)


@repo.command("siblings")
@click.option("--check-remote", is_flag=True, default=False, help="Query GitHub for latest remote tags.")
@click.pass_context
def repo_siblings(ctx: click.Context, check_remote: bool) -> None:
    """Inspect suite sibling repositories, installation locations, and versions."""
    from rich.table import Table

    from hath0r_cli.bots.sibling_bot import SiblingManagerBot

    bot = SiblingManagerBot()
    report = bot.scan_siblings(check_remote=check_remote)
    state = "ok" if report.get("all_canonical_present") else "degraded"

    response = _build_response(ctx, command="repo.siblings", state=state, data=report)

    def _text() -> None:
        table = Table(title="HATH0R Suite Siblings")
        table.add_column("Product", style="bold cyan")
        table.add_column("Status")
        table.add_column("Local Version")
        if check_remote:
            table.add_column("Remote Latest")
        table.add_column("Path")

        for pid, p in report.get("products", {}).items():
            status = (
                "[green]Installed[/green]"
                if p.get("present")
                else (
                    "[red]Missing (Canonical)[/red]"
                    if p.get("canonical")
                    else "[dim]Optional (Missing)[/dim]"
                )
            )
            row = [
                p.get("name", pid),
                status,
                p.get("local_version") or "-",
            ]
            if check_remote:
                row.append(p.get("remote_version") or "-")
            row.append(p.get("path") or "-")
            table.add_row(*row)

        console.print(table)
        if not report.get("all_canonical_present"):
            console.print("\n[bold yellow]Some canonical siblings are missing.[/bold yellow]")
            console.print(
                "Run [bold green]hath0r repo ensure[/bold green] to download and install missing siblings."
            )

    _emit_response(ctx, response, text_renderer=_text)


@repo.command("install")
@click.argument("product", required=True)
@click.option("--version", "tag_or_version", default=None, help="Specific tag or version to download.")
@click.pass_context
def repo_install(ctx: click.Context, product: str, tag_or_version: str | None) -> None:
    """Download and install a suite sibling repository (e.g. hath0r-atc, hath0r-mcp)."""
    from hath0r_cli.bots.sibling_bot import SiblingManagerBot
    from hath0r_cli.envelope import Diagnostic

    bot = SiblingManagerBot()
    res = bot.download_and_install(product, version=tag_or_version)

    state = "ok" if res.get("success") else "error"
    diagnostics = []
    if not res.get("success"):
        diagnostics.append(
            Diagnostic(
                code="REPO_INSTALL_FAILED",
                message=str(res.get("error", f"Failed to install {product}")),
                severity="error",
                remediation="Verify repository name, network connectivity, or GitHub credentials.",
                provenance={"component": "hath0r-cli", "operation": "repo.install"},
            )
        )

    response = _build_response(ctx, command="repo.install", state=state, data=res, diagnostics=diagnostics)

    def _text() -> None:
        if res.get("success"):
            action = "Already installed" if res.get("already_installed") else "Successfully installed"
            console.print(f"[bold green]✓ {action}:[/bold green] {res.get('name')} at {res.get('path')}")
            if res.get("version"):
                console.print(f"  Version: [bold cyan]{res.get('version')}[/bold cyan]")
            if res.get("installed_deps"):
                console.print("  [bold green]✓ Project dependencies installed.[/bold green]")
        else:
            console.print(f"[bold red]✗ Installation failed:[/bold red] {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@repo.command("ensure")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate checking without downloading.")
@click.pass_context
def repo_ensure(ctx: click.Context, dry_run: bool) -> None:
    """Ensure all canonical suite sibling repositories (ATC, MCP) are present and installed."""
    from hath0r_cli.bots.sibling_bot import SiblingManagerBot

    bot = SiblingManagerBot()
    res = bot.ensure_siblings(dry_run=dry_run)
    state = "ok" if res.get("success") else "error"

    response = _build_response(ctx, command="repo.ensure", state=state, data=res)

    def _text() -> None:
        console.print(f"[bold cyan]Ensure Suite Siblings[/bold cyan] (Dry Run: {dry_run})")
        console.print("-" * 50)
        for r in res.get("results", []):
            name = r.get("name") or r.get("product_id")
            if r.get("action") == "already_present":
                console.print(f"  [green]✓[/green] [bold]{name}[/bold]: already installed ({r.get('path')})")
            elif r.get("action") == "would_install":
                console.print(f"  [yellow]?[/yellow] [bold]{name}[/bold]: would install from {r.get('repo')}")
            elif r.get("success"):
                console.print(f"  [green]✓[/green] [bold]{name}[/bold]: installed ({r.get('path')})")
            else:
                console.print(f"  [red]✗[/red] [bold]{name}[/bold]: failed — {r.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)

