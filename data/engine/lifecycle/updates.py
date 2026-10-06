"""Update notices and moves for the panel and the console: one service, both surfaces.

`check()` asks the source for newer releases and caches the answer as an
`UpdateNotice`; `notice()` only reads that cache, so a page that shows the
notice never waits on the network. `review()` is a dry run that lists the
patches and the changelog a move crosses; `apply()` performs it with the
verification command recorded in the lock - never one supplied by a request.

Only one move runs at a time per project: a marker file next to the lock is
created exclusively and removed when the move ends.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Any

from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.lock import lock_path, utc_now
from engine.lifecycle.release import parse_ref
from engine.lifecycle.reports import MoveReport
from engine.lifecycle.service import EngineLifecycle

_LOG = logging.getLogger("craft")

#: Cache key of the last update notice.
NOTICE_CACHE_KEY = "engine.lifecycle.notice"

#: Seconds a notice stays cached; a scheduled `engine check` refreshes it sooner.
NOTICE_TTL_SECONDS = 6 * 60 * 60

#: Target name for "the newest release on the current minor line".
UPDATE_TARGET = "update"


@dataclass
class UpdateNotice:
    """What the last check found, as plain values a template can read.

    Args:
        pinned: The release tag the project is pinned to ("" without a lock).
        running: The engine release executing the check.
        update: Newest release on the same minor line, when newer.
        newest: Newest release overall, when newer.
        checked_at: ISO 8601 UTC time of the check.
        error: Refusal code when the check could not complete.
    """

    pinned: str = ""
    running: str = ""
    update: str = ""
    newest: str = ""
    checked_at: str = ""
    error: str = ""

    @property
    def available(self) -> bool:
        """Return whether any newer release exists."""
        return bool(self.update or self.newest)


class EngineUpdates:
    """The update notice and the guarded move, shared by the panel and the console.

    Args:
        lifecycle: The project's lifecycle.
        cache: Any object with `get(key)`, `put(key, value, ttl)` and `forget(key)`.
    """

    def __init__(self, lifecycle: EngineLifecycle, cache: Any) -> None:
        self.lifecycle = lifecycle
        self.cache = cache

    def check(self) -> UpdateNotice:
        """Ask the source for newer releases and cache the result.

        Returns:
            The fresh notice; a missing lock or an unreachable source is
            recorded in `error`, never raised.
        """
        running = "v{0}-{1}".format(*self.lifecycle.running)
        try:
            report = self.lifecycle.status(check_remote=True)
        except EngineLifecycleError as refused:
            notice = UpdateNotice(running=running, checked_at=utc_now(), error=refused.code)
        else:
            notice = UpdateNotice(report.lock.ref, running, report.update.ref if report.update else "",
                                  report.newest.ref if report.newest else "", utc_now(), report.remote_error)
        self.cache.put(NOTICE_CACHE_KEY, asdict(notice), NOTICE_TTL_SECONDS)
        return notice

    def notice(self) -> UpdateNotice | None:
        """Return the cached notice without touching the network, or None when none is cached."""
        cached = self.cache.get(NOTICE_CACHE_KEY)
        return UpdateNotice(**cached) if isinstance(cached, dict) else None

    def overview(self) -> dict[str, Any]:
        """Return the pin, patches, drift and verification command for a screen, without the network.

        Returns:
            Plain values; `error` holds a refusal code (no lock, unreadable lock) or "".
        """
        try:
            report = self.lifecycle.status(check_remote=False)
        except EngineLifecycleError as refused:
            return {"error": refused.code}
        lock = report.lock
        return {
            "error": "",
            "pinned": lock.ref,
            "mode": lock.mode,
            "running": "v{0}-{1}".format(*report.running),
            "verify_command": lock.verify_command,
            "patches": [asdict(patch) for patch in lock.patches],
            "drift": report.drift.paths() if report.drift is not None else [],
        }

    def review(self, target: str) -> MoveReport:
        """Return what moving to `target` would do, changing nothing.

        Args:
            target: `update`, a version such as `4.5.0`, or a release tag.
        """
        return self._mover(target)(dry_run=True)

    def apply(self, target: str, actor: str) -> MoveReport:
        """Move to `target` with the lock's verification command, one move at a time.

        Args:
            target: `update`, or a version such as `4.5.0`.
            actor: Who asked for the move, for the log.

        Returns:
            The applied move.

        Raises:
            EngineLifecycleError: `ENGINE_MOVE_IN_PROGRESS` while another move
                runs, or any refusal of the move itself.
        """
        with self._exclusive():
            report = self._mover(target)(dry_run=False)
        self.cache.forget(NOTICE_CACHE_KEY)
        _LOG.info("engine_lifecycle_moved", extra={"actor": actor, "from_ref": report.current.ref,
                                                   "to_ref": report.target.ref})
        return report

    def _mover(self, target: str) -> Callable[..., MoveReport]:
        """Return the lifecycle call that moves to `target`, verification from the lock."""
        if target == UPDATE_TARGET:
            return lambda dry_run: self.lifecycle.update(dry_run=dry_run)
        release = parse_ref(target)
        version = release.version_text if release is not None else target
        return lambda dry_run: self.lifecycle.upgrade(version, dry_run=dry_run)

    @contextmanager
    def _exclusive(self) -> Iterator[None]:
        """Hold the project's move marker for the duration of the block."""
        marker = lock_path(self.lifecycle.root).with_suffix(".busy")
        try:
            handle = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise EngineLifecycleError("ENGINE_MOVE_IN_PROGRESS", str(marker)) from None
        os.close(handle)
        try:
            yield
        finally:
            marker.unlink(missing_ok=True)


__all__ = ["NOTICE_CACHE_KEY", "UPDATE_TARGET", "EngineUpdates", "UpdateNotice"]
