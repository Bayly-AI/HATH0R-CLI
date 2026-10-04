"""Release command for HATH0R CLI."""

from __future__ import annotations

from pathlib import Path

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def release() -> None:
    """Version + release notes + GitHub tag/release bot."""


@release.command("validate")
@click.pass_context
def release_validate(ctx: click.Context) -> None:
    """Validate VERSION SemVer and CHANGELOG alignment."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.validate()
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.validate", state=state, data=res)

    def _text() -> None:
        click.echo(res.get("message") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("notes")
@click.option("--version", default=None, help="Override VERSION file.")
@click.pass_context
def release_notes(ctx: click.Context, version: str | None) -> None:
    """Generate release notes from CHANGELOG section."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.generate_notes(version=version)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.notes", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(res.get("notes"))
        else:
            click.echo(res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("publish")
@click.option("--repo", default=None)
@click.option("--skip-github-release", is_flag=True, default=False)
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def release_publish(ctx: click.Context, repo: str | None, skip_github_release: bool, dry_run: bool) -> None:
    """Create annotated tag and optional GitHub Release."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.tag_and_release(repo=repo, dry_run=dry_run, skip_github_release=skip_github_release)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.publish", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("action") or res.get("tag") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("build")
@click.option(
    "--out", "out_dir", type=click.Path(path_type=Path), default=None, help="Output directory for release artifacts."
)
@click.option(
    "--previous-dir", type=click.Path(path_type=Path), default=None, help="Directory for previous version archives."
)
@click.option("--framework-dir", type=click.Path(path_type=Path), default=None, help="Framework release directory.")
@click.option("--no-rotate", is_flag=True, default=False, help="Skip rotating existing release artifacts to previous/.")
@click.option("--no-sync-framework", is_flag=True, default=False, help="Skip syncing release to Framework.")
@click.option("--checksums-only", is_flag=True, default=False, help="Recalculate checksums only.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate build without modifying files.")
@click.pass_context
def release_build(
    ctx: click.Context,
    out_dir: Path | None,
    previous_dir: Path | None,
    framework_dir: Path | None,
    no_rotate: bool,
    no_sync_framework: bool,
    checksums_only: bool,
    dry_run: bool,
) -> None:
    """Build release artifacts, rotate previous versions, and sync with Framework."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.build_and_rotate_artifacts(
        out_dir=out_dir,
        previous_dir=previous_dir,
        framework_dir=framework_dir,
        rotate=not no_rotate,
        sync_framework=not no_sync_framework,
        checksums_only=checksums_only,
        dry_run=dry_run,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.build", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(f"Release build complete for version {res.get('version')}.")
            if res.get("archived_path"):
                click.echo(f"Archived previous version to: {res.get('archived_path')}")
            if res.get("framework_synced"):
                click.echo("Synchronized release artifacts with Framework.")
        else:
            click.echo(f"Release build failed: {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@release.command("sync")
@click.option("--framework-dir", type=click.Path(path_type=Path), default=None, help="Framework release directory.")
@click.option("--dry-run", is_flag=True, default=False, help="Simulate sync without modifying files.")
@click.pass_context
def release_sync(
    ctx: click.Context,
    framework_dir: Path | None,
    dry_run: bool,
) -> None:
    """Synchronize latest release artifacts and previous archives to Framework."""
    from hath0r_cli.bots.quality import ReleaseBot

    bot = ReleaseBot(cwd=Path.cwd())
    res = bot.build_and_rotate_artifacts(
        framework_dir=framework_dir,
        rotate=False,
        sync_framework=True,
        checksums_only=True,
        dry_run=dry_run,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="release.sync", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo("Release artifacts synchronized successfully with Framework.")
        else:
            click.echo(f"Sync failed: {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)
