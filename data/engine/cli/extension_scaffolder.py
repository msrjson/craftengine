"""Generate extensions and screens: `make:module`, `make:plugin`, `make:theme`, `make:screen`.

Every generated extension is self-contained under the first configured root of
its kind (`app/modules`, `app/plugins`, `app/themes` by default), installs and
activates as it is, and ships its copy as keys in `en`, `pt-BR` and `es`.
Templates live in `extension_templates/` as `.stub` files; placeholders are
`__SLUG__`, `__CLASS__`, `__NAME__`, `__URL__`, `__SCREEN__`, `__SCREEN_CLASS__`
and the engine version bounds.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import os
import re
from typing import Final

from engine.extensions.errors import ExtensionError
from engine.extensions.manifest import MANIFEST_FILE, ExtensionKind

TEMPLATES: Final[str] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension_templates")
STUB_SUFFIX: Final[str] = ".stub"
_SLUG = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
_ROUTE_MARKER: Final[str] = "    # make:screen adds routes above this line."

#: Templates whose generated name starts with a dot, stored without it:
#: setuptools' package-data globs skip hidden files, so a `.gitkeep.stub` is in
#: a source checkout and missing from every installed package.
DOTFILE_RENAMES: Final[dict[str, str]] = {"gitkeep": ".gitkeep"}

#: Default root of each kind, matching `config/extensions.py`.
DEFAULT_ROOTS: Final[dict[ExtensionKind, str]] = {
    ExtensionKind.MODULE: os.path.join("app", "modules"),
    ExtensionKind.PLUGIN: os.path.join("app", "plugins"),
    ExtensionKind.THEME: os.path.join("app", "themes"),
}


def build_extension(base_path: str, kind: ExtensionKind, slug: str, *, force: bool = False) -> list[str]:
    """Write a new extension of `kind` named `slug`; return the files written.

    Raises:
        ExtensionError: `EXTENSION_SLUG_INVALID`, or `EXTENSION_ALREADY_EXISTS`
            when the directory exists and `force` is false.
    """
    if not _SLUG.match(slug):
        raise ExtensionError("EXTENSION_SLUG_INVALID", slug)
    target = os.path.join(base_path, DEFAULT_ROOTS[kind], slug)
    if os.path.exists(os.path.join(target, MANIFEST_FILE)) and not force:
        raise ExtensionError("EXTENSION_ALREADY_EXISTS", slug, target)
    values = _values(slug)
    written: list[str] = []
    source_root = os.path.join(TEMPLATES, kind.value)
    for directory, _subdirectories, files in os.walk(source_root):
        for name in sorted(files):
            relative = os.path.relpath(os.path.join(directory, name), source_root)
            destination = os.path.join(target, _dotfile(_fill(relative[: -len(STUB_SUFFIX)], values)))
            written.append(_write(destination, _render(os.path.join(directory, name), values)))
    return sorted(written)


def build_screen(base_path: str, slug: str, screen: str) -> list[str]:
    """Add a screen to module `slug`: controller, view, route and three-locale title.

    Raises:
        ExtensionError: The module does not exist, the screen name is invalid,
            or the screen already exists.
    """
    module = os.path.join(base_path, DEFAULT_ROOTS[ExtensionKind.MODULE], slug)
    if not os.path.isfile(os.path.join(module, MANIFEST_FILE)):
        raise ExtensionError("EXTENSION_NOT_FOUND", slug, module)
    if not _SLUG.match(screen):
        raise ExtensionError("EXTENSION_SCREEN_INVALID", slug, screen)
    values = {**_values(slug), "__SCREEN__": screen, "__SCREEN_CLASS__": _studly(screen)}
    controller = os.path.join(module, "controllers", f"{screen}_controller.py")
    if os.path.exists(controller):
        raise ExtensionError("EXTENSION_SCREEN_EXISTS", slug, screen)
    written = [
        _write(controller, _render(os.path.join(TEMPLATES, "screen", "controller.py.stub"), values)),
        _write(os.path.join(module, "views", screen, "index.forge.py"), _render(os.path.join(TEMPLATES, "screen", "view.forge.py.stub"), values)),
        _add_route(module, slug, screen, values["__SCREEN_CLASS__"]),
        _add_title_keys(module, slug, screen),
    ]
    return written


def _values(slug: str) -> dict[str, str]:
    """Return the placeholder values of an extension named `slug`."""
    import engine

    major = int(str(getattr(engine, "__version__", "4")).split(".")[0])
    return {
        "__SLUG__": slug, "__CLASS__": _studly(slug), "__NAME__": slug.replace("_", " ").title(),
        "__URL__": slug.replace("_", "-"), "__ENGINE_MAJOR__": str(major), "__ENGINE_NEXT__": str(major + 1),
    }


def _dotfile(path: str) -> str:
    """Restore the leading dot of a template stored without it."""
    directory, name = os.path.split(path)
    return os.path.join(directory, DOTFILE_RENAMES.get(name, name))


def _studly(value: str) -> str:
    """`sales_pipeline` -> `SalesPipeline`."""
    return "".join(part.capitalize() for part in value.split("_"))


def _fill(text: str, values: dict[str, str]) -> str:
    """Replace every placeholder in `text`, longest first."""
    for placeholder in sorted(values, key=len, reverse=True):
        text = text.replace(placeholder, values[placeholder])
    return text


def _render(stub: str, values: dict[str, str]) -> str:
    """Return the stub's content with placeholders filled."""
    with open(stub, encoding="utf-8") as handle:
        return _fill(handle.read(), values)


def _write(path: str, content: str) -> str:
    """Write `content` to `path`, creating directories; return the path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _add_route(module: str, slug: str, screen: str, screen_class: str) -> str:
    """Insert the screen's route and import into the module's `routes.py`."""
    path = os.path.join(module, "routes.py")
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    if _ROUTE_MARKER not in source:
        raise ExtensionError("EXTENSION_ROUTES_MARKER_MISSING", slug, path)
    url = f"/{slug.replace('_', '-')}/{screen.replace('_', '-')}"
    route = f'    router.get("{url}", [{screen_class}Controller, "index"]).name("{slug}.{screen}")\n'
    source = source.replace(_ROUTE_MARKER, route + _ROUTE_MARKER)
    import_line = f"from .controllers.{screen}_controller import {screen_class}Controller\n"
    first_import = source.index("from ")
    return _write(path, source[:first_import] + import_line + source[first_import:])


def _add_title_keys(module: str, slug: str, screen: str) -> str:
    """Add the screen's title key to the module's catalog in every locale."""
    path = os.path.join(module, "lang", "catalog.json")
    with open(path, encoding="utf-8") as handle:
        catalog = json.load(handle)
    title = screen.replace("_", " ").title()
    for locale in ("en", "pt-BR", "es"):
        catalog.setdefault(locale, {})[f"{slug}.{screen}.title"] = title
    return _write(path, json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")


__all__ = ["DEFAULT_ROOTS", "build_extension", "build_screen"]
