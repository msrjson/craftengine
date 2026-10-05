"""View layers: extension namespaces and theme overrides on top of `resources/views`.

A view name is resolved through a chain:

1. the active theme, when one is selected: `<theme>/views/<path>` for an
   application view, `<theme>/views/<slug>/<path>` for an extension view;
2. the extension that owns the namespace, for `slug::path`;
3. `resources/views`.

The theme is part of the name Jinja sees (`@theme/<slug>/<name>`), so compiled
templates are cached per theme and two requests on different themes never share
one. `@extends` and `@include` inherit the theme of the template that uses them.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from jinja2 import BaseLoader, Environment, FileSystemLoader, TemplateNotFound

#: Separates an extension slug from the view path: `billing::invoices/index`.
NAMESPACE_SEPARATOR = "::"
_THEME_PREFIX = "@theme/"


def themed_name(name: str, theme: str | None) -> str:
    """Return the name Jinja loads for `name` under `theme` (or none)."""
    return f"{_THEME_PREFIX}{theme}/{name}" if theme else name


def split_themed(name: str) -> tuple[str | None, str]:
    """Split a loaded name into its theme (or None) and the logical view name."""
    if not name.startswith(_THEME_PREFIX):
        return None, name
    theme, _, logical = name[len(_THEME_PREFIX):].partition("/")
    return theme, logical


class LayeredLoader(BaseLoader):
    """Find a view in the theme, then the extension namespace, then the base directory.

    Args:
        base_directory: The application's `resources/views`.
    """

    def __init__(self, base_directory: str) -> None:
        self.base = FileSystemLoader(base_directory)
        self.namespaces: dict[str, str] = {}
        self.themes: dict[str, str] = {}

    def get_source(self, environment: Environment, template: str) -> tuple[str, str | None, Callable[[], bool] | None]:
        """Return the source of the first layer holding `template`.

        Raises:
            TemplateNotFound: No layer holds it.
        """
        theme, logical = split_themed(template)
        namespace, _, path = logical.rpartition(NAMESPACE_SEPARATOR)
        for loader, name in self._candidates(theme, namespace, path):
            try:
                return loader.get_source(environment, name)
            except TemplateNotFound:
                continue
        raise TemplateNotFound(template)

    def list_templates(self) -> list[str]:
        """Return the application's own templates (the base layer)."""
        return self.base.list_templates()

    def _candidates(self, theme: str | None, namespace: str, path: str) -> list[tuple[BaseLoader, str]]:
        """Return (loader, name) pairs in resolution order."""
        candidates: list[tuple[BaseLoader, str]] = []
        if theme and theme in self.themes:
            themed = f"{namespace}/{path}" if namespace else path
            candidates.append((FileSystemLoader(self.themes[theme]), themed))
        if namespace:
            if namespace in self.namespaces:
                candidates.append((FileSystemLoader(self.namespaces[namespace]), path))
            return candidates
        candidates.append((self.base, path))
        return candidates


class LayeredEnvironment(Environment):
    """Jinja environment whose `@extends` and `@include` keep the parent's theme."""

    def join_path(self, template: str, parent: str) -> str:
        """Prefix `template` with the theme of `parent`, when it has one."""
        theme, _ = split_themed(parent)
        _, logical = split_themed(template)
        return themed_name(logical, theme)


def resolve_directory(directory: str) -> str:
    """Return an absolute directory for a view layer."""
    return os.path.abspath(directory)


def describe(loader: Any) -> dict[str, dict[str, str]]:
    """Return the registered namespaces and themes, for diagnostics."""
    return {"namespaces": dict(loader.namespaces), "themes": dict(loader.themes)}


__all__ = [
    "LayeredEnvironment", "LayeredLoader", "NAMESPACE_SEPARATOR",
    "describe", "resolve_directory", "split_themed", "themed_name",
]
