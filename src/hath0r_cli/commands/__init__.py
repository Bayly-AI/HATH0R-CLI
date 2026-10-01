"""HATH0R CLI Modular Command Registry."""

from __future__ import annotations

import click

from hath0r_cli.lazy_group import COMMAND_REGISTRY, Hath0rLazyGroup


def register_all_commands(cli: click.Group) -> None:
    """Register all modular commands on the root CLI click group."""
    if isinstance(cli, Hath0rLazyGroup):
        # Already dynamically resolved via lazy registry
        return

    # Fallback for standard click.Group instances
    for cmd_name, (mod_path, attr_name) in COMMAND_REGISTRY.items():
        try:
            import importlib

            mod = importlib.import_module(mod_path)
            cmd = getattr(mod, attr_name)
            if isinstance(cmd, click.Command):
                cli.add_command(cmd, name=cmd_name)
        except Exception:
            pass


__all__ = ["register_all_commands", "COMMAND_REGISTRY"]
