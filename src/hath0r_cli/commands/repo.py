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


# ============================================================================
# Voice Command Group (HATHOR-TS-006 / Issue #131)
# ============================================================================
