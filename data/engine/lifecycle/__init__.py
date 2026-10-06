"""Engine lifecycle: pin a project to a release, then update, upgrade and hotfix it.

See `documentation/engine-lifecycle.md` and ADR 0005. The console entry points
are the `engine` commands; `EngineLifecycle` is the API they call.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.lock import LOCK_FILE, EngineLock, Patch, Source
from engine.lifecycle.reports import MoveReport, StatusReport
from engine.lifecycle.service import EngineLifecycle

__all__ = [
    "LOCK_FILE",
    "EngineLifecycle",
    "EngineLifecycleError",
    "EngineLock",
    "MoveReport",
    "Patch",
    "Source",
    "StatusReport",
]
