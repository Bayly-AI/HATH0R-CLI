"""Dynamic Lazy Command Group for Hath0r CLI."""

from __future__ import annotations

import importlib
from typing import Any, Dict, List, Optional, Tuple

import click

COMMAND_REGISTRY: Dict[str, Tuple[str, str]] = {
    "doctor": ("hath0r_cli.commands.doctor", "doctor"),
    "init": ("hath0r_cli.commands.init_cmd", "init_cmd"),
    "kb": ("hath0r_cli.commands.kb", "kb"),
    "planes": ("hath0r_cli.commands.planes", "planes"),
    "schema": ("hath0r_cli.commands.planes", "schema"),
    "mcp": ("hath0r_cli.commands.mcp", "mcp"),
    "factory": ("hath0r_cli.commands.factory", "factory"),
    "branch": ("hath0r_cli.commands.branch", "branch"),
    "pr": ("hath0r_cli.commands.pr", "pr"),
    "janitor": ("hath0r_cli.commands.janitor", "janitor"),
    "task": ("hath0r_cli.commands.task", "task"),
    "jev": ("hath0r_cli.commands.jev", "jev"),
    "docker": ("hath0r_cli.commands.docker", "docker"),
    "quality": ("hath0r_cli.commands.quality", "quality"),
    "preflight": ("hath0r_cli.commands.preflight", "preflight"),
    "deploy": ("hath0r_cli.commands.deploy", "deploy"),
    "release": ("hath0r_cli.commands.release", "release"),
    "docs": ("hath0r_cli.commands.docs", "docs"),
    "issue": ("hath0r_cli.commands.issue", "issue"),
    "repo": ("hath0r_cli.commands.repo", "repo"),
    "clean-repos": ("hath0r_cli.commands.repo", "clean_repos_cmd"),
    "clean-repo": ("hath0r_cli.commands.repo", "clean_repo_cmd"),
    "voice": ("hath0r_cli.commands.voice", "voice"),
    "speak": ("hath0r_cli.commands.voice", "speak_group"),
    "playbook": ("hath0r_cli.commands.playbook", "playbook"),
    "context": ("hath0r_cli.commands.context", "context"),
    "memory": ("hath0r_cli.commands.memory", "memory"),
    "contracts": ("hath0r_cli.commands.contracts", "contracts"),
    "local": ("hath0r_cli.commands.local", "local_group"),
    "wasm": ("hath0r_cli.commands.wasm", "wasm_group"),
    "tui": ("hath0r_cli.commands.tui", "tui_cmd"),
    "serve": ("hath0r_cli.commands.serve", "serve_cmd"),
    "validate-change": ("hath0r_cli.commands.validate_cmd", "validate_change_cmd"),
    "vision": ("hath0r_cli.commands.vision", "vision"),
    "code": ("hath0r_cli.commands.code", "code"),
    "optimize": ("hath0r_cli.commands.optimize", "optimize"),
    "finops": ("hath0r_cli.commands.finops", "finops"),
    "agentgraph": ("hath0r_cli.commands.agentgraph", "agentgraph"),
    "design": ("hath0r_cli.commands.design", "design"),
    "observe": ("hath0r_cli.commands.observe", "observe_cmd"),
    "phoenix": ("hath0r_cli.commands.phoenix", "phoenix_cmd"),
    "cccd": ("hath0r_cli.commands.cccd", "cccd"),
    "cicccd": ("hath0r_cli.commands.cicccd", "cicccd"),
    "upgrade": ("hath0r_cli.commands.upgrade", "upgrade"),
    "churn": ("hath0r_cli.commands.churn", "churn"),
    "pmat": ("hath0r_cli.commands.pmat", "pmat_cmd"),
    "mesh": ("hath0r_cli.commands.mesh", "mesh_cmd"),
}


class Hath0rLazyGroup(click.Group):
    """Click command group that dynamically imports subcommands on demand."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._lazy_commands: Dict[str, Tuple[str, str]] = dict(COMMAND_REGISTRY)

    def list_commands(self, ctx: click.Context) -> List[str]:
        # Combine explicitly added commands and registered lazy commands
        cmd_set = set(super().list_commands(ctx))
        cmd_set.update(self._lazy_commands.keys())
        return sorted(cmd_set)

    def get_command(self, ctx: click.Context, cmd_name: str) -> Optional[click.Command]:
        # Check standard explicitly added commands first
        cmd = super().get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd

        # Check lazy commands registry
        if cmd_name in self._lazy_commands:
            mod_path, attr_name = self._lazy_commands[cmd_name]
            try:
                mod = importlib.import_module(mod_path)
                target = getattr(mod, attr_name)
                if isinstance(target, click.Command):
                    return target
            except Exception:
                return None
        return None
