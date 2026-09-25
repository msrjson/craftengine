"""Every CLI command the engine or its documentation tells a developer to run exists.

Agents copy commands from printed "Next steps" and from the guides verbatim.
A command that does not exist costs them a failed run and a guess.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import re

import pytest
from typer.testing import CliRunner

from craft.cli import app as cli_module

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: `python dev.py <command> [<subcommand>]` in prose or code.
_COMMAND = re.compile(r"dev\.py ([a-z][a-z-]*(?::[a-z][a-z-]*)?)(?: ([a-z][a-z-]+))?")

#: Destructive commands the documentation names only to say they are refused.
_REFUSED = {"migrate reset", "migrate refresh", "migrate fresh", "migrate rollback", "db wipe", "db drop"}

#: Words after a command that are prose, not a subcommand.
_PROSE = {"and", "or", "to", "with", "then", "first", "again", "on", "in", "for", "from", "is"}

_SOURCES = ["documentation", "engine", "README.md", "AGENTS.md", "llms.txt", "CRAFT_ENGINE.md"]

#: Mirrors `dev.py`: a leading `group:command` token is split in two.
_ATOMIC = {"key:generate"}


def _files():
    for source in _SOURCES:
        path = os.path.join(ROOT, source)
        if os.path.isfile(path):
            yield path
        for folder, _, names in os.walk(path):
            for name in names:
                if name.endswith((".md", ".py", ".stub", ".txt")):
                    yield os.path.join(folder, name)


def _argv(head: str, tail: str) -> list:
    words = head.split(":", 1) if ":" in head and head not in _ATOMIC else [head]
    if tail and tail not in _PROSE and len(words) == 1:
        words.append(tail)
    return words


def _documented_commands() -> dict:
    found: dict = {}
    for path in _files():
        with open(path, encoding="utf-8") as handle:
            for match in _COMMAND.finditer(handle.read()):
                argv = _argv(match.group(1), match.group(2) or "")
                found.setdefault(" ".join(argv), os.path.relpath(path, ROOT))
    return found


_COMMANDS = _documented_commands()


def _help(argv: list):
    return CliRunner().invoke(cli_module.cli, [*argv, "--help"])


def _exists(argv: list) -> bool:
    return _help(argv).exit_code == 0


def _is_leaf(argv: list) -> bool:
    """A command that runs, rather than a group listing subcommands."""
    result = _help(argv)
    return result.exit_code == 0 and "Commands" not in result.output


def test_the_scan_finds_the_generator_instructions():
    assert {"migrate", "user assign-role", "make auth"} <= set(_COMMANDS)


@pytest.mark.parametrize("command", sorted(c for c in _COMMANDS if c not in _REFUSED))
def test_each_documented_command_exists(command):
    argv = command.split()
    # `dev.py route list` is a command plus a word of prose as often as a
    # subcommand; accept the shorter form when it is a leaf command.
    assert _exists(argv) or (len(argv) == 2 and _is_leaf(argv[:1])), (
        f"`python dev.py {command}` is documented in {_COMMANDS[command]} but does not exist"
    )


def test_no_printed_link_is_hardcoded_to_the_development_port():
    with open(cli_module.__file__, encoding="utf-8") as handle:
        assert "127.0.0.1:9000" not in handle.read()
