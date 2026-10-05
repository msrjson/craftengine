"""`extension` commands: discover, install, activate, deactivate and inspect extensions.

The same operations the extension manager panel offers, for terminals and
agents, and the way back in when the panel itself is the extension that broke.
Output is engineer-facing: codes and slugs, never translated copy.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer

from engine.extensions.errors import ExtensionError

extension_app = typer.Typer(name="extension", help="Modules, plugins and themes (ADR 0004).", no_args_is_help=True)


def _manager() -> Any:
    """Return the booted application's extension manager."""
    from engine.cli.app import get_app

    return get_app().make("extensions")


def _run(action: Callable[[], Any], done: str) -> None:
    """Run a lifecycle action; print the refusal code and exit 1 when refused."""
    from engine.cli.app import echo

    try:
        action()
    except ExtensionError as refused:
        echo(f"Refused: {refused}", "red")
        raise typer.Exit(code=1) from None
    echo(done, "green")


@extension_app.command("list")
def extension_list() -> None:
    """List every discovered extension with its kind, version, state and health."""
    from engine.cli.app import echo

    manager = _manager()
    echo(f"{'SLUG':<24} {'KIND':<8} {'VERSION':<10} {'STATE':<12} {'HEALTH':<12} REQUIRES")
    echo("-" * 96)
    for row in manager.status():
        requires = ", ".join(f"{name} {spec}" for name, spec in row["requires"].items()) or "-"
        echo(f"{row['slug']:<24} {row['kind']:<8} {row['version']:<10} {row['state']:<12} {row['availability']:<12} {requires}")
    for path, refused in manager.discovery_errors.items():
        echo(f"Refused manifest {path}: {refused.code} {refused.detail}", "yellow")


@extension_app.command("status")
def extension_status(slug: str) -> None:
    """Show one extension's state, availability, circuit breaker and last error."""
    from engine.cli.app import echo

    rows = {row["slug"]: row for row in _manager().status()}
    if slug not in rows:
        echo(f"Refused: EXTENSION_NOT_FOUND {slug}", "red")
        raise typer.Exit(code=1)
    for key, value in rows[slug].items():
        echo(f"{key:<14} {value}")


@extension_app.command("install")
def extension_install(slug: str) -> None:
    """Run the extension's migrations, seed its translations and mark it installed."""
    _run(lambda: _manager().install(slug), f"Installed: {slug}")


@extension_app.command("activate")
def extension_activate(slug: str) -> None:
    """Load the extension and mark it active (every worker follows within seconds)."""
    _run(lambda: _manager().activate(slug), f"Activated: {slug}")


@extension_app.command("deactivate")
def extension_deactivate(slug: str) -> None:
    """Undo the extension's contributions and mark it inactive; its data stays."""
    _run(lambda: _manager().deactivate(slug), f"Deactivated: {slug}")


@extension_app.command("uninstall")
def extension_uninstall(slug: str) -> None:
    """Mark the extension uninstalled; tables, rows and translations stay (NR-02)."""
    _run(lambda: _manager().uninstall(slug), f"Uninstalled: {slug} (its data was kept)")


def register_make_commands(make_app: typer.Typer) -> None:
    """Add `make:module`, `make:plugin`, `make:theme` and `make:screen` to `make`."""
    from engine.extensions.manifest import ExtensionKind

    def scaffold(kind: ExtensionKind) -> Callable[..., None]:
        def command(slug: str, force: bool = typer.Option(False, "--force")) -> None:
            from engine.cli.app import base_path, echo
            from engine.cli.extension_scaffolder import build_extension

            _run(lambda: [echo(f"  {path}") for path in build_extension(base_path(), kind, slug, force=force)],
                 f"Created {kind.value} {slug}. Next: dev.py extension install {slug} && dev.py extension activate {slug}")

        command.__doc__ = f"Generate a self-contained {kind.value} extension under its configured root."
        return command

    for kind in ExtensionKind:
        make_app.command(kind.value)(scaffold(kind))

    @make_app.command("screen")
    def make_screen(slug: str, screen: str) -> None:
        """Add a screen to a module: controller, namespaced view, route and title key."""
        from engine.cli.app import base_path, echo
        from engine.cli.extension_scaffolder import build_screen

        _run(lambda: [echo(f"  {path}") for path in build_screen(base_path(), slug, screen)],
             f"Screen {screen} added to {slug}. Run dev.py extension install again only for new migrations.")


__all__ = ["extension_app", "register_make_commands"]
