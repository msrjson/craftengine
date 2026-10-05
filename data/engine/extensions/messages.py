"""Seed the extension model's messages from `lang/catalog.json`.

The catalog holds every `message_key` of `engine.extensions.errors` and the
state and kind labels, in `en`, `pt-BR` and `es`. Existing rows are never
changed, so a project's edited copy survives.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import os
from typing import Any

from engine.extensions.resources import REQUIRED_LOCALES, seed_translations

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "lang", "catalog.json")


def catalog() -> dict[str, dict[str, str]]:
    """Return the shipped catalog, keyed by locale."""
    with open(CATALOG_PATH, encoding="utf-8") as handle:
        loaded = json.load(handle)
    return {locale: loaded[locale] for locale in REQUIRED_LOCALES}


def seed_messages(db: Any) -> int:
    """Insert every message row the translation store lacks; return how many."""
    return seed_translations(db, catalog())


__all__ = ["CATALOG_PATH", "catalog", "seed_messages"]
