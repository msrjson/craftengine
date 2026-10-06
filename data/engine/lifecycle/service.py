"""The engine lifecycle: adopt a release, inspect drift, patch, hotfix, update, upgrade.

`EngineLifecycle` is the one entry point the console commands call. It reads
and writes `craft-engine.lock` at the project root and never touches anything
outside the project's engine, its pin files and its own scratch directories.
Database schema is not its concern: engine migrations run forward-only through
`migrate` after a move, like any other.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path

from engine.lifecycle import applier
from engine.lifecycle.changelog import crossed_sections
from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.lock import EngineLock, Patch, Source, load_lock, lock_path, save_lock, utc_now
from engine.lifecycle.manifest import Drift, build_manifest, compare, expected_with_patches, hash_file
from engine.lifecycle.planner import check_new_patch, checked_plan
from engine.lifecycle.release import Release, find_version, newest_patch, parse_version, require_ref
from engine.lifecycle.reports import MoveReport, StatusReport
from engine.lifecycle.source import fetch_release, list_releases, newer_releases


class EngineLifecycle:
    """Lifecycle operations for the project at `root`.

    Args:
        root: The project root, where `craft-engine.lock` lives.
        running: `(version, release)` of the engine executing this code.
    """

    def __init__(self, root: Path, running: tuple[str, str]) -> None:
        self.root = root
        self.running = running

    # -- adopt and inspect --------------------------------------------------

    def adopt(self, ref: str, mode: str, *, engine_path: str = "engine", pin_files: Iterable[str] = (),
              source: Source | None = None, force: bool = False) -> EngineLock:
        """Pin the project to `ref` and write the lock.

        Args:
            ref: The release tag the project runs.
            mode: `package` or `vendored`.
            engine_path: Project-relative directory of a vendored engine.
            pin_files: Project files that spell the ref (package mode).
            source: Where releases come from; the canonical repository by default.
            force: Replace an existing lock.

        Returns:
            The written lock.

        Raises:
            EngineLifecycleError: `ENGINE_LOCK_EXISTS`, `ENGINE_REF_INVALID`,
                `ENGINE_MODE_INVALID`, or a source refusal (vendored mode).
        """
        if lock_path(self.root).exists() and not force:
            raise EngineLifecycleError("ENGINE_LOCK_EXISTS", str(lock_path(self.root)))
        if mode not in ("package", "vendored"):
            raise EngineLifecycleError("ENGINE_MODE_INVALID", mode)
        release = require_ref(ref)
        lock = EngineLock(mode, release.ref, release.version_text, release.release_text, engine_path,
                          source or Source(), pin_files=list(pin_files))
        if mode == "vendored":
            lock.manifest = self._release_manifest(lock.source, release.ref)
        save_lock(self.root, lock)
        return lock

    def status(self, *, check_remote: bool = True) -> StatusReport:
        """Report the pin, unregistered drift and newer releases.

        Args:
            check_remote: Ask the source for newer releases.

        Returns:
            The report; an unreachable source is reported, not raised.
        """
        lock = load_lock(self.root)
        report = StatusReport(lock, self.running)
        if lock.mode == "vendored":
            report.drift = self.unregistered_drift(lock)
        if check_remote:
            self._fill_remote(report)
        return report

    def unregistered_drift(self, lock: EngineLock) -> Drift:
        """Return how the vendored engine differs from its release plus its patches."""
        expected = expected_with_patches(lock.manifest, lock.patched_files())
        return compare(expected, build_manifest(self._engine_dir(lock)))

    # -- patches and hotfixes -----------------------------------------------

    def record_patch(self, paths: Iterable[str], patch_id: str, patch_class: str, reason: str,
                     recorded_by: str, source_ref: str = "") -> Patch:
        """Register the current content of vendored engine files as a patch.

        A path already covered by another patch moves to this one; a patch left
        with no path is removed.

        Args:
            paths: Engine-relative paths (an `engine/` prefix is accepted).
            patch_id: A new, unique id.
            patch_class: One of `PATCH_CLASSES`.
            reason: Why the change exists.
            recorded_by: Who registers it.
            source_ref: The canonical ref the content came from, if any.

        Returns:
            The recorded patch.

        Raises:
            EngineLifecycleError: `ENGINE_NOT_VENDORED`, `ENGINE_PATCH_CLASS_INVALID`,
                `ENGINE_PATCH_EXISTS` or `ENGINE_PATCH_EMPTY`.
        """
        lock = self._vendored_lock()
        check_new_patch(lock, patch_id, patch_class)
        files = {path: self._current_hash(lock, path) for path in self._normalize(lock, paths)}
        unchanged = sorted(path for path, digest in files.items() if digest == lock.manifest.get(path))
        if unchanged or not files:
            raise EngineLifecycleError("ENGINE_PATCH_EMPTY", ",".join(unchanged))
        patch = Patch(patch_id, patch_class, reason, recorded_by, utc_now(), files, source_ref)
        save_lock(self.root, replace(lock, patches=[*_without_paths(lock.patches, files), patch]))
        return patch

    def hotfix(self, ref: str, paths: Iterable[str], patch_id: str, reason: str, recorded_by: str,
               patch_class: str = "security") -> Patch:
        """Take files from a canonical ref into the vendored engine, without moving the pin.

        Args:
            ref: A tag or commit of the canonical repository holding the fix.
            paths: Engine-relative paths to take.
            patch_id: A new, unique id (an advisory id is a good one).
            reason: Why the fix is needed now.
            recorded_by: Who applies it.
            patch_class: `security` unless stated otherwise.

        Returns:
            The recorded patch.

        Raises:
            EngineLifecycleError: `ENGINE_NOT_VENDORED`, `ENGINE_DRIFT_UNREGISTERED`
                on a path with local edits, `ENGINE_HOTFIX_PATH_MISSING`,
                `ENGINE_HOTFIX_NO_CHANGE`, or a patch or source refusal.
        """
        lock = self._vendored_lock()
        check_new_patch(lock, patch_id, patch_class)
        wanted = self._normalize(lock, paths)
        clobbered = sorted(set(wanted) & set(self.unregistered_drift(lock).paths()))
        if clobbered:
            raise EngineLifecycleError("ENGINE_DRIFT_UNREGISTERED", ",".join(clobbered))
        with tempfile.TemporaryDirectory() as scratch:
            release_engine = fetch_release(lock.source, ref, Path(scratch)) / "engine"
            self._check_hotfix_files(lock, release_engine, wanted)
            applier.copy_engine_files(release_engine, self._engine_dir(lock), wanted)
        return self.record_patch(wanted, patch_id, patch_class, reason, recorded_by, source_ref=ref)

    # -- moves ----------------------------------------------------------------

    def update(self, *, verify: str | None = None, dry_run: bool = False, dropped: Iterable[str] = ()) -> MoveReport:
        """Move to the newest release of the same `major.minor` line.

        `verify` defaults to the lock's `verify_command`; pass "" to skip it.

        Raises:
            EngineLifecycleError: `ENGINE_ALREADY_LATEST`, or any move refusal.
        """
        lock = load_lock(self.root)
        target = newest_patch(require_ref(lock.ref), list_releases(lock.source))
        if target is None:
            raise EngineLifecycleError("ENGINE_ALREADY_LATEST", lock.ref)
        return self._move(lock, target, verify, dry_run, set(dropped))

    def upgrade(self, to: str, *, verify: str | None = None, dry_run: bool = False,
                dropped: Iterable[str] = ()) -> MoveReport:
        """Move to the release carrying version `to`, across minors and majors.

        `verify` defaults to the lock's `verify_command`; pass "" to skip it.

        Raises:
            EngineLifecycleError: `ENGINE_NOT_NEWER` for the same or an older
                version, `ENGINE_RELEASE_NOT_FOUND`, or any move refusal.
        """
        lock = load_lock(self.root)
        current = require_ref(lock.ref)
        target = find_version(list_releases(lock.source), parse_version(to))
        if target.version <= current.version:
            raise EngineLifecycleError("ENGINE_NOT_NEWER", f"{current.ref}->{target.ref}")
        return self._move(lock, target, verify, dry_run, set(dropped))

    def _move(self, lock: EngineLock, target: Release, verify: str | None, dry_run: bool,
              dropped: set[str]) -> MoveReport:
        """Fetch `target`, plan the patches, then apply unless this is a dry run."""
        verify = lock.verify_command if verify is None else verify
        if lock.mode == "vendored" and (drift := self.unregistered_drift(lock)):
            raise EngineLifecycleError("ENGINE_DRIFT_UNREGISTERED", ",".join(drift.paths()))
        current = require_ref(lock.ref)
        with tempfile.TemporaryDirectory() as scratch:
            tree = fetch_release(lock.source, target.ref, Path(scratch))
            manifest = build_manifest(tree / "engine")
            report = MoveReport(current, target, notes=crossed_sections(tree, current, target))
            if lock.mode == "vendored":
                report.plan = checked_plan(lock, manifest, dropped)
            if not dry_run:
                self._apply(lock, tree / "engine", report, manifest, verify)
                report.applied = True
        return report

    def _apply(self, lock: EngineLock, release_engine: Path, report: MoveReport, manifest: dict[str, str],
               verify: str) -> None:
        """Swap the engine (or the pins), verify, and roll back on failure."""
        target = report.target
        moved = replace(lock, ref=target.ref, version=target.version_text, release=target.release_text)
        if lock.mode == "package":
            originals = applier.rewrite_pins(self.root, lock.pin_files, lock.ref, target.ref)
            self._verify_or(verify, target, lambda: applier.restore_pins(originals))
            save_lock(self.root, moved)
            return
        engine_dir = self._engine_dir(lock)
        previous = applier.swap_in(engine_dir, applier.stage_vendored(release_engine, engine_dir, report.plan.carried))
        self._verify_or(verify, target, lambda: applier.swap_back(engine_dir, previous))
        shutil.rmtree(previous)
        save_lock(self.root, replace(moved, manifest=manifest, patches=report.plan.carried))

    def _verify_or(self, verify: str, target: Release, rollback: Callable[[], None]) -> None:
        """Run the verification command; roll back and refuse when it fails."""
        if applier.run_verify(verify, self.root) != 0:
            rollback()
            raise EngineLifecycleError("ENGINE_VERIFY_FAILED", target.ref)

    def set_verify_command(self, command: str) -> EngineLock:
        """Record the command every move runs after the swap; "" clears it."""
        lock = replace(load_lock(self.root), verify_command=command.strip())
        save_lock(self.root, lock)
        return lock

    # -- helpers --------------------------------------------------------------

    def _engine_dir(self, lock: EngineLock) -> Path:
        """Return the vendored engine directory."""
        return self.root / lock.engine_path

    def _vendored_lock(self) -> EngineLock:
        """Return the lock, refusing a project that does not vendor its engine."""
        lock = load_lock(self.root)
        if lock.mode != "vendored":
            raise EngineLifecycleError("ENGINE_NOT_VENDORED", lock.mode)
        return lock

    def _release_manifest(self, source: Source, ref: str) -> dict[str, str]:
        """Return the engine manifest of the release `ref`."""
        with tempfile.TemporaryDirectory() as scratch:
            return build_manifest(fetch_release(source, ref, Path(scratch)) / "engine")

    def _current_hash(self, lock: EngineLock, path: str) -> str | None:
        """Return the hash of a vendored file, None when it does not exist."""
        file = self._engine_dir(lock) / path
        return hash_file(file) if file.is_file() else None

    def _normalize(self, lock: EngineLock, paths: Iterable[str]) -> list[str]:
        """Return engine-relative POSIX paths, accepting an `engine/` prefix."""
        prefix = lock.engine_path.rstrip("/") + "/"
        return sorted({Path(path).as_posix().removeprefix(prefix) for path in paths})

    def _check_hotfix_files(self, lock: EngineLock, release_engine: Path, paths: list[str]) -> None:
        """Refuse a hotfix path the ref lacks or whose content equals the pinned release."""
        missing = sorted(path for path in paths if not (release_engine / path).is_file())
        if missing:
            raise EngineLifecycleError("ENGINE_HOTFIX_PATH_MISSING", ",".join(missing))
        same = sorted(path for path in paths if hash_file(release_engine / path) == lock.manifest.get(path))
        if same:
            raise EngineLifecycleError("ENGINE_HOTFIX_NO_CHANGE", ",".join(same))

    def _fill_remote(self, report: StatusReport) -> None:
        """Add newer releases to the report, or the reason the source was unreadable."""
        try:
            report.update, report.newest = newer_releases(report.lock.source, require_ref(report.lock.ref))
        except EngineLifecycleError as unreachable:
            report.remote_error = unreachable.code

def _without_paths(patches: list[Patch], paths: dict[str, str | None]) -> list[Patch]:
    """Return the patches with `paths` removed, dropping any patch left empty."""
    trimmed = [replace(patch, files={p: d for p, d in patch.files.items() if p not in paths}) for patch in patches]
    return [patch for patch in trimmed if patch.files]


__all__ = ["EngineLifecycle", "MoveReport", "StatusReport"]
