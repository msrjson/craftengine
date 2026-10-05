"""An extension's own schema and copy: `migrations/` and `lang/catalog.json`.

Both are applied on install and never undone: migrations are forward-only and
translations are never deleted (NR-02). Uninstalling leaves tables, rows and
translations in place.

`lang/catalog.json` maps each locale to its keys:

    {"en": {"billing.extension.name": "Billing"},
     "pt-BR": {"billing.extension.name": "Faturamento"},
     "es": {"billing.extension.name": "Facturacion"}}

Every key starts with the extension's slug and exists in every required
locale; a catalog that breaks either rule is refused before anything is written.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any

from engine.extensions.errors import ExtensionError
from engine.extensions.manifest import Manifest

#: Source, default runtime locale and alternative (governance section 4).
REQUIRED_LOCALES: tuple[str, ...] = ("en", "pt-BR", "es")
CATALOG = ("lang", "catalog.json")


def run_migrations(app: Any, manifest: Manifest) -> list[str]:
    """Apply the extension's pending migrations; return the names that ran."""
    if not manifest.has("migrations"):
        return []
    from engine.migrations.migrator import Migrator

    return Migrator(app, path=manifest.file("migrations")).run()


def load_catalog(manifest: Manifest) -> dict[str, dict[str, str]]:
    """Read and validate the extension's catalog; empty when it ships none.

    Raises:
        ExtensionError: The file is unreadable, a key lacks the slug prefix, or
            a required locale is missing a key another locale has.
    """
    if not manifest.has(*CATALOG):
        return {}
    try:
        with open(manifest.file(*CATALOG), encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (OSError, ValueError) as error:
        raise ExtensionError("EXTENSION_CATALOG_UNREADABLE", manifest.slug, str(error)) from error
    _check_catalog(manifest.slug, catalog)
    return {locale: {str(key): str(value) for key, value in catalog[locale].items()} for locale in REQUIRED_LOCALES}


def seed_translations(db: Any, catalog: dict[str, dict[str, str]]) -> int:
    """Insert every catalog row the store lacks; never overwrite an edited one.

    Returns:
        How many rows were inserted.
    """
    inserted = 0
    for locale, entries in catalog.items():
        for key, value in entries.items():
            if db.table("translations").where("key", key).where("locale", locale).first() is None:
                db.table("translations").insert({"key": key, "locale": locale, "value": value})
                inserted += 1
    return inserted


def _check_catalog(slug: str, catalog: Any) -> None:
    """Refuse a catalog with a foreign key prefix or a locale missing keys."""
    if not isinstance(catalog, dict) or any(not isinstance(catalog.get(locale), dict) for locale in REQUIRED_LOCALES):
        raise ExtensionError("EXTENSION_CATALOG_LOCALE_MISSING", slug, ",".join(REQUIRED_LOCALES))
    keys = {key for locale in REQUIRED_LOCALES for key in catalog[locale]}
    foreign = sorted(key for key in keys if not key.startswith(slug + "."))
    if foreign:
        raise ExtensionError("EXTENSION_CATALOG_KEY_PREFIX", slug, foreign[0])
    for locale in REQUIRED_LOCALES:
        missing = sorted(keys - set(catalog[locale]))
        if missing:
            raise ExtensionError("EXTENSION_CATALOG_KEY_MISSING", slug, f"{locale}:{missing[0]}")


__all__ = ["REQUIRED_LOCALES", "load_catalog", "run_migrations", "seed_translations"]
