"""Typed refusals of the extension model.

Every refusal carries a stable machine `code` and a `message_key` the
presentation layer translates; the engine never renders a sentence for a user.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations


class ExtensionError(RuntimeError):
    """An extension operation the engine refuses.

    Args:
        code: Machine code naming the refusal, e.g. `EXTENSION_DEPENDENCY_MISSING`.
        slug: The extension the refusal is about.
        detail: Engineer-facing context (a path, a version, another slug);
            never shown to a user.
    """

    #: A refusal is a request the engine understood and declined.
    status_code = 422

    def __init__(self, code: str, slug: str = "", detail: str = "") -> None:
        super().__init__(code, slug, detail)
        self.code = code
        self.slug = slug
        self.detail = detail
        self.message_key = "extension.error." + code.lower()
        self.params = {"slug": slug, "detail": detail}

    def __str__(self) -> str:
        return " ".join(part for part in (self.code, self.slug, self.detail) if part)


class ExtensionUnavailableError(ExtensionError):
    """The extension exists but cannot serve right now (inactive or tripped).

    Args:
        slug: The extension that cannot serve.
        code: `MODULE_DISABLED` (404) or `EXTENSION_UNAVAILABLE` (503).
    """

    def __init__(self, slug: str, code: str = "EXTENSION_UNAVAILABLE") -> None:
        super().__init__(code, slug)
        self.status_code = 404 if code == "MODULE_DISABLED" else 503
        self.message_key = "module.error.disabled" if code == "MODULE_DISABLED" else "extension.error.unavailable"


__all__ = ["ExtensionError", "ExtensionUnavailableError"]
