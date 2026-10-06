"""`craft-engine.lock`: which engine a project runs and what it changed locally.

The lock is the single record the lifecycle commands read and write. It names
the canonical source, the release the project is pinned to, how the engine
reaches the project (`package`: installed from a pinned archive; `vendored`:
an `engine/` directory committed with the project), the file manifest of that
release, and every local patch with its class and reason.

A vendored file that differs from the manifest and is not covered by a patch is
unregistered drift: the lifecycle refuses to move a project that has any.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.lifecycle.errors import EngineLifecycleError

#: File name of the lock, at the project root.
LOCK_FILE = "craft-engine.lock"

#: Lock layout version. Bumped only with a reader for the previous one.
LOCK_SCHEMA = 1

#: Archive of any tag or commit of the canonical repository. Never the
#: development workspace (owner ruling 2026-09-22).
CANONICAL_ARCHIVE_URL = "https://github.com/msrjson/craftengine/archive/{ref}.tar.gz"

#: Tag listing of the canonical repository.
CANONICAL_TAGS_URL = "https://api.github.com/repos/msrjson/craftengine/tags?per_page=100"

#: Directory of the canonical repository that holds `engine/` and `CHANGELOG.md`.
CANONICAL_SUBDIRECTORY = "data"

#: How the engine reaches the project.
MODES = ("package", "vendored")

#: Why a local patch exists. The same classes SoftPax's engine lock uses.
PATCH_CLASSES = ("security", "improvement", "upstream-sync")


@dataclass
class Source:
    """Where releases come from.

    Args:
        archive_url: Archive URL template with a `{ref}` placeholder.
        tags_url: URL of a JSON list of `{"name": <tag>}` objects.
        subdirectory: Directory inside the archive that holds `engine/`.
    """

    archive_url: str = CANONICAL_ARCHIVE_URL
    tags_url: str = CANONICAL_TAGS_URL
    subdirectory: str = CANONICAL_SUBDIRECTORY


@dataclass
class Patch:
    """A registered local change to vendored engine files.

    Args:
        id: Stable identifier chosen by the project (a ticket or advisory id).
        patch_class: One of `PATCH_CLASSES`.
        reason: Why the change exists.
        recorded_by: Who registered it.
        recorded_at: ISO 8601 UTC timestamp.
        files: Engine-relative path to the SHA-256 of the patched content, or
            None when the patch deletes the file.
        source_ref: The canonical ref a hotfix took its files from; empty for
            a change made in the project.
    """

    id: str
    patch_class: str
    reason: str
    recorded_by: str
    recorded_at: str
    files: dict[str, str | None] = field(default_factory=dict)
    source_ref: str = ""


@dataclass
class EngineLock:
    """The full lock record.

    Args:
        mode: `package` or `vendored`.
        ref: The release tag the project is pinned to.
        version: The release's `MAJOR.MINOR.PATCH`.
        release: The release's `rNNNNN` counter.
        engine_path: Project-relative directory of a vendored engine.
        source: Where releases come from.
        manifest: Engine-relative path to SHA-256 of the pinned release (vendored only).
        patches: Registered local changes (vendored only).
        pin_files: Project files that spell the pinned ref (package only).
    """

    mode: str
    ref: str
    version: str
    release: str
    engine_path: str = "engine"
    source: Source = field(default_factory=Source)
    manifest: dict[str, str] = field(default_factory=dict)
    patches: list[Patch] = field(default_factory=list)
    pin_files: list[str] = field(default_factory=list)

    def patched_files(self) -> dict[str, str | None]:
        """Return every patched path with the hash its patch recorded."""
        return {path: digest for patch in self.patches for path, digest in patch.files.items()}


def utc_now() -> str:
    """Return the current time as ISO 8601 UTC with a `Z` suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def lock_path(root: Path) -> Path:
    """Return where the lock lives for the project at `root`."""
    return root / LOCK_FILE


def to_dict(lock: EngineLock) -> dict[str, Any]:
    """Return the lock as a JSON-ready mapping, schema version first."""
    return {"schema": LOCK_SCHEMA, **asdict(lock)}


def from_dict(payload: dict[str, Any]) -> EngineLock:
    """Build a lock from its decoded JSON mapping.

    Args:
        payload: The decoded lock file.

    Returns:
        The lock.

    Raises:
        EngineLifecycleError: `ENGINE_LOCK_INVALID` on an unknown schema, mode
            or patch class, or a missing field.
    """
    if payload.get("schema") != LOCK_SCHEMA or payload.get("mode") not in MODES:
        raise EngineLifecycleError("ENGINE_LOCK_INVALID", f"schema={payload.get('schema')} mode={payload.get('mode')}")
    fields = {key: value for key, value in payload.items() if key != "schema"}
    try:
        lock = EngineLock(**{**fields, "source": Source(**fields.get("source", {}))})
        lock.patches = [Patch(**patch) for patch in fields.get("patches", [])]
    except TypeError as malformed:
        raise EngineLifecycleError("ENGINE_LOCK_INVALID", str(malformed)) from None
    unknown = sorted({patch.patch_class for patch in lock.patches} - set(PATCH_CLASSES))
    if unknown:
        raise EngineLifecycleError("ENGINE_LOCK_INVALID", f"patch_class={','.join(unknown)}")
    return lock


def load_lock(root: Path) -> EngineLock:
    """Read the lock of the project at `root`.

    Args:
        root: The project root.

    Returns:
        The lock.

    Raises:
        EngineLifecycleError: `ENGINE_LOCK_MISSING` when there is none,
            `ENGINE_LOCK_INVALID` when it cannot be read.
    """
    path = lock_path(root)
    if not path.is_file():
        raise EngineLifecycleError("ENGINE_LOCK_MISSING", str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as unreadable:
        raise EngineLifecycleError("ENGINE_LOCK_INVALID", str(unreadable)) from None
    return from_dict(payload)


def save_lock(root: Path, lock: EngineLock) -> Path:
    """Write the lock atomically: a reader sees the old file or the new one, never half.

    Args:
        root: The project root.
        lock: The lock to write.

    Returns:
        The lock's path.
    """
    path = lock_path(root)
    staging = path.with_name(path.name + ".tmp")
    staging.write_text(json.dumps(to_dict(lock), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(staging, path)
    return path


__all__ = [
    "CANONICAL_ARCHIVE_URL",
    "CANONICAL_SUBDIRECTORY",
    "CANONICAL_TAGS_URL",
    "LOCK_FILE",
    "MODES",
    "PATCH_CLASSES",
    "EngineLock",
    "Patch",
    "Source",
    "from_dict",
    "load_lock",
    "lock_path",
    "save_lock",
    "to_dict",
    "utc_now",
]
