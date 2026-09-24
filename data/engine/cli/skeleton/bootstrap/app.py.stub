"""Application bootstrap - creates and boots the Craft application."""

from __future__ import annotations

import os

import engine  # noqa: F401  installs the `craft.*` import alias

from craft.container.application import Application
from craft.facades.base import Facade


def create_app() -> Application:
    """Create and bootstrap the Craft application.

    Returns:
        The booted application container.
    """
    app = Application(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    app.register_config()

    # Every engine provider, from the single list in the engine. Writing the
    # list out here is how this bootstrap once fell behind and left the
    # generated login screen without the anti-spam it depends on.
    from craft.providers.engine_providers import register_engine_providers

    register_engine_providers(app)

    from app.Providers.AppServiceProvider import AppServiceProvider
    from app.Providers.EventServiceProvider import EventServiceProvider as AppEventServiceProvider
    from app.Providers.RouteServiceProvider import RouteServiceProvider

    app.register_provider(AppServiceProvider)
    app.register_provider(AppEventServiceProvider)
    app.register_provider(RouteServiceProvider)

    Facade._app = app
    app.boot()
    return app


app = create_app()

from craft.http.kernel import Kernel  # noqa: E402
from craft.http.middleware import (  # noqa: E402
    Authenticate,
    RequestContext,
    SecurityHeaders,
    SetLocale,
    StartSession,
    VerifyCsrfToken,
)

kernel = Kernel(app)

# Order matters: the session must exist before the locale can be remembered in
# it, before CSRF verification, and before the user is resolved from it.
# SecurityHeaders goes early so every response, including error responses
# raised further down, carries them.
_global_middleware = [
    RequestContext,
    SecurityHeaders,
    StartSession,
    SetLocale,
    VerifyCsrfToken,
    Authenticate,
]

# Multi-tenancy is opt-in, and each middleware is imported inside its branch so
# a single-tenant application loads neither.
#
#   rls     row-level security, enforced by the database. The default, and the
#           right choice for most applications.
#   schema  one PostgreSQL schema per tenant, for the few that need physical
#           separation. Scopes users whose `type` attribute is "tenant".
_config = app.make("config")
if _config.get("framework.MULTI_TENANCY_ENABLED", False):
    _strategy = str(_config.get("framework.MULTI_TENANCY_STRATEGY", "rls")).lower()
    if _strategy == "rls":
        from craft.http.middleware import ScopeTenant

        _global_middleware.append(ScopeTenant)
    elif _strategy == "schema":
        from craft.http.tenant_schema import TenantMiddleware

        _global_middleware.append(TenantMiddleware)
    else:
        # Refuse rather than degrade: an unrecognised strategy that fell
        # through would serve every tenant from the same tables.
        raise ValueError(_strategy)

kernel.with_middleware(*_global_middleware)

# Record the framework's own routes - the health probes, the metrics scrape,
# the MSR manifest, the static-asset mount - on the router, so `route:list`
# and the panel's route audit account for every path that answers. Each is
# governed by its own configuration flag and none of them is on by default.
kernel.register_engine_routes()

asgi_app = kernel.get_starlette_app()
