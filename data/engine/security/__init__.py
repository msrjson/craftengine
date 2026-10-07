"""Security Subsystem for Craft Framework.

The public names are re-exported lazily (PEP 562): `import engine.security`
does not load the captcha - and Pillow behind it - the firewall, the honeypot
or PQC until one of them is actually used. This keeps the security package off
the import path of the framework and of a bare HTTP application (ADR 0002,
step 0).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from engine.security.captcha import Captcha
    from engine.security.firewall import Firewall, FirewallMiddleware
    from engine.security.honeypot import HoneypotService
    from engine.security.pqc import PQC

#: Public name -> the module that defines it, resolved on first attribute
#: access instead of at package import.
_LAZY_EXPORTS = {
    "Captcha": "engine.security.captcha",
    "Firewall": "engine.security.firewall",
    "FirewallMiddleware": "engine.security.firewall",
    "HoneypotService": "engine.security.honeypot",
    "PQC": "engine.security.pqc",
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str):
    """Import and cache the submodule behind a public name on first use."""
    try:
        module_name = _LAZY_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_EXPORTS})
