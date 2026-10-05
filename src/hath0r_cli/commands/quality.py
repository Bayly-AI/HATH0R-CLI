"""Quality command for HATH0R CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import click

from hath0r_cli.common import (
    _build_response,
    _emit_response,
)


@click.group()
def quality() -> None:
    """PR Quality Gates bot — aggregate hard gates including SonarCloud."""


@quality.command("check")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="owner/repo")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def quality_check(ctx: click.Context, pr_number: int, repo: str | None, dry_run: bool) -> None:
    """Evaluate PR status checks against configured hard gates."""
    from hath0r_cli.bots.quality import QualityGateBot

    bot = QualityGateBot(cwd=Path.cwd())
    res = bot.check_pr(pr_number, repo=repo, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="quality.check", state=state, dry_run=dry_run, data=res)

    def _text() -> None:
        click.echo(res.get("message") or json.dumps(res, indent=2))
        if res.get("hard_failures"):
            click.echo(f"Hard failures: {', '.join(res['hard_failures'])}")
        if res.get("hard_missing"):
            click.echo(f"Missing gates: {', '.join(res['hard_missing'])}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@quality.command("sonar")
@click.option("--project-key", default=None, help="SonarCloud project key (defaults to sonar-project.properties).")
@click.option("--organization", default="bayly-ai", help="SonarCloud organization key.")
@click.pass_context
def quality_sonar(ctx: click.Context, project_key: str | None, organization: str) -> None:
    """Inspect real-time SonarCloud Quality Gate status and list blocking issues."""
    from hath0r_cli.bots.quality import QualityGateBot

    bot = QualityGateBot(cwd=Path.cwd())
    res = bot.check_sonar(project_key=project_key, organization=organization)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="quality.sonar", state=state, data=res)

    def _text() -> None:
        if res.get("success"):
            click.echo(f"✓ {res.get('message')}")
        else:
            click.echo(f"✗ {res.get('message')}")
            if res.get("failing_conditions"):
                click.echo("\nFailing Quality Gate Conditions:")
                for cond in res["failing_conditions"]:
                    metric = cond.get("metricKey", "")
                    actual = cond.get("actualValue", "")
                    thresh = cond.get("errorThreshold", "")
                    op = cond.get("comparator", "")
                    click.echo(f"  - {metric}: actual {actual} (threshold {op} {thresh})")
            if res.get("blocking_issues"):
                click.echo(f"\nTop Unresolved Issues ({len(res['blocking_issues'])} total):")
                for iss in res["blocking_issues"][:10]:
                    click.echo(f"  [{iss.get('severity')}] {iss.get('component')}:{iss.get('line')} - {iss.get('message')} ({iss.get('rule')})")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@quality.command("repair")
@click.option(
    "--input-file",
    "-f",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="JSON/YAML file containing malformed payload.",
)
@click.option("--raw-string", "-s", default=None, help="Raw payload string to repair directly.")
@click.option(
    "--schema-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Optional JSON schema for coercion.",
)
@click.pass_context
def quality_repair(
    ctx: click.Context, input_file: Path | None, raw_string: str | None, schema_file: Path | None
) -> None:
    """Repair and sanitize malformed JSON payload using deterministic schema repair rules."""
    from hath0r_cli.schema_repair import SchemaRepairEngine

    if input_file:
        raw_text = input_file.read_text(encoding="utf-8")
    elif raw_string:
        raw_text = raw_string
    else:
        raise click.UsageError("Must provide either --input-file or --raw-string.")

    schema = None
    if schema_file:
        schema = json.loads(schema_file.read_text(encoding="utf-8"))

    engine = SchemaRepairEngine()
    try:
        repaired = engine.repair_json(raw_text, schema=schema)
        response = _build_response(
            ctx,
            command="quality.repair",
            state="ok",
            data={
                "repaired": True,
                "payload": repaired,
            },
        )

        def _text() -> None:
            click.echo("✓ Payload Repaired Successfully:")
            click.echo(json.dumps(repaired, indent=2))

        _emit_response(ctx, response, text_renderer=_text)
    except Exception as exc:
        response = _build_response(
            ctx,
            command="quality.repair",
            state="error",
            data={"repaired": False, "error": str(exc)},
        )
        _emit_response(ctx, response)
        ctx.exit(1)


def _render_sonar_text(res: Dict[str, Any]) -> None:
    if res.get("success"):
        click.echo(f"✓ SonarCloud Quality Gate PASSED ({res.get('status')}) for '{res.get('project_key')}'")
        return

    click.echo(
        f"✗ SonarCloud Quality Gate FAILED (status: {res.get('status')}) for '{res.get('project_key')}'. "
        f"Fix {len(res.get('failing_conditions', []))} failing condition(s) and {res.get('total_blocking_issues', 0)} issue(s) before proceeding.\n"
    )
    for c in res.get("failing_conditions", []):
        click.echo(f"  - {c.get('metric')}: actual {c.get('actual')} (threshold {c.get('comparator')} {c.get('threshold')})")
    if res.get("blocking_issues"):
        click.echo(f"\nTop Unresolved Issues ({res.get('total_blocking_issues')} total):")
        for iss in res["blocking_issues"][:10]:
            click.echo(f"  [{iss.get('severity')}] {iss.get('component')}:{iss.get('line')} - {iss.get('message')} ({iss.get('rule')})")


@quality.command("sonar")
@click.option("--project-key", default=None, help="SonarCloud project key (defaults to sonar-project.properties).")
@click.pass_context
def quality_sonar(ctx: click.Context, project_key: str | None) -> None:
    """Check live SonarCloud Quality Gate status via SonarCloud Web API."""
    from hath0r_cli.bots.quality import QualityGateBot

    bot = QualityGateBot(cwd=Path.cwd())
    res = bot.check_sonar(project_key=project_key)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="quality.sonar", state=state, data=res)

    _emit_response(ctx, response, text_renderer=lambda: _render_sonar_text(res))
    if not res.get("success"):
        ctx.exit(1)
