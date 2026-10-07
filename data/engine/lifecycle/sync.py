"""Release synchronization: what keeps a node standing on its own after a deploy.

A migration creates a column; it does not create the *rows* the system needs to
work. Those are born in a seeder, and a seeder that only runs when somebody
remembers leaves the screen empty after a deploy on an environment nobody opens
a terminal on. `release:sync` therefore does the two things together, in order,
once per deploy:

1. **Migrate** - apply every pending migration.
2. **Seed** - run the idempotent seeders that ADD what is missing and never
   touch what already exists, so running again is safe by construction.

Then it records one `release_syncs` row with the version and what ran.

Nothing here deletes: a seed that deletes to recreate is the shortest path to
destroying operational rows (NR-02). The `VERSION` file carries the release
identity the deployed code must match; a mismatch is a stale image or a
half-finished release, refused before it serves a request.

Category: Core Framework (Release).
Relations:
  - Called by the `release:sync` and `release:status` commands
    (`engine/cli/app.py`); no container binding of its own.
  - Takes the migrator's session-scoped advisory lock
    (`Migrator.with_lock`, `craft:migrations`) so two deploys cannot migrate the
    same node at once, and runs unlocked on a driver without advisory locks.
References:
  - Guide: `documentation/release.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import os
import time
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from engine.lifecycle.errors import EngineLifecycleError

#: The file carrying the release identity the deployed code must match.
VERSION_FILE = "VERSION"

#: The seeders a release runs: only those defining what the node NEEDS to exist.
#: Example seeders (fictitious records) stay out of a release - in production
#: they would be garbage that looks like records.
DEFAULT_SEEDERS: Tuple[str, ...] = ("DatabaseSeeder",)


class ReleaseSync:
    """Migrate and seed the node, then record the release. Safe to run every boot."""

    def __init__(self, app: Any = None, seeders: Optional[Tuple[str, ...]] = None):
        self.app = app
        self.seeders = DEFAULT_SEEDERS if seeders is None else tuple(seeders)

    # -- application and paths ------------------------------------------------

    def _app(self) -> Any:
        if self.app is not None:
            return self.app
        from engine.container.application import Container

        return Container.getInstance()

    def version_path(self) -> str:
        """The absolute path of the `VERSION` file at the application root."""
        return os.path.join(str(self._app().base_path), VERSION_FILE)

    # -- identity -------------------------------------------------------------

    @staticmethod
    def code_identity() -> str:
        """The identity the running code carries, `MAJOR.MINOR.PATCH-rNNNNN`."""
        import engine

        return f"{engine.__version__}-{engine.__release__}"

    def read_version_file(self) -> Optional[str]:
        """The `VERSION` file's content, or None when it is absent or empty."""
        try:
            with open(self.version_path(), encoding="utf-8") as handle:
                text = handle.read().strip()
        except FileNotFoundError:
            return None
        return text or None

    def verify_identity(self) -> str:
        """Return the code identity, refusing any drift from the `VERSION` file.

        Refusing here is cheaper than serving requests from code nobody can
        name: a `VERSION` that disagrees with the running code is a stale image
        or a half-finished release.
        """
        identity = self.code_identity()
        declared = self.read_version_file()
        if declared is None:
            raise EngineLifecycleError("RELEASE_VERSION_FILE_MISSING", VERSION_FILE)
        if declared != identity:
            raise EngineLifecycleError(
                "RELEASE_VERSION_DRIFT", f"{VERSION_FILE}={declared} code={identity}"
            )
        return identity

    # -- sync -----------------------------------------------------------------

    def sync(self) -> Dict[str, Any]:
        """Migrate, seed and record one release sync. Returns the recorded row."""
        identity = self.verify_identity()
        started = time.monotonic()
        counts: Dict[str, int] = {"migrations": 0, "seeders": 0}
        findings: List[str] = []

        def work() -> None:
            from engine.migrations.migrator import Migrator
            from engine.seeding import run_seeder

            counts["migrations"] = len(Migrator(self._app()).run())
            for name in self.seeders:
                seeder = run_seeder(name, self._app())
                counts["seeders"] += 1
                findings.extend(getattr(seeder, "command_output", []))

        # The migrator's lock covers the whole sync, not just the migrations: a
        # seeder racing another deploy's migration is the same half-built state.
        from engine.migrations.migrator import Migrator

        Migrator(self._app()).with_lock(work)

        duration_ms = int((time.monotonic() - started) * 1000)
        return self._record(identity, counts["migrations"], counts["seeders"], findings, duration_ms)

    def _record(
        self,
        identity: str,
        migrations_run: int,
        seeders_run: int,
        findings: List[str],
        duration_ms: int,
        status: str = "ok",
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        db = self._app().make("db")
        db.statement(
            "INSERT INTO release_syncs "
            "(uuid, version, migrations_run, seeders_run, status, findings, duration_ms, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                str(_uuid.uuid4()),
                identity,
                migrations_run,
                seeders_run,
                status,
                json.dumps(findings),
                duration_ms,
                now,
                now,
            ],
        )
        return {
            "version": identity,
            "migrations_run": migrations_run,
            "seeders_run": seeders_run,
            "status": status,
            "findings": findings,
            "duration_ms": duration_ms,
        }

    # -- status ---------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """The code identity, the `VERSION` file and the last recorded sync."""
        from engine.migrations.schema import Schema

        last: Optional[Dict[str, Any]] = None
        if Schema.has_table("release_syncs"):
            row = self._app().make("db").statement(
                "SELECT version, migrations_run, seeders_run, status, duration_ms, created_at "
                "FROM release_syncs ORDER BY id DESC LIMIT 1",
                read=True,
            ).fetchone()
            if row is not None:
                last = dict(row)
        return {
            "code": self.code_identity(),
            "version_file": self.read_version_file(),
            "last_sync": last,
        }


__all__ = ["DEFAULT_SEEDERS", "VERSION_FILE", "ReleaseSync"]
