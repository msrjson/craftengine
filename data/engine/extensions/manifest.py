"""The extension manifest: `extension.toml` at the root of every extension.

    slug = "billing"
    kind = "module"
    version = "1.0.0"
    engine = ">=4.3,<5"
    name_key = "billing.extension.name"

    [requires]
    catalog = ">=1.0"

The manifest is the whole contract between an extension and the engine: what
it is, which engine it runs on, and which other extensions it needs. Parsing
uses `tomllib` from the standard library.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from engine.extensions.errors import ExtensionError
from engine.extensions.versions import check_range, parse_version

MANIFEST_FILE = "extension.toml"
_SLUG = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


class ExtensionKind(StrEnum):
    """What an extension is, which decides what it may contribute."""

    MODULE = "module"
    PLUGIN = "plugin"
    THEME = "theme"
    CONNECTOR = "connector"


#: Files and directories a kind may not ship. A theme is presentation only;
#: a connector is headless (an integration with an outside service), so it
#: ships no views and no assets. It may ship routes, for inbound webhooks.
FORBIDDEN_CONTRIBUTIONS: dict[ExtensionKind, tuple[str, ...]] = {
    ExtensionKind.MODULE: (),
    ExtensionKind.PLUGIN: (),
    ExtensionKind.THEME: ("provider.py", "routes.py", "migrations"),
    ExtensionKind.CONNECTOR: ("views", "assets"),
}


@dataclass(frozen=True)
class Manifest:
    """A parsed and validated `extension.toml`.

    Attributes:
        slug: Unique identifier; also the view namespace and the translation
            key prefix.
        kind: Module, plugin, theme or connector.
        version: Dotted integers.
        engine: Range of engine versions the extension runs on.
        name_key: Translation key of the human-readable name.
        requires: Other extensions this one needs, slug to version range.
        path: Absolute directory of the extension.
    """

    slug: str
    kind: ExtensionKind
    version: str
    path: str
    engine: str = ""
    name_key: str = ""
    requires: dict[str, str] = field(default_factory=dict)

    def file(self, *parts: str) -> str:
        """Return the absolute path of a file inside the extension."""
        return os.path.join(self.path, *parts)

    def has(self, *parts: str) -> bool:
        """Return whether the extension ships a file or directory."""
        return os.path.exists(self.file(*parts))


def load_manifest(directory: str) -> Manifest:
    """Read and validate the manifest of the extension in `directory`.

    Raises:
        ExtensionError: The file is missing or unreadable, a field is missing
            or malformed, or the directory ships something its kind may not.
    """
    path = os.path.join(directory, MANIFEST_FILE)
    try:
        with open(path, "rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ExtensionError("EXTENSION_MANIFEST_UNREADABLE", detail=f"{path}: {error}") from error
    manifest = _build(raw, os.path.abspath(directory))
    _check_contributions(manifest)
    return manifest


def _build(raw: dict[str, Any], directory: str) -> Manifest:
    """Turn the raw TOML table into a `Manifest`, validating every field."""
    slug = str(raw.get("slug", ""))
    if not _SLUG.match(slug):
        raise ExtensionError("EXTENSION_SLUG_INVALID", slug, directory)
    try:
        kind = ExtensionKind(str(raw.get("kind", "")))
    except ValueError as error:
        raise ExtensionError("EXTENSION_KIND_INVALID", slug, str(raw.get("kind", ""))) from error
    version = str(raw.get("version", ""))
    parse_version(version)
    requires = raw.get("requires", {}) or {}
    if not isinstance(requires, dict) or slug in requires:
        raise ExtensionError("EXTENSION_REQUIRES_INVALID", slug)
    for spec in (str(raw.get("engine", "")), *map(str, requires.values())):
        check_range(spec)
    return Manifest(
        slug=slug, kind=kind, version=version, path=directory,
        engine=str(raw.get("engine", "")), name_key=str(raw.get("name_key", "")),
        requires={str(name): str(spec) for name, spec in requires.items()},
    )


def _check_contributions(manifest: Manifest) -> None:
    """Refuse a directory shipping something its kind may not contribute."""
    for forbidden in FORBIDDEN_CONTRIBUTIONS[manifest.kind]:
        if manifest.has(forbidden):
            raise ExtensionError("EXTENSION_KIND_CONTRIBUTION_FORBIDDEN", manifest.slug, forbidden)


__all__ = ["ExtensionKind", "FORBIDDEN_CONTRIBUTIONS", "MANIFEST_FILE", "Manifest", "load_manifest"]
