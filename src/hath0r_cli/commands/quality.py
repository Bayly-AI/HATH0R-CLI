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
    """PR & Local Quality Gates bot — enforce SonarCloud thresholds locally via thresholds.json."""


@quality.command("init")
@click.option("--repo-root", type=click.Path(path_type=Path), default=None, help="Target repository root.")
@click.option("--install-missing", is_flag=True, default=False, help="Install missing test/lint/coverage libraries.")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing thresholds.json with canonical defaults.")
@click.pass_context
def quality_init(
    ctx: click.Context, repo_root: Path | None, install_missing: bool, overwrite: bool
) -> None:
    """Provision canonical <repo>/thresholds.json and verify/scaffold the repository testing system."""
    from hath0r_cli.bots.local_quality_gate_bot import LocalQualityGateBot

    bot = LocalQualityGateBot(cwd=repo_root or Path.cwd())
    res = bot.ensure_supporting_system(
        repo_root=repo_root,
        install_missing=install_missing,
        scaffold_missing=True,
        overwrite_thresholds=overwrite,
    )
    response = _build_response(ctx, command="quality.init", state="ok", data=res)

    def _text() -> None:
        click.echo(f"✓ Local Quality Gates initialized for '{res['repo_name']}' ({res['technology']})")
        click.echo(f"  • Thresholds file: {res['thresholds_file']}")
        click.echo(f"  • Libraries ready: {', '.join(res['libraries']['installed']) or 'none'}")
        if res["libraries"]["missing"]:
            click.echo(f"  • Missing libs:    {', '.join(res['libraries']['missing'])}")
        if res["scaffolded_files"]:
            click.echo(f"  • Scaffolded:      {', '.join(res['scaffolded_files'])}")

    _emit_response(ctx, response, text_renderer=_text)


@quality.command("local")
@click.option("--repo-root", type=click.Path(path_type=Path), default=None, help="Target repository root.")
@click.option("--all-files", is_flag=True, default=False, help="Analyze all source files instead of changed files only.")
@click.option("--no-auto-init", is_flag=True, default=False, help="Do not auto-create thresholds.json if missing.")
@click.pass_context
def quality_local(
    ctx: click.Context, repo_root: Path | None, all_files: bool, no_auto_init: bool
) -> None:
    """Evaluate Local Quality Gates (Errors, Coverage, Complexity, Duplication) against thresholds.json."""
    from hath0r_cli.bots.local_quality_gate_bot import LocalQualityGateBot

    bot = LocalQualityGateBot(cwd=repo_root or Path.cwd())
    res = bot.evaluate_local_gates(
        repo_root=repo_root,
        changed_only=not all_files,
        auto_init=not no_auto_init,
    )
    state = "ok" if res.get("passed") else "error"
    response = _build_response(ctx, command="quality.local", state=state, data=res)

    def _text() -> None:
        status_str = "PASSED" if res.get("passed") else "FAILED"
        click.echo(
            f"{'✓' if res.get('passed') else '✗'} Local Quality Gates {status_str} "
            f"for '{res.get('repo_name')}' (score={res.get('qgate_score'):.4f}, tech={res.get('technology')})"
        )
        gates = res.get("gates", {})
        err_g = gates.get("errors", {})
        cov_g = gates.get("coverage", {})
        cmp_g = gates.get("complexity", {})
        dup_g = gates.get("duplication", {})
        click.echo(
            f"  • Errors:      {err_g.get('actual_errors')} <= {err_g.get('max_errors')} "
            f"[{'PASS' if err_g.get('passed') else 'FAIL'}]"
        )
        click.echo(
            f"  • Coverage:    {cov_g.get('actual_coverage_pct')}% >= {cov_g.get('min_coverage_pct')}% "
            f"[{'PASS' if cov_g.get('passed') else 'FAIL'}]"
        )
        click.echo(
            f"  • Complexity:  max {cmp_g.get('max_observed_complexity')} <= {cmp_g.get('max_complexity')} "
            f"[{'PASS' if cmp_g.get('passed') else 'FAIL'}]"
        )
        click.echo(
            f"  • Duplication: {dup_g.get('duplicated_lines_pct')}% <= {dup_g.get('max_duplicated_lines_pct')}% "
            f"[{'PASS' if dup_g.get('passed') else 'FAIL'}]"
        )

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("passed"):
        ctx.exit(1)


@quality.command("ensure-all")
@click.option("--workspace-root", type=click.Path(path_type=Path), default=None, help="Workspace parent directory.")
@click.option("--install-missing", is_flag=True, default=False, help="Install missing supporting libraries.")
@click.pass_context
def quality_ensure_all(
    ctx: click.Context, workspace_root: Path | None, install_missing: bool
) -> None:
    """Provision thresholds.json and evaluate Local Quality Gates across all 5 suite repositories."""
    from hath0r_cli.bots.local_quality_gate_bot import LocalQualityGateBot

    bot = LocalQualityGateBot(cwd=Path.cwd())
    res = bot.ensure_all_repos(
        workspace_root=workspace_root,
        install_missing=install_missing,
        scaffold_missing=True,
    )
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="quality.ensure_all", state=state, data=res)

    def _text() -> None:
        click.echo(
            f"Local Quality Gates Fleet Rollout ({res.get('passed_count')}/{res.get('repos_count')} PASSED):"
        )
        for item in res.get("results", []):
            mark = "✓" if item.get("passed") else "✗"
            click.echo(
                f"  {mark} {item.get('repo_name')} ({item.get('technology')}): "
                f"score={item.get('qgate_score'):.4f} -> {item.get('thresholds_file')}"
            )

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


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


