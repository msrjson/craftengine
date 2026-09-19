"""Craft Framework — a batteries-included Python web framework.

The framework lives in `engine/` but is imported publicly as `craft.*`.
A meta path finder maps `craft.<anything>` onto `engine.<anything>` on
demand, so new subpackages are exposed automatically with no alias list to
keep in sync — and the unrelated third-party `dev` package on PyPI can
never shadow the framework.

:copyright: (c) 2026 Antonio Santos.
:license: MIT, see LICENSE for details.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import os
import sys
from collections.abc import Sequence
from types import ModuleType
from typing import Optional

__version__ = "3.22.0"
#: Increments by exactly 1 on every cut release, never reset and never skipped
#: (CONTRIBUTING.md, "Versioning and releases"). v3.11.0 was r00001, v3.12.0
#: r00002, v3.13.0 r00003 — this counter was left at r00001 through both of
#: those and corrected at v3.14.0 (r00004) rather than carried forward wrong.
__release__ = "r00015"
__author__ = "Antonio Santos"
__email__ = "snarthost@gmail.com"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2026 Antonio Santos"

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

_ALIAS = "craft"
_TARGET = __name__


class _AliasLoader(importlib.abc.Loader):
    """Loads `craft.x.y` by importing `engine.x.y` and re-exporting it."""

    def __init__(self, real_name: str):
        self.real_name = real_name

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType | None:
        return importlib.import_module(self.real_name)

    def exec_module(self, module: ModuleType) -> None:
        # The real module was already executed on import; nothing more to do.
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    """Resolves the `dev` namespace to the `engine` package."""

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname != _ALIAS and not fullname.startswith(_ALIAS + "."):
            return None

        real_name = _TARGET + fullname[len(_ALIAS) :]
        try:
            importlib.import_module(real_name)
        except ImportError:
            return None

        spec = importlib.machinery.ModuleSpec(fullname, _AliasLoader(real_name))
        spec.submodule_search_locations = getattr(
            sys.modules[real_name], "__path__", None
        )
        return spec


def install_alias() -> None:
    """Register the `dev` -> `engine` import alias (idempotent)."""
    if not any(isinstance(finder, _AliasFinder) for finder in sys.meta_path):
        sys.meta_path.insert(0, _AliasFinder())
    sys.modules[_ALIAS] = sys.modules[_TARGET]


install_alias()
