"""Owned container registrations for extension providers.

Category: Core Framework (Extensions).
Relations: ExtensionContext records undo steps; Container reserves unused keys.
References: documentation/extensions.md, docs/adr/0004-extension-model.md.
"""

# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from engine.extensions.errors import ExtensionError


class ExtensionContainer:
    """Delegate resolution while recording a provider's service registrations.

    Args:
        app: The application's container.
        slug: The extension that owns registrations.
        on_unload: Records an undo step for deactivation or a failed boot.
    """

    def __init__(self, app: Any, slug: str, on_unload: Callable[[Callable[[], None]], None]) -> None:
        self._app = app
        self._slug = slug
        self._on_unload = on_unload

    def __getattr__(self, name: str) -> Any:
        """Delegate non-registration operations to the application."""
        return getattr(self._app, name)

    def bind(self, abstract: Any, concrete: Any = None, shared: bool = False) -> None:
        """Register an owned service, refusing an existing service key."""
        self._register(abstract, concrete, shared=shared)

    def singleton(self, abstract: Any, concrete: Any = None) -> None:
        """Register an owned singleton, including its cached instance."""
        self._register(abstract, concrete, shared=True)

    def scoped(self, abstract: Any, concrete: Any = None) -> None:
        """Register a service with a separate cache in each request."""
        self._register(abstract, concrete, scoped=True)

    def instance(self, abstract: Any, instance: Any) -> None:
        """Register an existing instance for this activation only."""
        self.singleton(abstract, lambda container: instance)

    def alias(self, abstract: Any, alias: str) -> None:
        """Register an owned alias, refusing an existing alias or service."""
        try:
            undo = self._app.alias_reversible(abstract, alias)
        except ValueError as error:
            raise ExtensionError("EXTENSION_BINDING_CONFLICT", self._slug, str(error)) from error
        self._on_unload(undo)

    def _register(self, abstract: Any, concrete: Any, *, shared: bool = False, scoped: bool = False) -> None:
        """Reserve a key and track its undo step before resolving anything."""
        try:
            undo = self._app.bind_reversible(abstract, concrete, shared=shared, scoped=scoped)
        except ValueError as error:
            raise ExtensionError("EXTENSION_BINDING_CONFLICT", self._slug, str(error)) from error
        self._on_unload(undo)
