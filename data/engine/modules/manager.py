"""
ModuleManager - Manages dynamic framework modules discovery and state.
Category: Subsystem (Core Framework).
Relations:
  - Reads and writes the `modules` table through the DB facade.
  - Defers to `engine.extensions` for any slug that is an extension: the
    kernel asks this manager whether a module-scoped route may serve, and an
    extension's answer comes from its lifecycle state and circuit breaker.
References:
  - Skill: `craft-development` (`.agents/skills/framework/craft-development/SKILL.md`,
    workspace root, outside this repository)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import time
from typing import Any, Dict, List, Optional, Tuple

from craft.facades import DB


class ModuleManager:
    """Manages application modules state and lifecycle."""

    #: Seconds an `is_enabled()` answer is reused before hitting the database
    #: again. The router asks once per request for every module-scoped route,
    #: so an uncached lookup is a SELECT on the hot path. Bounded staleness:
    #: a module toggled by another process (CLI, second worker) takes at most
    #: this long to take effect here; a toggle in *this* process is immediate,
    #: because `_set_enabled()` clears the cache.
    cache_ttl = 5.0

    def __init__(self, app: Any = None) -> None:
        self.app = app
        self._registered_modules: Dict[str, dict] = {}
        self._enabled_cache: Dict[str, Tuple[float, bool]] = {}

    def refusal(self, slug: str) -> Optional[Exception]:
        """Return the typed exception refusing a route of `slug`, or None to serve.

        An extension answers from its lifecycle and health: inactive is a 404
        `MODULE_DISABLED`, failed or circuit-open a 503 `EXTENSION_UNAVAILABLE`.
        Any other module answers from this manager's state, falling back to
        `modules.<slug>.enabled` in configuration (enabled by default).
        """
        from engine.extensions.errors import ExtensionUnavailableError

        extensions = self._extensions()
        if extensions is not None:
            availability = extensions.availability(slug).value
            if availability == "serving":
                return None
            if availability == "unavailable":
                return ExtensionUnavailableError(slug)
            if availability == "disabled":
                return ExtensionUnavailableError(slug, "MODULE_DISABLED")
        return None if self._legacy_enabled(slug) else ExtensionUnavailableError(slug, "MODULE_DISABLED")

    def report_failure(self, slug: str, error: BaseException) -> None:
        """Count a failure of a module-scoped route toward the extension's health."""
        extensions = self._extensions()
        if extensions is not None and extensions.availability(slug).value != "unknown":
            extensions.failed(slug, error)

    def _extensions(self) -> Any:
        """Return the extension manager, when the application runs one."""
        if self.app is None or not self.app.bound("extensions"):
            return None
        return self.app.make("extensions")

    def _legacy_enabled(self, slug: str) -> bool:
        """Return the state of a non-extension module, config deciding the unknown."""
        state = self.state(slug)
        if state is not None:
            return state
        if self.app is None:
            return True
        return bool(self.app.make("config").get(f"modules.{slug}.enabled", True))

    def register(self, slug: str, name: str, description: str = "", version: str = "1.0.0") -> None:
        """Register a module in memory."""
        self._registered_modules[slug] = {
            "slug": slug,
            "name": name,
            "description": description,
            "version": version,
            "enabled": True,
        }

    def all(self) -> List[dict]:
        """Fetch all modules registered in DB or memory."""
        try:
            res = DB.statement("SELECT slug, name, enabled FROM modules")
            rows = res.fetchall()
            if rows:
                # Access by column name: SQLite rows are sqlite3.Row and the
                # MySQL/PostgreSQL cursors return dicts - positional indexing
                # raises KeyError on those drivers.
                return [{"slug": r["slug"], "name": r["name"], "enabled": bool(r["enabled"])} for r in rows]
        except Exception:
            pass
        return list(self._registered_modules.values())

    def state(self, slug: str) -> Optional[bool]:
        """Known state of a module, or None when the manager has never heard of it.

        `None` is not "disabled": it means neither the `modules` table nor the
        in-memory registry knows this slug, and the caller decides the default
        (the router falls back to `modules.<slug>.enabled` in config). Cached
        for `cache_ttl` seconds.
        """
        cached = self._enabled_cache.get(slug)
        if cached is not None and (time.monotonic() - cached[0]) < self.cache_ttl:
            return cached[1]

        resolved = self._resolve_state(slug)
        self._enabled_cache[slug] = (time.monotonic(), resolved)
        return resolved

    def is_enabled(self, slug: str) -> bool:
        """Check if a module is enabled. An unknown module is not enabled."""
        return self.state(slug) is True

    def forget_cached_state(self, slug: Optional[str] = None) -> None:
        """Drop the cached state for one module, or all of them.

        Call this after writing to the `modules` table behind the manager's
        back (raw SQL, a migration, another process) - the manager clears its
        own cache automatically on `enable()`/`disable()`.
        """
        if slug is None:
            self._enabled_cache.clear()
        else:
            self._enabled_cache.pop(slug, None)

    def _resolve_state(self, slug: str) -> Optional[bool]:
        try:
            res = DB.statement("SELECT enabled FROM modules WHERE slug = :slug", {"slug": slug})
            row = res.fetchone()
            if row is not None:
                return bool(row["enabled"])
        except Exception:
            pass
        mod = self._registered_modules.get(slug)
        return bool(mod["enabled"]) if mod else None

    def _set_enabled(self, slug: str, enabled: bool) -> bool:
        """Flip a module's state. Returns whether the module was found."""
        affected = 0
        try:
            result = DB.statement(
                "UPDATE modules SET enabled = :enabled WHERE slug = :slug",
                {"enabled": enabled, "slug": slug},
            )
            affected = getattr(result, "rowcount", 0) or 0
        except Exception:
            affected = 0

        in_memory = slug in self._registered_modules
        if in_memory:
            self._registered_modules[slug]["enabled"] = enabled

        # A toggle in this process must be visible on the very next request.
        self.forget_cached_state(slug)

        # Report what actually happened. Returning True unconditionally - as
        # this used to - made "enable a module that does not exist" look like a
        # success.
        return affected > 0 or in_memory

    def enable(self, slug: str) -> bool:
        """Enable a module. Returns False when there is no such module."""
        return self._set_enabled(slug, True)

    def disable(self, slug: str) -> bool:
        """Disable a module. Returns False when there is no such module."""
        return self._set_enabled(slug, False)
