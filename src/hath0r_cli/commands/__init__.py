"""HATH0R CLI Modular Command Registry."""

from __future__ import annotations

import click

from hath0r_cli.commands.branch import branch
from hath0r_cli.commands.context import context
from hath0r_cli.commands.contracts import contracts
from hath0r_cli.commands.deploy import deploy
from hath0r_cli.commands.docker import docker
from hath0r_cli.commands.docs import docs
from hath0r_cli.commands.doctor import doctor
from hath0r_cli.commands.factory import factory
from hath0r_cli.commands.init_cmd import init_cmd
from hath0r_cli.commands.issue import issue
from hath0r_cli.commands.janitor import janitor
from hath0r_cli.commands.jev import jev
from hath0r_cli.commands.kb import kb
from hath0r_cli.commands.local import local_group
from hath0r_cli.commands.mcp import mcp
from hath0r_cli.commands.memory import memory
from hath0r_cli.commands.planes import planes, schema
from hath0r_cli.commands.playbook import playbook
from hath0r_cli.commands.pr import pr
from hath0r_cli.commands.preflight import preflight
from hath0r_cli.commands.quality import quality
from hath0r_cli.commands.release import release
from hath0r_cli.commands.repo import clean_repo_cmd, clean_repos_cmd, repo
from hath0r_cli.commands.serve import serve_cmd
from hath0r_cli.commands.task import task
from hath0r_cli.commands.tui import tui_cmd
from hath0r_cli.commands.validate_cmd import validate_change_cmd
from hath0r_cli.commands.voice import speak_group, voice
from hath0r_cli.commands.wasm import wasm_group


def register_all_commands(cli: click.Group) -> None:
    """Register all modular commands and command groups on the root CLI click group."""
    cli.add_command(doctor)
    cli.add_command(init_cmd, name="init")
    cli.add_command(kb)
    cli.add_command(planes, name="planes")
    cli.add_command(schema, name="schema")
    cli.add_command(mcp)
    cli.add_command(factory)
    cli.add_command(branch)
    cli.add_command(pr)
    cli.add_command(janitor)
    cli.add_command(task)
    cli.add_command(jev)
    cli.add_command(docker)
    cli.add_command(quality)
    cli.add_command(preflight)
    cli.add_command(deploy)
    cli.add_command(release)
    cli.add_command(docs)
    cli.add_command(issue)
    cli.add_command(repo)
    cli.add_command(clean_repos_cmd, name="clean-repos")
    cli.add_command(clean_repo_cmd, name="clean-repo")
    cli.add_command(voice)
    cli.add_command(speak_group, name="speak")
    cli.add_command(playbook)
    cli.add_command(context)
    cli.add_command(memory)
    cli.add_command(contracts)
    cli.add_command(local_group)
    cli.add_command(wasm_group)
    cli.add_command(tui_cmd)
    cli.add_command(serve_cmd)
    cli.add_command(validate_change_cmd)


__all__ = ["register_all_commands"]

