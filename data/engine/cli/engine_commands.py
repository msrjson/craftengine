"""`engine` commands: pin the project to a release, then update, upgrade and hotfix it.

Thin console layer over `engine.lifecycle.EngineLifecycle` (ADR 0005). Output is
engineer-facing: refusal codes, refs and paths, never translated copy.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from engine.lifecycle import EngineLifecycle, EngineLifecycleError, MoveReport, Source, StatusReport

engine_app = typer.Typer(name="engine", help="Engine release pin, update, upgrade and hotfix (ADR 0005).",
                         no_args_is_help=True)


def _lifecycle() -> EngineLifecycle:
    """Return the lifecycle of the project in the working directory."""
    import engine
    from engine.cli.app import base_path

    return EngineLifecycle(Path(base_path()), (engine.__version__, engine.__release__))


def _run(action: Callable[[], Any]) -> Any:
    """Run a lifecycle action; print the refusal code and exit 1 when refused."""
    from engine.cli.app import echo

    try:
        return action()
    except EngineLifecycleError as refused:
        echo(f"Refused: {refused}", "red")
        raise typer.Exit(code=1) from None


def _record(code: str, **fields: object) -> str:
    """Return a machine-readable result line: the code, then `key=value` pairs."""
    return " ".join([code, *(f"{key}={value}" for key, value in fields.items())])


def _render_status(report: StatusReport) -> None:
    """Print a status report."""
    from engine.cli.app import echo

    lock = report.lock
    echo(f"pinned     {lock.ref} ({lock.mode})")
    echo(f"running    v{report.running[0]}-{report.running[1]}", None if lock.version == report.running[0] else "yellow")
    echo(f"verify     {lock.verify_command or '-'}")
    echo(f"patches    {len(lock.patches)}")
    for patch in lock.patches:
        echo(f"  {patch.id:<20} {patch.patch_class:<14} files={len(patch.files):<4} {patch.reason}")
    if report.drift is not None:
        echo(f"drift      unregistered={len(report.drift.paths())}", "red" if report.drift else "green")
        for path in report.drift.paths():
            echo(f"  {path}", "red")
    if report.remote_error:
        echo(f"remote     {report.remote_error}", "yellow")
    echo(f"update     {report.update.ref if report.update else '-'}")
    echo(f"newest     {report.newest.ref if report.newest else '-'}")


def _render_move(report: MoveReport) -> None:
    """Print what a move did, or would do on a dry run."""
    from engine.cli.app import echo

    state = "Moved" if report.applied else "Dry run"
    echo(f"{state}: {report.current.ref} -> {report.target.ref}", "green" if report.applied else "cyan", bold=True)
    for patch in report.plan.carried:
        echo(f"  carried  {patch.id}")
    for patch_id in report.plan.retired:
        echo(f"  retired  {patch_id}")
    for section in report.notes:
        echo(section.heading, bold=True)
        for entry in section.attention:
            echo(f"  {entry}", "yellow")
    if report.applied:
        echo("Next: rebuild or reinstall the engine where it is packaged, then run `migrate`.", "cyan")


@engine_app.command("adopt")
def engine_adopt(
    ref: str = typer.Argument(..., help="Release tag, e.g. v4.4.2-r00024."),
    mode: str = typer.Option("package", help="package (installed from a pinned archive) or vendored."),
    engine_path: str = typer.Option("engine", help="Project-relative vendored engine directory."),
    pin: Annotated[list[str] | None, typer.Option(help="Project file that spells the ref (package mode). Repeatable.")] = None,
    archive_url: str = typer.Option(Source.archive_url, help="Archive URL template with {ref}."),
    tags_url: str = typer.Option(Source.tags_url, help="JSON tag listing URL."),
    subdirectory: str = typer.Option(Source.subdirectory, help="Archive directory holding engine/."),
    verify_command: str = typer.Option("", help="Command every move runs after the swap (the panel's too)."),
    force: bool = typer.Option(False, "--force", help="Replace an existing lock."),
) -> None:
    """Pin this project to an engine release and write craft-engine.lock."""
    from engine.cli.app import echo

    source = Source(archive_url, tags_url, subdirectory)
    lifecycle = _lifecycle()
    lock = _run(lambda: lifecycle.adopt(ref, mode, engine_path=engine_path, pin_files=pin or [], source=source,
                                        force=force))
    if verify_command:
        lock = lifecycle.set_verify_command(verify_command)
    echo(_record("ENGINE_PINNED", ref=lock.ref, mode=lock.mode, files=len(lock.manifest)), "green")


@engine_app.command("status")
def engine_status(offline: bool = typer.Option(False, "--offline", help="Do not ask the source for releases.")) -> None:
    """Show the pin, local patches, unregistered drift and newer releases."""
    report = _run(lambda: _lifecycle().status(check_remote=not offline))
    _render_status(report)
    if report.drift:
        raise typer.Exit(code=1)


@engine_app.command("check")
def engine_check() -> None:
    """Ask the source for newer releases and refresh the notice the panel shows."""
    from engine.cli.app import echo, get_app

    notice = get_app().make("engine_updates").check()
    color = "red" if notice.error else "yellow" if notice.available else "green"
    echo(_record("ENGINE_CHECKED", pinned=notice.pinned or "-", update=notice.update or "-",
                 newest=notice.newest or "-", error=notice.error or "-"), color)
    if notice.error:
        raise typer.Exit(code=1)


@engine_app.command("verify-command")
def engine_verify_command(
    command: Annotated[str, typer.Argument(help="Command line; an empty string clears it.")],
) -> None:
    """Set the command every move runs after the swap, from the console and from the panel."""
    from engine.cli.app import echo

    lock = _run(lambda: _lifecycle().set_verify_command(command))
    echo(_record("ENGINE_VERIFY_COMMAND_SET", verify_command=lock.verify_command or "-"), "green")


@engine_app.command("patch")
def engine_patch(
    paths: Annotated[list[str], typer.Argument(help="Engine-relative paths of the local change.")],
    patch_id: str = typer.Option(..., "--id", help="Unique patch id (ticket or advisory)."),
    patch_class: str = typer.Option(..., "--class", help="security, improvement or upstream-sync."),
    reason: str = typer.Option(..., help="Why the change exists."),
    by: str = typer.Option(..., help="Who registers it."),
) -> None:
    """Register local edits of the vendored engine as a patch."""
    from engine.cli.app import echo

    patch = _run(lambda: _lifecycle().record_patch(paths, patch_id, patch_class, reason, by))
    echo(_record("ENGINE_PATCH_RECORDED", id=patch.id, patch_class=patch.patch_class, files=len(patch.files)), "green")


@engine_app.command("hotfix")
def engine_hotfix(
    ref: Annotated[str, typer.Argument(help="Canonical tag or commit holding the fix.")],
    paths: Annotated[list[str], typer.Argument(help="Engine-relative paths to take from it.")],
    patch_id: str = typer.Option(..., "--id", help="Unique patch id (an advisory id is a good one)."),
    reason: str = typer.Option(..., help="Why the fix is needed now."),
    by: str = typer.Option(..., help="Who applies it."),
    patch_class: str = typer.Option("security", "--class", help="security, improvement or upstream-sync."),
) -> None:
    """Take files from a canonical ref into the vendored engine without moving the pin."""
    from engine.cli.app import echo

    patch = _run(lambda: _lifecycle().hotfix(ref, paths, patch_id, reason, by, patch_class))
    echo(_record("ENGINE_HOTFIX_APPLIED", id=patch.id, source_ref=ref, files=len(patch.files)), "green")


@engine_app.command("update")
def engine_update(
    verify: Annotated[str | None, typer.Option(help="Command that must pass after the swap; defaults to the lock's.")] = None,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the plan and notes; change nothing."),
    drop_patch: Annotated[list[str] | None, typer.Option(help="Patch id to discard in favor of upstream. Repeatable.")] = None,
) -> None:
    """Move to the newest release of the same major.minor line."""
    _render_move(_run(lambda: _lifecycle().update(verify=verify, dry_run=dry_run, dropped=drop_patch or [])))


@engine_app.command("upgrade")
def engine_upgrade(
    to: str = typer.Option(..., "--to", help="Target version, e.g. 4.5.0."),
    verify: Annotated[str | None, typer.Option(help="Command that must pass after the swap; defaults to the lock's.")] = None,
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the plan and notes; change nothing."),
    drop_patch: Annotated[list[str] | None, typer.Option(help="Patch id to discard in favor of upstream. Repeatable.")] = None,
) -> None:
    """Move to a newer minor or major release, showing the changelog it crosses."""
    _render_move(_run(lambda: _lifecycle().upgrade(to, verify=verify, dry_run=dry_run, dropped=drop_patch or [])))


__all__ = ["engine_app"]
