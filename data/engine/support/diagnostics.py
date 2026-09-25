"""Developer diagnostics: one catalog of messages for engine misconfiguration.

When the engine refuses something a developer or an agent wired wrongly, it
raises with a stable code and the values involved, and this catalog turns them
into the sentence that says what is wrong and what to change. These messages
are for engineers - exceptions, logs, console output - never for an
application's end users, so they are English templates with named
placeholders rather than translation keys.

Keeping them in one place is what lets a message change without hunting through
the engine, and what lets `craft doctor` and the runtime say the same thing.

Category: Core Framework (Support).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import difflib
from typing import Any, Iterable

CATALOG = {
    "CONFIG_KEY_MISSING": (
        "Configuration key {key} does not exist. Closest: {closest}. "
        "Keys are <file>.<MODULE_ATTRIBUTE>, e.g. app.APP_DEBUG."
    ),
    "CONTAINER_NOT_BOOTED": (
        "No application has booted: this is the empty fallback container, which is what a "
        "facade used at import time, before bootstrap/app.py runs, resolves from."
    ),
    "CONTAINER_UNBOUND": "Target [{key}] is not bound in container and cannot be resolved.",
    "CONTAINER_CLOSEST": "Closest bound keys: {closest}.",
    "CONTAINER_PARAMETER_UNRESOLVABLE": (
        "Cannot resolve parameter [{parameter}: {annotation}] for class [{owner}]. "
        "Bind it in a service provider or give it a default."
    ),
    "FACADE_IMPORT_ELSEWHERE": "craft.facades has no {name}; use {location}.",
    "FACADE_IMPORT_UNKNOWN": "craft.facades has no {name}. Closest: {closest}. Facades: {facades}.",
    "FACADE_METHOD_MISSING": (
        "{facade} facade (-> {service}, container key {accessor}) has no method {name}. "
        "Closest: {closest}{signature}. Public methods: {public}."
    ),
    "FORGE_UNKNOWN_DIRECTIVE": (
        "Unknown Forge directive @{name}. {detail}Supported: {supported}. "
        "Plain Jinja tags ({{% ... %}}) also work."
    ),
    "FORGE_INCLUDE_WITH_DATA": "@include takes only a view name; set variables before it instead of passing data. ",
    "IDENTITY_MODEL_IMPORT_FAILED": (
        "{code}: the {kind} model path {path} does not import ({cause}). "
        "Fix the path in config/auth.py or the module it names."
    ),
    "IDENTITY_MODEL_NOT_SET": (
        "{code}: no {kind} model is configured ({key} is empty). "
        "Run {remedy} or point that key at your model class."
    ),
    "IDENTITY_MODEL_UNKNOWN_KIND": "{code}: unknown identity model kind {kind}.",
    "MIDDLEWARE_TAKES_NO_PARAMETER": (
        "{middleware} takes no route parameter, but got :{param}. Remove it. "
        "Authentication by API token is the api alias, not auth:api."
    ),
    "MIDDLEWARE_TOO_MANY_PARAMETERS": (
        "{middleware} takes {count} route parameter(s) ({names}), got :{param}. To require any of "
        "several roles or permissions, check them in a Gate or policy instead of one alias."
    ),
    "MIDDLEWARE_PARAMETER_NOT_INTEGER": "{middleware} parameter {name} must be an integer, got {value}.",
    "MODEL_ATTRIBUTE_MISSING": (
        "{model} object has no attribute {name}. Closest: {closest}. Loaded columns: {columns}."
    ),
    "ROUTE_ACTION_NOT_FOUND": (
        "{controller} has no method {name}. Closest: {closest}. Public methods: {public}."
    ),
    "ROUTE_ACTION_RETURNED_NONE": (
        "The route action {action} returned None. Return a response, a View, a dict or list "
        "(sent as JSON) or a string (sent as HTML) - usually a missing return."
    ),
    "VALIDATION_RULE_UNKNOWN": (
        "Unknown validation rule [{rule}] on field [{field}]. Closest: {closest}."
    ),
    "VALIDATION_RULE_NEEDS_ARGUMENT": (
        "Validation rule {rule} on field [{field}] needs {count} argument(s), "
        "e.g. {rule}:<value>; without them it would accept anything."
    ),
    "USER_MODEL_NOT_AUTHORIZABLE": (
        "The {alias}: route middleware calls {model}.{method}(), which does not exist. "
        "Mix craft.auth.models.AuthorizableMixin into {model}."
    ),
}


def describe(message_code: str, /, **params: Any) -> str:
    """Return the catalog message for `message_code` with `params` filled in.

    Args:
        message_code: A key of `CATALOG`. Positional-only, so a message may
            itself name a `code` parameter.
        **params: The values the message names.

    Returns:
        The developer-facing message.
    """
    return CATALOG[message_code].format(**params)


def closest(name: str, candidates: Iterable[str], limit: int = 1) -> str:
    """Return the candidates closest to `name`, comma-separated, or "none".

    Args:
        name: What was asked for.
        candidates: What exists.
        limit: How many suggestions to return.

    Returns:
        The suggestions, or "none" when nothing is close.
    """
    matches = difflib.get_close_matches(str(name), [str(c) for c in candidates], n=limit)
    return ", ".join(matches) if matches else "none"


__all__ = ["CATALOG", "closest", "describe"]
