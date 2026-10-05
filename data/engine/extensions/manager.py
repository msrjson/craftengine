"""ExtensionManager: discover, install, activate, isolate and retire extensions.

The engine is the runtime; each extension is a unit it runs. The manager keeps
the lifecycle (`discovered -> installed -> active <-> inactive -> uninstalled`,
plus `failed`), refuses transitions that would break a dependency, loads each
active extension behind its own error boundary, and answers the one question
the kernel, the proxy and the asset mount ask: can this extension serve now?

Where extensions live is the application's decision: `extensions.paths` in
its configuration lists the roots, relative to the application base path.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
import os
import time
from enum import StrEnum
from typing import Any

from engine.extensions.breaker import BreakerState, CircuitBreaker
from engine.extensions.errors import ExtensionError
from engine.extensions.loader import ExtensionLoader
from engine.extensions.manifest import MANIFEST_FILE, Manifest, load_manifest
from engine.extensions.resources import load_catalog, run_migrations, seed_translations
from engine.extensions.store import ExtensionState, ExtensionStore
from engine.extensions.versions import satisfies

_LOG = logging.getLogger("craft.extensions")

_INSTALLABLE = {ExtensionState.DISCOVERED, ExtensionState.UNINSTALLED}
_ACTIVATABLE = {ExtensionState.INSTALLED, ExtensionState.INACTIVE, ExtensionState.FAILED}
_PRESENT = {ExtensionState.INSTALLED, ExtensionState.ACTIVE, ExtensionState.INACTIVE, ExtensionState.FAILED}


class Availability(StrEnum):
    """Whether an extension can serve a call right now."""

    UNKNOWN = "unknown"
    SERVING = "serving"
    DISABLED = "disabled"
    UNAVAILABLE = "unavailable"


class ExtensionManager:
    """Own the lifecycle and the health of every extension.

    Args:
        app: The application container.
    """

    def __init__(self, app: Any) -> None:
        self.app = app
        config = app.make("config")
        self.roots: list[str] = [str(root) for root in (config.get("extensions.paths", []) or [])]
        self.engine_version = _engine_version()
        self.breaker = CircuitBreaker(
            threshold=int(config.get("extensions.failure_threshold", 5)),
            window=float(config.get("extensions.failure_window", 60)),
            cooldown=float(config.get("extensions.cooldown", 30)),
        )
        self.reconcile_interval = float(config.get("extensions.reconcile_interval", 5))
        self.store = ExtensionStore(lambda: app.make("db"))
        self.loader = ExtensionLoader(app, self)
        self.discovery_errors: dict[str, ExtensionError] = {}
        self._manifests: dict[str, Manifest] | None = None
        #: slug -> (read at, state): the request path reads the store at most
        #: once per `reconcile_interval`; a write in this process clears it.
        self._state_cache: dict[str, tuple[float, ExtensionState]] = {}

    # -- discovery -------------------------------------------------------------

    def manifests(self, refresh: bool = False) -> dict[str, Manifest]:
        """Return every valid manifest under the configured roots, keyed by slug.

        A broken or duplicated manifest never stops discovery of the others;
        it is kept in `discovery_errors`, keyed by its directory.
        """
        if self._manifests is None or refresh:
            self._manifests, self.discovery_errors = {}, {}
            for directory in self._candidate_directories():
                self._discover_one(directory)
        return self._manifests

    def manifest(self, slug: str) -> Manifest:
        """Return the manifest of `slug`.

        Raises:
            ExtensionError: `EXTENSION_NOT_FOUND`.
        """
        manifest = self.manifests().get(slug)
        if manifest is None:
            raise ExtensionError("EXTENSION_NOT_FOUND", slug)
        return manifest

    def _candidate_directories(self) -> list[str]:
        """Return every directory directly under a root that holds a manifest."""
        found: list[str] = []
        for root in self.roots:
            absolute = root if os.path.isabs(root) else os.path.join(self.app.base_path, root)
            if os.path.isdir(absolute):
                found.extend(
                    os.path.join(absolute, entry) for entry in sorted(os.listdir(absolute))
                    if os.path.isfile(os.path.join(absolute, entry, MANIFEST_FILE))
                )
        return found

    def _discover_one(self, directory: str) -> None:
        """Validate one manifest and record it, or record why it was refused."""
        try:
            manifest = load_manifest(directory)
        except ExtensionError as error:
            self.discovery_errors[directory] = error
            _LOG.warning("extension_manifest_refused path=%s code=%s", directory, error.code)
            return
        if manifest.slug in self._manifests:
            self.discovery_errors[directory] = ExtensionError("EXTENSION_SLUG_DUPLICATE", manifest.slug, directory)
            return
        self._manifests[manifest.slug] = manifest

    # -- lifecycle -------------------------------------------------------------

    def state(self, slug: str) -> ExtensionState:
        """Return the persisted lifecycle state of `slug`."""
        return self.store.state(slug)

    def install(self, slug: str) -> list[str]:
        """Run the extension's migrations, seed its translations, mark it installed.

        Returns:
            The migrations that ran.

        Raises:
            ExtensionError: Not found, already installed, engine out of range,
                a dependency missing, or a catalog refused.
        """
        manifest = self.manifest(slug)
        if self.state(slug) not in _INSTALLABLE:
            raise ExtensionError("EXTENSION_ALREADY_INSTALLED", slug)
        self._check_engine(manifest)
        self._check_dependencies(manifest, _PRESENT, "EXTENSION_DEPENDENCY_MISSING")
        catalog = load_catalog(manifest)
        ran = run_migrations(self.app, manifest)
        seed_translations(self.app.make("db"), catalog)
        self._save(manifest, ExtensionState.INSTALLED)
        return ran

    def activate(self, slug: str) -> None:
        """Load the extension and mark it active.

        Raises:
            ExtensionError: Not installed, engine out of range, a dependency not
                active at a compatible version, or `EXTENSION_BOOT_FAILED` (the
                extension is then marked failed).
        """
        manifest = self.manifest(slug)
        if self.state(slug) not in _ACTIVATABLE:
            raise ExtensionError("EXTENSION_NOT_ACTIVATABLE", slug, self.state(slug).value)
        self._check_engine(manifest)
        self._check_dependencies(manifest, {ExtensionState.ACTIVE}, "EXTENSION_DEPENDENCY_INACTIVE")
        self.breaker.reset(slug)
        self._load(manifest)
        self._save(manifest, ExtensionState.ACTIVE)

    def deactivate(self, slug: str) -> None:
        """Undo the extension's contributions and mark it inactive.

        Raises:
            ExtensionError: Not active, or an active extension depends on it.
        """
        manifest = self.manifest(slug)
        if self.state(slug) not in {ExtensionState.ACTIVE, ExtensionState.FAILED}:
            raise ExtensionError("EXTENSION_NOT_ACTIVE", slug)
        self._refuse_dependents(slug, {ExtensionState.ACTIVE}, "EXTENSION_HAS_ACTIVE_DEPENDENTS")
        self.loader.unload(slug)
        self._save(manifest, ExtensionState.INACTIVE)

    def uninstall(self, slug: str) -> None:
        """Mark the extension uninstalled; its tables, rows and translations stay.

        Raises:
            ExtensionError: Still active, or another installed extension needs it.
        """
        manifest = self.manifest(slug)
        if self.state(slug) is ExtensionState.ACTIVE:
            raise ExtensionError("EXTENSION_STILL_ACTIVE", slug)
        if self.state(slug) not in _PRESENT:
            raise ExtensionError("EXTENSION_NOT_INSTALLED", slug)
        self._refuse_dependents(slug, _PRESENT, "EXTENSION_HAS_INSTALLED_DEPENDENTS")
        self._save(manifest, ExtensionState.UNINSTALLED)

    def boot(self) -> list[str]:
        """Load every active extension in dependency order; return those loaded.

        An extension that fails to load, or whose dependency did not load, is
        marked failed and logged; the application boots without it.
        """
        loaded: list[str] = []
        manifests = self.manifests()
        for slug in _dependency_order(manifests):
            manifest = manifests[slug]
            if self.state(slug) is not ExtensionState.ACTIVE:
                continue
            if all(self.loader.is_loaded(name) for name in manifest.requires) and self._try_load(manifest):
                loaded.append(slug)
            else:
                self._save(manifest, ExtensionState.FAILED)
        return loaded

    def reconcile(self) -> None:
        """Converge this worker on the persisted states other workers may have set."""
        try:
            rows = self.store.all()
            for slug, manifest in self.manifests().items():
                state = ExtensionState(rows.get(slug, {}).get("state", ExtensionState.DISCOVERED.value))
                if state is ExtensionState.ACTIVE and not self.loader.is_loaded(slug):
                    self._try_load(manifest)
                elif state is not ExtensionState.ACTIVE and self.loader.is_loaded(slug):
                    self.loader.unload(slug)
        finally:
            _release_connection(self.app)

    # -- availability and the error boundary ----------------------------------

    def availability(self, slug: str) -> Availability:
        """Answer whether `slug` can serve a call right now, without side effects."""
        if self.loader.is_loaded(slug):
            healthy = self.breaker.state(slug) is not BreakerState.OPEN
            return Availability.SERVING if healthy else Availability.UNAVAILABLE
        if slug not in self.manifests():
            return Availability.UNKNOWN
        return Availability.UNAVAILABLE if self._cached_state(slug) is ExtensionState.FAILED else Availability.DISABLED

    def allow(self, slug: str) -> bool:
        """Return whether a call into `slug` may run (the breaker may let a trial through)."""
        return self.loader.is_loaded(slug) and self.breaker.allow(slug)

    def succeeded(self, slug: str) -> None:
        """Record a successful call into `slug`."""
        self.breaker.record_success(slug)

    def failed(self, slug: str, error: BaseException) -> bool:
        """Record a failure of `slug`; return True when it is a domain error to re-raise."""
        if int(getattr(error, "status_code", 500) or 500) < 500:
            self.breaker.record_success(slug)
            return True
        code = str(getattr(error, "code", "") or type(error).__name__)
        opened = self.breaker.record_failure(slug, code)
        _LOG.error("extension_failed slug=%s error=%s breaker_opened=%s", slug, code, opened, exc_info=error)
        return False

    def assets_directory(self, slug: str) -> str | None:
        """Return the assets directory of `slug` while it serves, else None."""
        manifest = self.manifests().get(slug)
        if manifest is None or not manifest.has("assets") or self.availability(slug) is not Availability.SERVING:
            return None
        return manifest.file("assets")

    def migration_paths(self) -> list[str]:
        """Return the migration directories of every installed extension."""
        return [
            manifest.file("migrations") for slug, manifest in self.manifests().items()
            if manifest.has("migrations") and self.state(slug) in _PRESENT
        ]

    def status(self) -> list[dict[str, Any]]:
        """Describe every discovered extension for the CLI and the panel."""
        return [
            {
                "slug": slug, "kind": manifest.kind.value, "version": manifest.version,
                "name_key": manifest.name_key, "requires": dict(manifest.requires),
                "state": self.state(slug).value, "availability": self.availability(slug).value,
                "breaker": self.breaker.state(slug).value, "last_error": self.breaker.last_error(slug),
                "path": manifest.path,
            }
            for slug, manifest in sorted(self.manifests().items())
        ]

    # -- internals -------------------------------------------------------------

    def _try_load(self, manifest: Manifest) -> bool:
        """Load `manifest`; on failure log it, mark it failed and return False."""
        try:
            self._load(manifest)
        except ExtensionError as error:
            _LOG.error("extension_boot_failed slug=%s detail=%s", manifest.slug, error.detail, exc_info=error.__cause__)
            self._save(manifest, ExtensionState.FAILED)
            return False
        return True

    def _load(self, manifest: Manifest) -> None:
        """Load `manifest`, marking it failed when it raises."""
        if self.loader.is_loaded(manifest.slug):
            return
        try:
            self.loader.load(manifest)
        except ExtensionError:
            self._save(manifest, ExtensionState.FAILED)
            raise

    def _cached_state(self, slug: str) -> ExtensionState:
        """Return the state of `slug`, reading the store at most once per interval."""
        cached = self._state_cache.get(slug)
        if cached is not None and time.monotonic() - cached[0] < self.reconcile_interval:
            return cached[1]
        state = self.state(slug)
        self._state_cache[slug] = (time.monotonic(), state)
        return state

    def _save(self, manifest: Manifest, state: ExtensionState) -> None:
        """Persist the new state of `manifest`."""
        self._state_cache.pop(manifest.slug, None)
        self.store.save(manifest.slug, manifest.kind.value, manifest.version, state, manifest.path)

    def _check_engine(self, manifest: Manifest) -> None:
        """Refuse an extension written for another engine version."""
        if not satisfies(self.engine_version, manifest.engine):
            raise ExtensionError("EXTENSION_ENGINE_INCOMPATIBLE", manifest.slug, f"{manifest.engine} vs {self.engine_version}")

    def _check_dependencies(self, manifest: Manifest, states: set[ExtensionState], code: str) -> None:
        """Refuse when a dependency is absent, in the wrong state or the wrong version."""
        for name, spec in manifest.requires.items():
            dependency = self.manifests().get(name)
            if dependency is None or self.state(name) not in states:
                raise ExtensionError(code, manifest.slug, name)
            if not satisfies(dependency.version, spec):
                raise ExtensionError("EXTENSION_DEPENDENCY_VERSION", manifest.slug, f"{name} {spec}")

    def _refuse_dependents(self, slug: str, states: set[ExtensionState], code: str) -> None:
        """Refuse when another extension in `states` requires `slug`."""
        for name, manifest in self.manifests().items():
            if slug in manifest.requires and self.state(name) in states:
                raise ExtensionError(code, slug, name)


def _dependency_order(manifests: dict[str, Manifest]) -> list[str]:
    """Return slugs so every extension comes after what it requires; cycles go last."""
    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(slug: str) -> None:
        if slug in ordered or slug in visiting or slug not in manifests:
            return
        visiting.add(slug)
        for name in sorted(manifests[slug].requires):
            visit(name)
        visiting.discard(slug)
        ordered.append(slug)

    for slug in sorted(manifests):
        visit(slug)
    return ordered


def _engine_version() -> str:
    """Return the running engine version."""
    import engine

    return str(getattr(engine, "__version__", "0"))


def _release_connection(app: Any) -> None:
    """Return this thread's pooled connection, when the database is bound."""
    try:
        app.make("db").release()
    except Exception:  # noqa: BLE001 - nothing to release is fine
        _LOG.debug("extension_reconcile_release_skipped", exc_info=True)


class ReconcileTicker:
    """Throttle `reconcile` to once per interval; registered on the router.

    Args:
        manager: The manager to reconcile.
    """

    def __init__(self, manager: ExtensionManager) -> None:
        self._manager = manager
        self._last = time.monotonic()

    def due(self) -> bool:
        """Return whether the interval elapsed since the last run."""
        return time.monotonic() - self._last >= self._manager.reconcile_interval

    def __call__(self) -> None:
        """Run one reconcile and restart the interval."""
        self._last = time.monotonic()
        self._manager.reconcile()


__all__ = ["Availability", "ExtensionManager", "ReconcileTicker"]
