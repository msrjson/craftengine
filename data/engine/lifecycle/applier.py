"""Applying a move to disk, transactionally.

Vendored: the target engine is staged beside the current one with the carried
patches on top, then swapped in by two renames on the same filesystem. If the
verification command fails, the previous engine is renamed back. The project
never runs a half-copied engine.

Package: the pinned ref is rewritten in the project's pin files; on failure
every file gets its previous content back.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.lock import Patch

#: Generated files never copied from a release.
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def sibling(engine_dir: Path, role: str) -> Path:
    """Return the scratch directory next to `engine_dir` used for `role` (`incoming`, `previous`)."""
    return engine_dir.with_name(f".{engine_dir.name}.{role}")


def _clear(path: Path) -> None:
    """Remove a scratch directory the lifecycle itself created on an earlier run."""
    if path.exists():
        shutil.rmtree(path)


def copy_engine_files(source_engine: Path, target_engine: Path, paths: list[str]) -> None:
    """Copy engine-relative `paths` from one engine tree onto another.

    Args:
        source_engine: The engine that holds the content.
        target_engine: The engine to write into.
        paths: Engine-relative POSIX paths.
    """
    for path in paths:
        target = target_engine / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_engine / path, target)


def apply_patch_files(source_engine: Path, staging: Path, patch: Patch) -> None:
    """Carry one patch from the current engine onto the staged one, deletions included.

    Args:
        source_engine: The engine that holds the patched content.
        staging: The staged engine to patch.
        patch: The patch to carry.
    """
    copy_engine_files(source_engine, staging, [path for path, digest in patch.files.items() if digest is not None])
    for path in (path for path, digest in patch.files.items() if digest is None):
        (staging / path).unlink(missing_ok=True)


def stage_vendored(release_engine: Path, engine_dir: Path, carried: list[Patch]) -> Path:
    """Build the target engine beside the current one.

    Args:
        release_engine: The extracted target release's `engine/`.
        engine_dir: The project's vendored engine.
        carried: Patches to re-apply on the target.

    Returns:
        The staged directory.
    """
    staging = sibling(engine_dir, "incoming")
    _clear(staging)
    shutil.copytree(release_engine, staging, ignore=COPY_IGNORE)
    for patch in carried:
        apply_patch_files(engine_dir, staging, patch)
    return staging


def swap_in(engine_dir: Path, staging: Path) -> Path:
    """Make the staged engine current and keep the old one aside.

    Args:
        engine_dir: The project's vendored engine.
        staging: The staged target engine.

    Returns:
        Where the previous engine now lives.
    """
    previous = sibling(engine_dir, "previous")
    _clear(previous)
    os.replace(engine_dir, previous)
    os.replace(staging, engine_dir)
    return previous


def swap_back(engine_dir: Path, previous: Path) -> None:
    """Restore the previous engine after a failed verification.

    Args:
        engine_dir: The project's vendored engine (currently the target).
        previous: The engine kept aside by `swap_in`.
    """
    failed = sibling(engine_dir, "failed")
    _clear(failed)
    os.replace(engine_dir, failed)
    os.replace(previous, engine_dir)
    shutil.rmtree(failed)


def run_verify(command: str, cwd: Path) -> int:
    """Run the verification command; an empty command passes.

    Args:
        command: A shell-style command line, run without a shell.
        cwd: The project root.

    Returns:
        The command's exit code.
    """
    if not command.strip():
        return 0
    return subprocess.run(shlex.split(command), cwd=cwd, check=False).returncode


def rewrite_pins(root: Path, pin_files: list[str], old_ref: str, new_ref: str) -> dict[Path, str]:
    """Replace the pinned ref in every pin file.

    Args:
        root: The project root.
        pin_files: Project-relative files that spell the ref.
        old_ref: The ref pinned now.
        new_ref: The ref to pin.

    Returns:
        Each rewritten file with its previous content, for `restore_pins`.

    Raises:
        EngineLifecycleError: `ENGINE_PIN_NOT_FOUND` when a pin file does not
            spell `old_ref`; nothing is written in that case.
    """
    absent = sorted(name for name in pin_files if not (root / name).is_file())
    if absent:
        raise EngineLifecycleError("ENGINE_PIN_NOT_FOUND", ",".join(absent))
    originals = {root / name: (root / name).read_text(encoding="utf-8") for name in pin_files}
    stale = sorted(str(path) for path, text in originals.items() if old_ref not in text)
    if stale:
        raise EngineLifecycleError("ENGINE_PIN_NOT_FOUND", ",".join(stale))
    for path, text in originals.items():
        path.write_text(text.replace(old_ref, new_ref), encoding="utf-8")
    return originals


def restore_pins(originals: dict[Path, str]) -> None:
    """Write back the content `rewrite_pins` replaced."""
    for path, text in originals.items():
        path.write_text(text, encoding="utf-8")


__all__ = [
    "apply_patch_files",
    "copy_engine_files",
    "restore_pins",
    "rewrite_pins",
    "run_verify",
    "sibling",
    "stage_vendored",
    "swap_back",
    "swap_in",
]
