#!/usr/bin/env python
"""`dev` - the Craft Framework console entrypoint.

Usage:
    python dev.py migrate
    python dev.py migrate:status
    python dev.py make model Product -m
    python dev.py db seed
    python dev.py serve --port 9000
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine  # noqa: F401,E402  installs the `craft.*` import alias

from craft.cli.app import cli  # noqa: E402

#: Commands that are a single name containing a colon, not `group:subcommand`.
_ATOMIC_COMMANDS = {"key:generate"}


def main() -> None:
    # Accept `migrate:status` as well as `migrate status` - but only the
    # leading command token is eligible. Splitting any colon-containing arg
    # also mangled option values like `--fields "name:string:required"`.
    argv = list(sys.argv[1:])
    if argv:
        head = argv[0]
        if ":" in head and not head.startswith("-") and head not in _ATOMIC_COMMANDS:
            argv[0:1] = head.split(":", 1)
    cli(args=argv, prog_name="dev")


if __name__ == "__main__":
    main()
