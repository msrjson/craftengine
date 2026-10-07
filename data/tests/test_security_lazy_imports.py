"""Importing the engine must not drag the security package in (ADR 0002 step 0).

`engine/security/__init__.py` imported every subsystem eagerly, and
`engine/http/middleware.py` imported the firewall at module level, so a bare
`import engine` or an import of the middleware stack loaded the captcha - and
Pillow behind it - the firewall, the honeypot and PQC. The deferral is checked
through `sys.modules` in a subprocess: this session has already imported
everything, so an in-process assertion would prove nothing.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _modules_after(source: str, prefix: str) -> list[str]:
    """Import `source` in a fresh interpreter; report `sys.modules` by prefix."""
    probe = (
        "import sys; {source}; "
        "print(' '.join(sorted(m for m in sys.modules if m.startswith({prefix!r}))))"
    ).format(source=source, prefix=prefix)
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split()


def test_importing_the_engine_does_not_import_the_security_package():
    assert _modules_after("import engine", "engine.security") == []


def test_importing_the_middleware_stack_does_not_import_the_security_package():
    assert _modules_after("import engine.http.middleware", "engine.security") == []


def test_importing_the_security_package_loads_no_subsystem():
    """`import engine.security` alone must not name any subsystem."""
    assert _modules_after("import engine.security", "engine.security.") == []


def test_the_lazy_names_stay_importable():
    """The deferral must not make a public name disappear."""
    from engine.security import Captcha, Firewall, FirewallMiddleware, HoneypotService, PQC

    assert all(obj is not None for obj in (Captcha, Firewall, FirewallMiddleware, HoneypotService, PQC))


def test_the_firewall_middleware_stays_on_the_middleware_module():
    """`from engine.http.middleware import FirewallMiddleware` keeps working."""
    from engine.http.middleware import FirewallMiddleware
    from engine.security.firewall import FirewallMiddleware as Canonical

    assert FirewallMiddleware is Canonical
