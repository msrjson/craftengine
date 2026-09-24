"""The schema strategy for multi-tenancy: one PostgreSQL schema per tenant.

Selected with `MULTI_TENANCY_STRATEGY=schema`. The alternative, and the better
default for most applications, is row-level security - `ScopeTenant` in
`engine/http/middleware.py`, selected with `MULTI_TENANCY_STRATEGY=rls` - which
migrates once instead of once per tenant, keeps DDL off the request path, and
is enforced by the database rather than by every query remembering to scope
itself. The schema strategy remains the right answer for a handful of tenants
that need physical separation.

This lived in the demo application as `app/Http/Middleware/TenantMiddleware.py`
although nothing in it belonged to the demo. A documented framework capability
implemented inside one sample app is the same inverted dependency as the user
model was: a project generated without that app lost the strategy entirely.

Contract with the project's user model: a request is scoped to a tenant schema
when the authenticated user's `type` attribute is `"tenant"`. A project that
adopts this strategy gives its user model that column. Any other user, and any
unauthenticated request, runs against the default schema.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

from engine.facades import Auth, DB
from engine.http.middleware import Middleware

#: The user `type` value that marks a request as belonging to a tenant.
TENANT_USER_TYPE = "tenant"

#: Characters kept in a schema name; everything else becomes an underscore.
_UNSAFE_SCHEMA_CHARACTERS = re.compile(r"[^a-zA-Z0-9_]")

#: Log once per process rather than once per request: a tenant application
#: under load would otherwise write the same line thousands of times a second.
_logged_isolation_refusal = False


class TenantIsolationUnavailable(RuntimeError):
    """Raised when the database driver cannot isolate tenant schemas.

    A developer-facing configuration failure, so it carries a stable code and
    the offending driver rather than a rendered sentence.

    Attributes:
        code: Stable machine code for this failure.
        status_code: HTTP status the exception handler answers with.
        driver: The database driver that cannot provide schema isolation.
    """

    code: str = "TENANT_ISOLATION_UNAVAILABLE"
    status_code: int = 500

    def __init__(self, driver: Optional[str]) -> None:
        super().__init__(self.code)
        self.driver = driver


def schema_name_for(user_id: Any) -> str:
    """Return the schema a tenant user's data lives in.

    Args:
        user_id: The tenant user's primary key.

    Returns:
        A schema name safe to place inside a quoted identifier.
    """
    return "tenant_" + _UNSAFE_SCHEMA_CHARACTERS.sub("_", str(user_id).lower())


class TenantMiddleware(Middleware):
    """Scope the connection to the authenticated tenant's schema.

    Schema isolation needs PostgreSQL. This used to warn once and keep serving
    on SQLite and MySQL, where creating a tenant schema is a no-op and every
    tenant therefore shares one set of tables. A warning is the wrong response
    to that: the request proceeds, the data crosses the boundary, and the only
    trace is a log line read afterwards. It refuses instead.
    """

    def handle(self, request: Any, next_callable: Callable[[Any], Any]) -> Any:
        """Route the request to its tenant's schema, or the default one.

        Args:
            request: The incoming request.
            next_callable: The rest of the middleware pipeline.

        Returns:
            The response produced by the rest of the pipeline.

        Raises:
            TenantIsolationUnavailable: If the request belongs to a tenant and
                the driver cannot isolate schemas.
        """
        user = Auth.user()
        if user is None or user.get_attribute("type") != TENANT_USER_TYPE:
            DB.set_tenant_schema(None)
            return next_callable(request)

        self._assert_isolation_is_real()
        schema_name = schema_name_for(user.get_attribute("id"))
        DB.set_tenant_schema(schema_name)
        DB.ensure_tenant_schema(schema_name, user)
        return next_callable(request)

    @staticmethod
    def _assert_isolation_is_real() -> None:
        """Refuse to serve a tenant request the database will not isolate.

        Raises:
            TenantIsolationUnavailable: If the driver is not PostgreSQL.
        """
        driver = getattr(DB, "driver", None)
        if driver == "postgresql":
            return

        global _logged_isolation_refusal
        if not _logged_isolation_refusal:
            _logged_isolation_refusal = True
            logging.getLogger("craft").error(
                "tenant_isolation_refused",
                extra={"driver": driver, "remedy": "use_postgresql_or_rls_strategy"},
            )
        raise TenantIsolationUnavailable(driver)
