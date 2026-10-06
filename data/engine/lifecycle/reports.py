"""Results of lifecycle operations, as plain records the console renders.

The reports carry codes, refs and paths only; rendering them is the console's job.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from dataclasses import dataclass, field

from engine.lifecycle.changelog import Section
from engine.lifecycle.lock import EngineLock
from engine.lifecycle.manifest import Drift
from engine.lifecycle.planner import MovePlan
from engine.lifecycle.release import Release


@dataclass
class StatusReport:
    """What `status` found.

    Args:
        lock: The project's lock.
        running: `(version, release)` of the engine executing this code.
        drift: Unregistered drift of a vendored engine; None in package mode.
        update: Newest release on the same minor line, when newer.
        newest: Newest release overall, when newer.
        remote_error: Refusal code when the source could not be read.
    """

    lock: EngineLock
    running: tuple[str, str]
    drift: Drift | None = None
    update: Release | None = None
    newest: Release | None = None
    remote_error: str = ""


@dataclass
class MoveReport:
    """What an update or upgrade did, or would do on a dry run.

    Args:
        current: The release the project was pinned to.
        target: The release it moves to.
        plan: The patch outcome (always empty in package mode).
        notes: Changelog sections crossed by the move.
        applied: False on a dry run.
    """

    current: Release
    target: Release
    plan: MovePlan = field(default_factory=MovePlan)
    notes: list[Section] = field(default_factory=list)
    applied: bool = False


__all__ = ["MoveReport", "StatusReport"]
