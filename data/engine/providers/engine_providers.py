"""The single list of service providers the engine needs to run.

Every application bootstrap registers the engine's providers before its own.
That list used to be written out by hand in each bootstrap, and the copies
drifted: the bootstrap `craft new` generated registered fourteen providers
where this repository's registered twenty-three. The missing ones included
AntiSpam and Honeypot, which the login screen `make:auth` generates depends
on, so every generated login answered a 500 - and NR-06 requires both on any
public form, so the fix is not to drop them from the screen.

A bootstrap now calls `register_engine_providers(app)`, and the list lives
here, once. Adding an engine provider is a change to this file only; no
generated project can fall behind it.
"""

from __future__ import annotations

from typing import Any


def register_engine_providers(app: Any) -> None:
    """Register every engine service provider on an application.

    Order matters: the database and router come first because later providers
    resolve them during registration, and FrameworkSubsystemsServiceProvider
    comes last because its boot step wires plugins against everything else.

    Two providers are governed by feature flags in `config/framework.py`, so
    configuration must already be loaded when this is called.

    Args:
        app: The application container, with configuration registered.
    """
    from engine.providers.service_providers import (
        AgentServiceProvider,
        AIServiceProvider,
        AntiSpamServiceProvider,
        AuthServiceProvider,
        CacheServiceProvider,
        CaptchaServiceProvider,
        DatabaseServiceProvider,
        EventServiceProvider,
        ExceptionServiceProvider,
        FirewallServiceProvider,
        FrameworkSubsystemsServiceProvider,
        HoneypotServiceProvider,
        LoggingServiceProvider,
        MailServiceProvider,
        MediaServiceProvider,
        MigratorServiceProvider,
        PostgresServiceProvider,
        PQCServiceProvider,
        QueueServiceProvider,
        RouterServiceProvider,
        SignerServiceProvider,
        StorageServiceProvider,
        VaultServiceProvider,
        ViewServiceProvider,
    )

    for provider in (
        DatabaseServiceProvider,
        PostgresServiceProvider,
        RouterServiceProvider,
        ViewServiceProvider,
        AuthServiceProvider,
        EventServiceProvider,
        QueueServiceProvider,
        LoggingServiceProvider,
        CacheServiceProvider,
        MigratorServiceProvider,
        ExceptionServiceProvider,
        FirewallServiceProvider,
        HoneypotServiceProvider,
        AntiSpamServiceProvider,
        MediaServiceProvider,
        AIServiceProvider,
        AgentServiceProvider,
        StorageServiceProvider,
        MailServiceProvider,
    ):
        app.register_provider(provider)

    # Feature flags that genuinely switch: each provider registers only when
    # its flag is on.
    config = app.make("config")
    if config.get("framework.PQC_SECURITY_ENABLED", True):
        app.register_provider(PQCServiceProvider)
    if config.get("framework.CAPTCHA_ENABLED", True):
        app.register_provider(CaptchaServiceProvider)

    # Unconditional and lazy: registering costs nothing, because the instance
    # is built, and APP_KEY read, only on first use.
    app.register_provider(VaultServiceProvider)
    app.register_provider(SignerServiceProvider)

    app.register_provider(FrameworkSubsystemsServiceProvider)
