"""Translation helper for Craft Framework.

Locales follow BCP 47: a lowercase language subtag, optionally followed by an
uppercase region subtag — `en`, `pt`, `pt-BR`, `es`.

Lookups walk a fallback chain, so a regional locale inherits from its base
language and finally from the configured fallback:

    pt-BR  ->  pt  ->  en

Without that chain, asking for `pt-BR` when only `pt` is translated returned the
raw key.

Category: Core Framework (Support / i18n).
Relations:
  - `__()` reads from `config/lang.py`-style config entries and the
    `translations` table (seeded by `database/seeders/TranslationSeeder.py`);
    used by the `__` template helper (`engine/view/forge.py`).
References:
  - Guide: `documentation/localization.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, Dict, List, Optional

#: Locale for the request being handled, published by the SetLocale middleware.
#: It lives here rather than in the config repository because that repository is
#: a process-wide singleton: writing the locale there leaked one visitor's
#: language to the next request, and two concurrent requests would race.
current_locale: ContextVar[Optional[str]] = ContextVar("current_locale", default=None)


def get_current_locale() -> Optional[str]:
    return current_locale.get()


def normalize_locale(locale: Optional[str]) -> Optional[str]:
    """Canonicalise a BCP 47 tag: `PT-br` -> `pt-BR`, `EN` -> `en`."""
    if not locale:
        return None
    parts = str(locale).replace("_", "-").split("-")
    language = parts[0].lower()
    if len(parts) == 1:
        return language
    region = parts[1].upper()
    return f"{language}-{region}"


def locale_chain(locale: Optional[str], fallback: Optional[str] = None) -> List[str]:
    """Locales to try, most specific first.

    `pt-BR` yields ["pt-BR", "pt", "en"] — the region, then the base language,
    then the application fallback.
    """
    chain: List[str] = []

    for candidate in (normalize_locale(locale), normalize_locale(fallback)):
        if not candidate:
            continue
        if candidate not in chain:
            chain.append(candidate)
        if "-" in candidate:
            base = candidate.split("-")[0]
            if base not in chain:
                chain.append(base)

    return chain


_logger = logging.getLogger("craft.i18n")

#: (locale, key) pairs already reported missing, so each is logged once.
_reported_missing: set = set()
#: Slot in the request store that holds this request's translation bundles.
_BUNDLES_SLOT = "craft.i18n.bundles"


def clear_translation_cache() -> None:
    """Forget this request's bundles and the missing-key log."""
    from engine.container.application import Container

    store = Container.request_store()
    if store is not None:
        store.pop(_BUNDLES_SLOT, None)
    _reported_missing.clear()


def _fetch_bundle(app: Any, locale: str) -> Dict[str, str]:
    """Load every translation of `locale` in one query."""
    try:
        rows = app.make("db").statement(
            "SELECT key, value FROM translations WHERE locale = ?", [locale], read=True
        ).fetchall()
    except Exception:
        return {}  # DB offline or not yet migrated - fall back to config
    return {str(row["key"]): str(row["value"]) for row in rows if row["value"]}


def _fetch_one(app: Any, locale: str, key: str) -> Optional[str]:
    """Load one translation; used outside a request, where nothing is cached."""
    try:
        row = app.make("db").statement(
            "SELECT value FROM translations WHERE key = ? AND locale = ?", [key, locale], read=True
        ).fetchone()
    except Exception:
        return None  # DB offline or not yet migrated - fall back to config
    return str(row["value"]) if row is not None and row["value"] else None


def _lookup(app: Any, locale: str, key: str) -> Optional[str]:
    """Return the stored translation of `key`, one bundle query per request.

    The bundle lives in the request store, keyed by locale and tenant schema,
    so an edited row shows in the next request and no tenant ever reads a
    bundle loaded for another. Outside a request nothing is cached.
    """
    from engine.container.application import Container

    store = Container.request_store()
    if store is None:
        return _fetch_one(app, locale, key)
    bundles = store.setdefault(_BUNDLES_SLOT, {})
    slot = (locale, app.make("db").tenant_schema())
    if slot not in bundles:
        bundles[slot] = _fetch_bundle(app, locale)
    return bundles[slot].get(key)


def _report_missing(key: str, locale: str) -> None:
    """Count a missing translation and log it the first time it is seen.

    A key rendered as itself used to leave no trace, so untranslated copy
    shipped unnoticed. The counter is `i18n_missing_keys_total{locale,key}`.
    """
    from engine.support.metrics import registry

    registry.increment("i18n_missing_keys_total", locale=locale, key=key)
    if (locale, key) in _reported_missing:
        return
    _reported_missing.add((locale, key))
    _logger.warning(
        "i18n.missing_key key=%s locale=%s hint=add a row to `translations` for en, pt-BR and es",
        key, locale,
    )


def translate(key: str, locale: Optional[str] = None, **replacements: Any) -> str:
    """Translate `key`, falling back through the locale chain.

    Returns the key itself when nothing matches — a missing translation shows up
    as the key rather than an empty string or a crash.
    """
    from engine.container.application import Container

    text: Optional[str] = None

    active_locale = str(locale or current_locale.get() or "en")

    try:
        app = Container.getInstance()
        config = app.make("config")
        active = locale or current_locale.get() or config.get("app.APP_LOCALE") or "en"
        active_locale = str(active)
        fallback = config.get("app.APP_FALLBACK_LOCALE") or "en"

        for candidate in locale_chain(active, fallback):
            # 1. Database-backed dynamic translation (primary source of truth)
            stored = _lookup(app, candidate, key)
            if stored is not None:
                text = stored
                break

            # 2. Config-defined fallback translations (e.g. config/lang.py)
            value = config.get(f"lang.{candidate}.{key}")
            if value:
                text = str(value)
                break
    except Exception:
        text = None

    if text is None:
        _report_missing(key, active_locale)
    result = text if text is not None else key

    if replacements:
        from engine.support.icu import format_message

        result = format_message(result, replacements, locale=active_locale)

    return result


#: Short alias used throughout views and controllers.
__ = translate


__all__ = [
    "translate",
    "__",
    "locale_chain",
    "normalize_locale",
    "current_locale",
    "get_current_locale",
    "clear_translation_cache",
]
