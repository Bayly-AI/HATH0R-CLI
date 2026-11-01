"""`hath0r install-wizard` / `hath0r setup` — Guided & Unattended Install Wizard for Hath0r CLI and Hath0r MCP (Docker)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.panel import Panel
from rich.table import Table

from hath0r_cli.bots.install_wizard_bot import (
    DEFAULT_MCP_PORT,
    INSTALL_METHODS,
    InstallWizardBot,
    default_bin_dir,
    install_home,
)
from hath0r_cli.common import _build_response, _emit_response, console
from hath0r_cli.envelope import Diagnostic

_METHOD_CHOICES = click.Choice(list(INSTALL_METHODS), case_sensitive=False)


def _diag(code: str, message: str, severity: str = "error", remediation: str = "") -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=severity,
        remediation=remediation or None,
        provenance={"component": "hath0r-cli", "operation": "install-wizard"},
    )


def _render_wizard_report(report: Dict[str, Any]) -> None:
    title = "✓ Hath0r Install Wizard Complete" if report.get("success") else "✗ Hath0r Install Wizard Failed"
    style = "bold green" if report.get("success") else "bold red"
    console.print(Panel(report.get("message", ""), title=title, border_style=style))

    table = Table(title="Install Wizard Pipeline Stages")
    table.add_column("Stage", style="bold cyan")
    table.add_column("Status")
    table.add_column("Details", style="white")
    for st in report.get("stages", []):
        status = st.get("status", "")
        mark = "[green]✓ ok[/green]" if status == "ok" else (
            "[yellow]- skipped[/yellow]" if status == "skipped" else "[red]✗ failed[/red]"
        )
        extras = ", ".join(f"{k}={v}" for k, v in st.items() if k not in ("stage", "status") and v is not None)
        table.add_row(str(st.get("stage", "")), mark, extras)
    console.print(table)

    failure = report.get("failure")
    if failure:
        console.print(f"[bold red]Failure ({failure.get('code')}):[/bold red] {failure.get('message')}")
        if failure.get("hint"):
            console.print(f"[yellow]Remediation:[/yellow] {failure.get('hint')}")


@click.group("install-wizard", invoke_without_command=True)
@click.pass_context
def install_wizard(ctx: click.Context) -> None:
    """Install Wizard: install dependencies, global Hath0r CLI, and Hath0r MCP Docker container."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@install_wizard.command("run")
@click.option("--version", "target_version", default=None, help="Specific CLI/MCP release version (default: latest).")
@click.option(
    "--method",
    type=_METHOD_CHOICES,
    default=None,
    help="Global CLI install method: pipx (recommended), binary, or pip.",
)
@click.option(
    "--bin-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Global binary target directory (default: /usr/local/bin or ~/.local/bin).",
)
@click.option(
    "--mcp-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory to stage Hath0r MCP Dockerfile and docker-compose.yml (default: ~/.hath0r/mcp).",
)
@click.option(
    "--mcp-port",
    default=DEFAULT_MCP_PORT,
    show_default=True,
    type=int,
    help="Host port to bind Hath0r-MCP container (127.0.0.1:<port>:8083).",
)
@click.option(
    "--image-url",
    default=None,
    help="Optional remote container registry image URL (default: build locally from staged Dockerfile).",
)
@click.option("--skip-docker", is_flag=True, default=False, help="Stage MCP files without launching the Docker container.")
@click.option(
    "--install-claude",
    is_flag=True,
    default=False,
    help="Also register Hath0r CLI and MCP connectors in Claude Desktop config.",
)
@click.option("-y", "--yes", "auto_approve", is_flag=True, default=False, help="Run non-interactively accepting defaults.")
@click.option("--dry-run", is_flag=True, default=False, help="Preview all wizard stages without mutating the system.")
@click.pass_context
def wizard_run(
    ctx: click.Context,
    target_version: Optional[str],
    method: Optional[str],
    bin_dir: Optional[Path],
    mcp_dir: Optional[Path],
    mcp_port: int,
    image_url: Optional[str],
    skip_docker: bool,
    install_claude: bool,
    auto_approve: bool,
    dry_run: bool,
) -> None:
    """Run the 5-stage Install Wizard (dependencies -> global CLI -> MCP Dockerfile -> Docker launch -> verify)."""
    resolved_bin = (bin_dir or default_bin_dir()).resolve()
    bot = InstallWizardBot(cwd=Path.cwd(), bin_dir=resolved_bin)

    is_tty = sys.stdin.isatty() and ctx.obj.get("output", "auto") != "json"
    chosen_method = method
    chosen_mcp_dir = mcp_dir
    chosen_port = mcp_port
    chosen_image = image_url

    if is_tty and not auto_approve and not dry_run:
        console.print(
            Panel(
                "[bold cyan]Hath0r CLI + Hath0r MCP (Docker) Install Wizard[/bold cyan]\n"
                "1. Inspect & install dependencies (Python >=3.10, pipx, Git, Docker, Compose v2)\n"
                "2. Install `hath0r` CLI globally on PATH\n"
                "3. Stage Hath0r MCP Dockerfile, docker-compose.yml & seed knowledgebase\n"
                "4. Provision `hath0r-net` & launch `Hath0r-MCP` via Docker\n"
                "5. Verify `/ready` endpoint & write `INSTALL_RECEIPT.json`",
                title="Welcome to Hath0r Setup",
                border_style="cyan",
            )
        )
        default_m = chosen_method or ("pipx" if bot.check_dependencies()["pipx"]["ok"] else "binary")
        chosen_method = click.prompt(
            "Global CLI install method (pipx / binary / pip)",
            default=default_m,
            type=_METHOD_CHOICES,
        )
        entered_port = click.prompt("Hath0r-MCP host port", default=chosen_port, type=int)
        chosen_port = int(entered_port)
        if not chosen_image:
            entered_img = click.prompt(
                "MCP Container Image URL (press Enter to build locally from Dockerfile)",
                default="",
                show_default=False,
            )
            if entered_img.strip():
                chosen_image = entered_img.strip()

    report = bot.run_wizard(
        version=target_version,
        method=chosen_method,
        mcp_dir=chosen_mcp_dir,
        mcp_port=chosen_port,
        image_url=chosen_image,
        skip_docker=skip_docker,
        install_claude=install_claude,
        auto_approve=True,
        dry_run=dry_run,
    )

    diags = []
    if not report.get("success"):
        failure = report.get("failure") or {}
        diags.append(
            _diag(
                failure.get("code", "INSTALL_WIZARD_FAILED"),
                failure.get("message", report.get("message", "")),
                remediation=failure.get("hint", ""),
            )
        )

    state = "ok" if report.get("success") else "error"
    response = _build_response(
        ctx,
        command="install-wizard.run",
        state=state,
        data=report,
        diagnostics=diags,
        dry_run=dry_run,
    )
    _emit_response(ctx, response, text_renderer=lambda: _render_wizard_report(report))
    if not report.get("success"):
        ctx.exit(1)


@install_wizard.command("check")
@click.option("--mcp-port", default=DEFAULT_MCP_PORT, show_default=True, type=int, help="Expected Hath0r-MCP host port.")
@click.pass_context
def wizard_check(ctx: click.Context, mcp_port: int) -> None:
    """Check system dependencies, global CLI PATH, Docker daemon, hath0r-net, and Hath0r-MCP health."""
    bot = InstallWizardBot(cwd=Path.cwd())
    res = bot.check_environment(mcp_port=mcp_port)
    state = "ok" if res.get("healthy") else "degraded"
    response = _build_response(ctx, command="install-wizard.check", state=state, data=res)

    def _text() -> None:
        deps = res["dependencies"]
        cli_info = res["cli"]
        mcp_info = res["mcp_docker"]

        table = Table(title="Hath0r Install Wizard — Environment Check")
        table.add_column("Component", style="bold cyan")
        table.add_column("Status")
        table.add_column("Detail", style="white")

        for key, label in (
            ("python", "Python >= 3.10"),
            ("pipx", "pipx"),
            ("git", "Git"),
            ("curl", "curl"),
            ("docker", "Docker CLI"),
            ("docker_compose", "Docker Compose v2"),
            ("docker_daemon", "Docker Daemon"),
        ):
            item = deps.get(key, {})
            ok = bool(item.get("ok"))
            detail = item.get("version") or item.get("path") or item.get("detail") or ""
            table.add_row(label, "[green]✓ OK[/green]" if ok else "[yellow]! MISSING[/yellow]", str(detail))

        table.add_row(
            "Hath0r CLI (PATH)",
            "[green]✓ OK[/green]" if cli_info.get("on_path") else "[red]✗ NOT ON PATH[/red]",
            f"{cli_info.get('version')} ({cli_info.get('method')}) -> {cli_info.get('which') or 'missing'}",
        )
        table.add_row(
            "Docker Network (hath0r-net)",
            "[green]✓ OK[/green]" if mcp_info.get("network_present") else "[yellow]! NOT CREATED[/yellow]",
            mcp_info.get("network", "hath0r-net"),
        )
        table.add_row(
            "Hath0r-MCP Container",
            "[green]✓ RUNNING[/green]" if mcp_info.get("container_running") else "[yellow]! STOPPED[/yellow]",
            f"{mcp_info.get('container_name')} (port {mcp_info.get('port')})",
        )
        table.add_row(
            "Hath0r-MCP /ready",
            "[green]✓ READY[/green]" if mcp_info.get("ready") else "[yellow]! UNREACHABLE[/yellow]",
            f"http://127.0.0.1:{mcp_info.get('port')}/ready",
        )
        console.print(table)

    _emit_response(ctx, response, text_renderer=_text)


@install_wizard.command("status")
@click.option("--mcp-port", default=DEFAULT_MCP_PORT, show_default=True, type=int)
@click.pass_context
def wizard_status(ctx: click.Context, mcp_port: int) -> None:
    """Show the latest INSTALL_RECEIPT.json and live status of CLI + Hath0r-MCP container."""
    bot = InstallWizardBot(cwd=Path.cwd())
    res = bot.status(mcp_port=mcp_port)
    response = _build_response(ctx, command="install-wizard.status", state="ok", data=res)

    def _text() -> None:
        console.print(f"[bold cyan]{res['message']}[/bold cyan]")
        console.print(f"Receipt File: {res['receipt_file']}")
        env = res.get("environment") or {}
        cli_info = env.get("cli") or {}
        mcp_info = env.get("mcp_docker") or {}
        console.print(f"  • CLI: hath0r {cli_info.get('version')} ({cli_info.get('method')}) at {cli_info.get('which')}")
        console.print(
            f"  • MCP Container: {mcp_info.get('container_name')} "
            f"(running={mcp_info.get('container_running')}, ready={mcp_info.get('ready')})"
        )

    _emit_response(ctx, response, text_renderer=_text)


@install_wizard.command("repair")
@click.option("--mcp-dir", type=click.Path(path_type=Path), default=None)
@click.option("--mcp-port", default=DEFAULT_MCP_PORT, show_default=True, type=int)
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def wizard_repair(ctx: click.Context, mcp_dir: Optional[Path], mcp_port: int, dry_run: bool) -> None:
    """Re-provision hath0r-net, rebuild/restart Hath0r-MCP container, and verify CLI PATH."""
    bot = InstallWizardBot(cwd=Path.cwd())
    res = bot.repair(mcp_dir=mcp_dir, mcp_port=mcp_port, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="install-wizard.repair", state=state, data=res, dry_run=dry_run)

    def _text() -> None:
        mark = "✓" if res.get("success") else "✗"
        click.echo(f"{mark} {res.get('message')}")

    _emit_response(ctx, response, text_renderer=_text)
    if not res.get("success"):
        ctx.exit(1)


@install_wizard.command("uninstall")
@click.option("--mcp-dir", type=click.Path(path_type=Path), default=None)
@click.option("--purge-data", is_flag=True, default=False, help="Also remove staged ~/.hath0r/mcp directory.")
@click.option("--dry-run", is_flag=True, default=False)
@click.pass_context
def wizard_uninstall(ctx: click.Context, mcp_dir: Optional[Path], purge_data: bool, dry_run: bool) -> None:
    """Stop and remove the Hath0r-MCP Docker container deployed by the wizard."""
    bot = InstallWizardBot(cwd=Path.cwd())
    res = bot.uninstall(mcp_dir=mcp_dir, purge_data=purge_data, dry_run=dry_run)
    response = _build_response(ctx, command="install-wizard.uninstall", state="ok", data=res, dry_run=dry_run)

    def _text() -> None:
        click.echo(res.get("action") or res.get("message"))

    _emit_response(ctx, response, text_renderer=_text)


@install_wizard.command("package")
@click.option(
    "--target",
    type=click.Choice(["all", "dmg", "exe"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Target installer format to build: all (.dmg + .exe), dmg (macOS), or exe (Windows x64).",
)
@click.option("--out-dir", type=click.Path(path_type=Path), default=None, help="Output directory (default: release/).")
@click.option("--version", "target_version", default=None, help="Version label (default: VERSION file).")
@click.option("--dry-run", is_flag=True, default=False, help="Preview installer packaging without writing files.")
@click.pass_context
def wizard_package(
    ctx: click.Context,
    target: str,
    out_dir: Optional[Path],
    target_version: Optional[str],
    dry_run: bool,
) -> None:
    """Build native macOS (.dmg) and Windows (.exe) launchers for the Hath0r Install Wizard."""
    bot = InstallWizardBot(cwd=Path.cwd())
    res = bot.build_installers(out_dir=out_dir, version=target_version, target=target, dry_run=dry_run)
    state = "ok" if res.get("success") else "error"
    response = _build_response(ctx, command="install-wizard.package", state=state, data=res, dry_run=dry_run)

    def _text() -> None:
        console.print(f"[bold green]✓ {res.get('message')}[/bold green]")
        if "macos_dmg" in res:
            dmg = res["macos_dmg"]
            console.print(f"  • macOS DMG:   {dmg.get('dmg_path')} ({dmg.get('versioned_dmg_path')})")
        if "windows_exe" in res:
            exe = res["windows_exe"]
            console.print(f"  • Windows EXE: {exe.get('exe_path')} ({exe.get('versioned_exe_path')})")

    _emit_response(ctx, response, text_renderer=_text)


__all__ = ["install_wizard", "install_home"]
