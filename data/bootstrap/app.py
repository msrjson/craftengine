"""Application bootstrap - creates and boots the Craft application."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import engine  # noqa: F401  installs the `craft.*` import alias


from craft.container.application import Application
from craft.facades.base import Facade


def create_app() -> Application:
    """Create and bootstrap the Craft application."""
    app = Application(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Load config
    app.register_config()

    # Register framework service providers
    from craft.providers.service_providers import (
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
        PQCServiceProvider,
        CaptchaServiceProvider,
        FirewallServiceProvider,
        HoneypotServiceProvider,
        AntiSpamServiceProvider,
        VaultServiceProvider,
        SignerServiceProvider,
        MediaServiceProvider,
        AIServiceProvider,
        AgentServiceProvider,
        StorageServiceProvider,
        MailServiceProvider,
        FrameworkSubsystemsServiceProvider,
    )

    app.register_provider(DatabaseServiceProvider)
    app.register_provider(PostgresServiceProvider)
    app.register_provider(RouterServiceProvider)
    app.register_provider(ViewServiceProvider)
    app.register_provider(AuthServiceProvider)
    app.register_provider(EventServiceProvider)
    app.register_provider(QueueServiceProvider)
    app.register_provider(LoggingServiceProvider)
    app.register_provider(CacheServiceProvider)
    app.register_provider(MigratorServiceProvider)
    app.register_provider(ExceptionServiceProvider)
    app.register_provider(FirewallServiceProvider)
    app.register_provider(HoneypotServiceProvider)
    app.register_provider(AntiSpamServiceProvider)
    app.register_provider(MediaServiceProvider)
    app.register_provider(AIServiceProvider)
    app.register_provider(AgentServiceProvider)
    app.register_provider(StorageServiceProvider)
    app.register_provider(MailServiceProvider)

    # `config/framework.py` ships these as feature flags, but nothing read
    # them: both providers registered unconditionally, so setting
    # PQC_SECURITY_ENABLED=false or CAPTCHA_ENABLED=false changed nothing. A
    # switch that does not switch is worse than no switch.
    config = app.make("config")
    if config.get("framework.PQC_SECURITY_ENABLED", True):
        app.register_provider(PQCServiceProvider)
    if config.get("framework.CAPTCHA_ENABLED", True):
        app.register_provider(CaptchaServiceProvider)
    # Unconditional and lazy: registering costs nothing (the Vault/Signer
    # instance is only built, and APP_KEY only read, on first use).
    app.register_provider(VaultServiceProvider)
    app.register_provider(SignerServiceProvider)


    app.register_provider(FrameworkSubsystemsServiceProvider)

    # Register application service providers
    from app.Providers.AppServiceProvider import AppServiceProvider
    from app.Providers.EventServiceProvider import EventServiceProvider as AppEventServiceProvider
    from app.Providers.RouteServiceProvider import RouteServiceProvider

    app.register_provider(AppServiceProvider)
    app.register_provider(AppEventServiceProvider)
    app.register_provider(RouteServiceProvider)

    # Wire facades to the app before booting providers
    Facade._app = app

    # Boot all providers
    app.boot()

    return app


# Create the app instance
app = create_app()

# Build the ASGI application
from craft.http.kernel import Kernel

from craft.http.middleware import (
    Authenticate,
    RequestContext,
    ScopeTenant,
    SecurityHeaders,
    SetLocale,
    StartSession,
    VerifyCsrfToken,
)

kernel = Kernel(app)

# Order matters: the session must exist before the locale can be remembered in
# it, before CSRF verification, and before the user is resolved from it.
# SecurityHeaders goes early so every response - including error responses
# rendered inside StartSession - carries the baseline headers.
# RequestContext goes first of all: everything after it, a session failure and
# a CSRF rejection included, should carry the identifier of the request that
# caused it and land in the latency histogram.
_global_middleware = [
    RequestContext,
    SecurityHeaders,
    StartSession,
    SetLocale,
    VerifyCsrfToken,
    Authenticate,
]

# `MULTI_TENANCY_ENABLED` used to be decorative: TenantMiddleware ran on every
# request whatever the flag said. A single-tenant app now stops paying for the
# per-request tenant resolution it never wanted.
#
# The strategy picks *which* middleware, and both refuse to serve a tenant
# request the database cannot isolate rather than degrading to shared tables.
# `MULTI_TENANCY_STRATEGY` used to appear only in error messages and docs while
# nothing read it - the instruction "switch to MULTI_TENANCY_STRATEGY=rls" had
# no effect at all.
_config = app.make("config")
if _config.get("framework.MULTI_TENANCY_ENABLED", False):
    _strategy = str(_config.get("framework.MULTI_TENANCY_STRATEGY", "rls")).lower()
    if _strategy == "rls":
        _global_middleware.append(ScopeTenant)
    elif _strategy == "schema":
        # Imported here, not at module scope: the schema strategy needs
        # PostgreSQL, and a project that never selects it never loads it.
        from craft.http.tenant_schema import TenantMiddleware

        _global_middleware.append(TenantMiddleware)
    else:
        raise ValueError(
            f"MULTI_TENANCY_STRATEGY is {_strategy!r}; expected 'rls' or 'schema'. "
            f"An unrecognised value here would silently serve every tenant from "
            f"the same tables."
        )

kernel.with_middleware(*_global_middleware)

# Record the framework's own routes - the health probes, the metrics scrape,
# the MSR manifest, the static-asset mount - on the router, so `route:list`
# and the panel's route audit account for every path that answers. Each is
# governed by its own configuration flag and none of them is on by default.
kernel.register_engine_routes()

asgi_app = kernel.get_starlette_app()
