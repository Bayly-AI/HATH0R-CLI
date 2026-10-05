"""`hath0r upgrade` — automated, self-verifying CLI upgrade/install management."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import click

from hath0r_cli.common import _build_response, _emit_response
from hath0r_cli.envelope import Diagnostic

_TEST_LEVELS = click.Choice(["smoke", "full"], case_sensitive=False)


def _diag(code: str, message: str, severity: str = "error", remediation: str = "") -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=severity,
        remediation=remediation or None,
        provenance={"component": "hath0r-cli", "operation": "upgrade"},
    )


@click.group()
def upgrade() -> None:
    """Upgrade Bot: check, install, verify, roll back and announce CLI upgrades."""


@upgrade.command("check")
@click.option("--version", "target", default=None, help="Compare against a specific release (e.g. 0.9.0).")
@click.option("--repo", default=None, help="GitHub repo to read releases from (default Bayly-AI/HATH0R-CLI).")
@click.pass_context
def upgrade_check(ctx: click.Context, target: Optional[str], repo: Optional[str]) -> None:
    """Show the installed version, install method and whether a newer release exists."""
    from hath0r_cli.bots.upgrade_bot import DEFAULT_REPO, UpgradeBot

    res = UpgradeBot(cwd=Path.cwd(), repo=repo or DEFAULT_REPO).check(version=target)
    state = "ok" if res.get("success") else "error"
    diags = []
    if not res.get("success"):
        failure = res.get("failure") or {}
        diags.append(
            _diag(
                failure.get("code", "UPGRADE_CHECK_FAILED"), res.get("error", ""), remediation=failure.get("hint", "")
            )
        )
    response = _build_response(ctx, command="upgrade.check", state=state, data=res, diagnostics=diags)

    def _text() -> None:
        install = res.get("install") or {}
        click.echo(f"Installed : {install.get('version')} ({install.get('method')})")
        if res.get("success"):
            click.echo(f"Latest    : {res.get('latest_version')}")
        click.echo(res.get("message") or res.get("error"))

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


def _render_report(report: Dict[str, Any], announcement: Optional[Dict[str, Any]]) -> None:
    click.echo(report.get("message", ""))
    for st in report.get("stages", []):
        mark = "✓" if st.get("status") == "ok" else "✗"
        click.echo(f"  {mark} {st.get('stage')}")
    for check in (report.get("verification") or {}).get("checks", []):
        mark = "✓" if check["passed"] else ("✗" if check["required"] else "!")
        click.echo(f"      {mark} {check['name']}: {check['detail'].splitlines()[0] if check['detail'] else ''}")
    if report.get("rollback"):
        rb = report["rollback"]
        click.echo(f"  Rollback: {'succeeded' if rb.get('success') else 'FAILED'}")
    if announcement:
        if announcement.get("issue", {}).get("url"):
            click.echo(f"  Issue: {announcement['issue']['url']}")
        if not announcement.get("success"):
            click.echo(f"  {announcement.get('message')}")


@upgrade.command("run")
@click.option("--version", "target", default=None, help="Install a specific release instead of the latest.")
@click.option("--force", is_flag=True, default=False, help="Reinstall even when already up to date.")
@click.option(
    "--tests",
    "test_level",
    type=_TEST_LEVELS,
    default="smoke",
    show_default=True,
    help="Verification depth: smoke checks, or smoke + full unit tests (source checkouts).",
)
@click.option(
    "--no-rollback", is_flag=True, default=False, help="Leave the new version in place if verification fails."
)
@click.option(
    "--file-issue/--no-file-issue",
    default=False,
    show_default=True,
    help="On failure, open (or update) a GitHub issue describing what to fix.",
)
@click.option("--no-speak", is_flag=True, default=False, help="Do not queue a spoken announcement.")
@click.option("--repo", default=None, help="GitHub repo for releases and issues (default Bayly-AI/HATH0R-CLI).")
@click.option("--dry-run", is_flag=True, default=False, help="Plan the upgrade without changing anything.")
@click.pass_context
def upgrade_run(
    ctx: click.Context,
    target: Optional[str],
    force: bool,
    test_level: str,
    no_rollback: bool,
    file_issue: bool,
    no_speak: bool,
    repo: Optional[str],
    dry_run: bool,
) -> None:
    """Upgrade the CLI, test the result, roll back on failure and announce the outcome."""
    from hath0r_cli.bots.upgrade_bot import DEFAULT_REPO, UpgradeAnnouncerBot, UpgradeBot

    repo = repo or DEFAULT_REPO
    bot = UpgradeBot(cwd=Path.cwd(), repo=repo)
    report = bot.run(
        version=target, force=force, dry_run=dry_run, test_level=test_level.lower(), auto_rollback=not no_rollback
    )
    announcement = None
    if report.get("outcome") not in ("up-to-date", "dry-run"):
        announcement = UpgradeAnnouncerBot(cwd=Path.cwd(), repo=repo).announce(
            report, file_issue=file_issue, speak=not no_speak, dry_run=dry_run
        )
        report["announcement"] = announcement

    diags = []
    if not report.get("success"):
        failure = report.get("failure") or {}
        diags.append(
            _diag(
                failure.get("code", "UPGRADE_FAILED"),
                failure.get("message", ""),
                severity="error",
                remediation=failure.get("hint", ""),
            )
        )
    # exit-codes contract: exit 1 → state error; exit 6 (rollback failed, install unhealthy) → degraded.
    state = "ok" if report.get("success") else ("degraded" if report.get("outcome") == "rollback-failed" else "error")
    response = _build_response(ctx, command="upgrade.run", state=state, data=report, diagnostics=diags, dry_run=dry_run)
    _emit_response(ctx, response, text_renderer=lambda: _render_report(report, announcement))
    code = int(report.get("exit_code", 0 if report.get("success") else 1))
    if code:
        ctx.exit(code)


@upgrade.command("verify")
@click.option("--tests", "test_level", type=_TEST_LEVELS, default="smoke", show_default=True)
@click.option("--expect-version", default=None, help="Version the install must report (default: current).")
@click.option("--announce", "do_announce", is_flag=True, default=False, help="Announce failures (voice queue).")
@click.option("--file-issue", is_flag=True, default=False, help="On failure, open/update a GitHub issue.")
@click.option("--repo", default=None)
@click.pass_context
def upgrade_verify(
    ctx: click.Context,
    test_level: str,
    expect_version: Optional[str],
    do_announce: bool,
    file_issue: bool,
    repo: Optional[str],
) -> None:
    """Test the currently installed CLI (use after a fresh or manual install)."""
    from hath0r_cli.bots.upgrade_bot import DEFAULT_REPO, UpgradeAnnouncerBot, UpgradeBot, UpgradeVerifierBot

    repo = repo or DEFAULT_REPO
    bot = UpgradeBot(cwd=Path.cwd(), repo=repo)
    install = bot.detect_install()
    verifier = UpgradeVerifierBot(cwd=Path.cwd())
    result = verifier.verify(
        expect_version or install.version,
        level=test_level.lower(),
        command=verifier.command_for(install),
        repo_root=install.repo_root or None,
    )
    data: Dict[str, Any] = {"install": install.to_dict(), "verification": result, "passed": result["passed"]}
    if not result["passed"] and (do_announce or file_issue):
        report = {
            "run_id": "verify",
            "outcome": "failed",
            "success": False,
            "install": install.to_dict(),
            "from_version": install.version,
            "to_version": expect_version or install.version,
            "test_level": test_level,
            "verification": result,
            "failure": {
                "stage": "verify",
                "code": "VERIFICATION_FAILED",
                "message": result["summary"],
                "hint": "Reinstall the release, or run `hath0r upgrade rollback` if you just upgraded.",
            },
            "message": f"Install verification failed: {result['summary']}",
        }
        data["announcement"] = UpgradeAnnouncerBot(cwd=Path.cwd(), repo=repo).announce(report, file_issue=file_issue)
    state = "ok" if result["passed"] else "error"
    response = _build_response(ctx, command="upgrade.verify", state=state, data=data)

    def _text() -> None:
        click.echo(f"hath0r {install.version} ({install.method}) — {result['summary']}")
        for check in result["checks"]:
            mark = "✓" if check["passed"] else ("✗" if check["required"] else "!")
            click.echo(f"  {mark} {check['name']}: {check['detail'].splitlines()[0] if check['detail'] else ''}")

    _emit_response(ctx, response, text_renderer=_text)
    if not result["passed"]:
        ctx.exit(1)


@upgrade.command("rollback")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def upgrade_rollback(ctx: click.Context, dry_run: bool) -> None:
    """Restore the install snapshot recorded by the last upgrade run."""
    from hath0r_cli.bots.upgrade_bot import UpgradeBot

    bot = UpgradeBot(cwd=Path.cwd())
    snap = bot.last_snapshot()
    if not snap:
        res: Dict[str, Any] = {"success": False, "error": "No snapshot recorded — nothing to roll back to."}
    elif dry_run:
        res = {
            "success": True,
            "dry_run": True,
            "snapshot": snap,
            "action": f"[DRY-RUN] Would restore {snap.get('method')} install of {snap.get('version')}.",
        }
    else:
        res = bot.rollback(snap)
        res["snapshot"] = snap
    response = _build_response(
        ctx, command="upgrade.rollback", state="ok" if res.get("success") else "error", data=res, dry_run=dry_run
    )

    def _text() -> None:
        if res.get("success"):
            click.echo(res.get("action") or f"Restored hath0r {snap.get('version') if snap else ''}.")
        else:
            click.echo(f"Rollback failed: {res.get('error')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@upgrade.command("status")
@click.option("--limit", default=10, show_default=True, help="History entries to show.")
@click.pass_context
def upgrade_status(ctx: click.Context, limit: int) -> None:
    """Show the last upgrade report and recent history."""
    from hath0r_cli.bots.upgrade_bot import UpgradeBot

    res = UpgradeBot(cwd=Path.cwd()).status(limit=limit)
    response = _build_response(ctx, command="upgrade.status", state="ok", data=res)

    def _text() -> None:
        click.echo(res["message"])
        for h in res["history"]:
            extra = f" ({h['failure']})" if h.get("failure") else ""
            click.echo(
                f"  {h.get('finished_at')}  {h.get('outcome'):<16} {h.get('from_version')} → {h.get('to_version')}{extra}"
            )

    _emit_response(ctx, response, text_renderer=_text)


@upgrade.command("schedule")
@click.option("--hour", default=4, show_default=True, type=click.IntRange(0, 23))
@click.option("--minute", default=17, show_default=True, type=click.IntRange(0, 59))
@click.option("--no-file-issue", is_flag=True, default=False, help="Scheduled runs will not open GitHub issues.")
@click.option("--write", is_flag=True, default=False, help="Write the launchd plist to ~/Library/LaunchAgents.")
@click.pass_context
def upgrade_schedule(ctx: click.Context, hour: int, minute: int, no_file_issue: bool, write: bool) -> None:
    """Print (or write) a nightly unattended upgrade schedule (launchd plist / crontab line)."""
    from hath0r_cli.bots.upgrade_bot import LAUNCHD_LABEL, UpgradeBot

    spec = UpgradeBot(cwd=Path.cwd()).schedule_spec(hour=hour, minute=minute, file_issue=not no_file_issue)
    if write:
        path = Path(spec["plist_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(spec["plist"], encoding="utf-8")
        spec["written"] = str(path)
        spec["next_step"] = (
            f"launchctl bootstrap gui/$(id -u) {path}   # remove: launchctl bootout gui/$(id -u)/{LAUNCHD_LABEL}"
        )
    response = _build_response(ctx, command="upgrade.schedule", state="ok", data=spec)

    def _text() -> None:
        if write:
            click.echo(f"Wrote {spec['written']}\nActivate with:\n  {spec['next_step']}")
        else:
            click.echo(spec["plist"])
            click.echo(f"# crontab alternative:\n{spec['cron']}")

    _emit_response(ctx, response, text_renderer=_text)
