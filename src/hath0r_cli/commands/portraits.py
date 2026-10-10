"""Verified biography portrait mining commands."""

import json

import click


@click.group()
def portraits():
    """Mine and verify government-first biography pictures."""


@portraits.command("sync")
@click.option("--config", default="cfg/portraits.yaml", show_default=True)
@click.option("--apply", is_flag=True, help="Publish only verified images with provenance.")
@click.option("--resume", is_flag=True, help="Resume this run from its JSONL checkpoint.")
@click.option("--limit", type=click.IntRange(min=1), default=None)
@click.option("--dry-run", is_flag=True)
def sync(config, apply, resume, limit, dry_run):
    from hath0r_cli.bots.portrait_sync import PortraitSyncBot

    try:
        result = PortraitSyncBot().sync(config=config, apply=apply, resume=resume, limit=limit, dry_run=dry_run)
    except (ValueError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps(result, indent=2))
