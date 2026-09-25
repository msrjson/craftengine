"""Middleware for Craft Framework.

Middleware is synchronous: `handle(request, next_callable)` returns a response.
The kernel composes the stack in registration order, so `StartSession` must come
first - `VerifyCsrfToken` and `Authenticate` both read from the session.

Category: Core Framework (HTTP).
Relations:
  - Registered by `bootstrap/app.py` via `kernel.with_middleware(...)`
    (`engine/http/kernel.py`); route-level aliases resolved by
    `engine/http/router.py`.
References:
  - Guide: `documentation/security.md`, `documentation/sessions.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import fnmatch
import logging
import secrets
from typing import Any, Callable, List, Optional, Tuple


class Middleware:
    """Base middleware - pass the request through untouched."""

    #: Constructor parameters a route alias may set, in order: `"throttle:30,60"`
    #: fills `max_attempts` then `decay_seconds`, each converted to the type of
    #: its default. An empty tuple means the alias takes no parameter, and one
    #: given is refused at boot. `None` (the default for classes outside the
    #: engine) keeps the original rule: the value goes, as a string, to the
    #: first constructor parameter after `app`.
    alias_parameters: Optional[Tuple[str, ...]] = None

    def handle(self, request: Any, next_callable: Callable) -> Any:
        return next_callable(request)


def _container(app: Any = None) -> Any:
    if app is not None:
        return app
    from engine.container.application import Container

    return Container.getInstance()


def _as_starlette(response: Any) -> Any:
    """Normalise a framework response into a Starlette response, if possible."""
    from starlette.responses import Response as StarletteResponse

    if isinstance(response, StarletteResponse):
        return response
    if hasattr(response, "to_starlette"):
        return response.to_starlette()
    return None


class RequestContext(Middleware):
    """Give the request an identity, then time it and count it.

    First in the stack, and deliberately so: everything after it - a session
    failure, a CSRF rejection, an exception rendered before any controller runs
    - should be attributable to a request, and a request that produced no log
    line still belongs in the latency histogram.

    An inbound `X-Request-ID` is echoed so a trace survives a hop between
    services, but only after validation: the header is attacker-controlled, and
    an unbounded value bloats every log line while a newline in one forges
    entries outright.
    """

    HEADER = "X-Request-ID"

    def __init__(self, app: Any = None):
        self.app = app

    def handle(self, request: Any, next_callable: Callable) -> Any:
        import time

        from engine.support import context
        from engine.support.metrics import registry

        # Exceptions are counted by the exception handler, not here: an inner
        # middleware may render a fault into a response before it reaches this
        # frame, and counting in both places would count some of them twice.
        identifier = context.sanitize_request_id(
            self._header(request, self.HEADER)
        ) or context.new_request_id()

        method = str(getattr(request, "method", "") or "GET").upper()
        route = self._route(request)
        started = time.monotonic()

        with context.bind(request_id=identifier, method=method, path=route):
            status = 500
            try:
                response = next_callable(request)
                starlette_response = _as_starlette(response)
                if starlette_response is not None:
                    status = starlette_response.status_code
                    starlette_response.headers.setdefault(self.HEADER, identifier)
                    response = starlette_response
                else:
                    status = 200
                return response
            finally:
                duration = time.monotonic() - started
                registry.observe(
                    "craft_request_duration_seconds", duration, method=method, route=route
                )
                registry.increment(
                    "craft_requests_total", method=method, route=route, status=str(status)
                )

    def _header(self, request: Any, name: str) -> Optional[str]:
        try:
            return request.headers.get(name.lower())
        except Exception:
            return None

    def _route(self, request: Any) -> str:
        """The matched route pattern, never the raw path.

        `/posts/{id}` is one series; `/posts/1`, `/posts/2` and the rest are as
        many series as there are posts, which is how a metrics store is killed
        by the thing that was meant to observe it. The kernel stamps the
        pattern on the request when it builds the endpoint.
        """
        pattern = getattr(request, "route_uri", None)
        return pattern if isinstance(pattern, str) and pattern else "unmatched"


class StartSession(Middleware):
    """Load the session before the request, persist it after."""

    alias_parameters = ()

    COOKIE_NAME = "craft_session"

    def __init__(self, app: Any = None):
        self.app = app
        self._store = None

    def store(self) -> Any:
        if self._store is None:
            from engine.http.session import make_store

            self._store = make_store(_container(self.app))
        return self._store

    def _config(self, key: str, default: Any) -> Any:
        try:
            return _container(self.app).make("config").get(key, default)
        except Exception:
            return default

    def handle(self, request: Any, next_callable: Callable) -> Any:
        from engine.http.session import current_session

        store = self.store()
        cookie_name = self._config("session.cookie", self.COOKIE_NAME)

        session = store.load(request.cookies.get(cookie_name))
        request.state.session = session
        # Publish it so view helpers (`@csrf`) can reach it without the request.
        token = current_session.set(session)

        try:
            # Exception-driven responses (validation redirect, CSRF 419) must
            # still carry the session writes and Set-Cookie, so render them
            # here - the kernel's outer handler remains as a fallback for
            # anything raised above this middleware.
            try:
                response = next_callable(request)
            except Exception as exc:
                from engine.http.kernel import render_exception

                response = render_exception(_container(self.app), request, exc)
        finally:
            current_session.reset(token)

        value = store.save(request.state.session)
        starlette_response = _as_starlette(response)
        if starlette_response is None:
            return response

        starlette_response.set_cookie(
            cookie_name,
            value,
            max_age=int(self._config("session.lifetime", 7200)),
            httponly=True,
            samesite=self._config("session.same_site", "lax"),
            secure=bool(self._config("session.secure", False)),
            path="/",
        )
        return starlette_response


class SetLocale(Middleware):
    """Resolve the active locale for the request.

    Order of precedence: an explicit `?lang=` query parameter, then whatever the
    visitor chose earlier (held in the session), then `Accept-Language`, then the
    configured default. The chosen tag is normalised to BCP 47 and persisted, so
    a language switch survives the next navigation.
    """

    QUERY_KEY = "lang"
    SESSION_KEY = "locale"

    def __init__(self, app: Any = None, supported: Optional[List[str]] = None):
        self.app = app
        self._supported = supported
        self._default: Optional[str] = None

    def supported(self) -> List[str]:
        if self._supported is not None:
            return self._supported
        try:
            configured = _container(self.app).make("config").get("app.APP_LOCALES")
        except Exception:
            configured = None
        return list(configured or ["en", "pt-BR", "es"])

    def _from_header(self, request: Any) -> Optional[str]:
        from engine.support.translation import normalize_locale

        header = request.headers.get("accept-language", "")
        supported = [normalize_locale(s) for s in self.supported()]

        for chunk in header.split(","):
            match = self._match(normalize_locale(chunk.split(";")[0].strip()), supported)
            if match:
                return match
        return None

    @staticmethod
    def _match(tag: Optional[str], supported: List[str]) -> Optional[str]:
        """Return the offered locale closest to `tag`, or None.

        An exact tag wins, then its base language (`pt-PT` -> `pt`), then the
        first offered variant of the same language (`pt` -> `pt-BR`), so a
        visitor asking for Portuguese is not served English just because only
        the Brazilian variant is offered.
        """
        if not tag:
            return None
        if tag in supported:
            return tag
        base = tag.split("-")[0]
        if base in supported:
            return base
        return next((s for s in supported if s.split("-")[0] == base), None)

    def default(self) -> str:
        """The configured locale, captured before anything overwrites it."""
        if getattr(self, "_default", None) is None:
            try:
                config = _container(self.app).make("config")
                self._default = str(
                    config.get("app.APP_LOCALE") or config.get("app.app_locale") or "en"
                )
            except Exception:
                self._default = "en"
        return self._default

    def resolve(self, request: Any, session: Any = None) -> str:
        """Pick the locale for this request, most specific source first."""
        from engine.support.translation import normalize_locale

        supported = [normalize_locale(s) for s in self.supported()]

        requested = self._match(normalize_locale(request.query_params.get(self.QUERY_KEY)), supported)
        if requested:
            if session is not None:
                session.put(self.SESSION_KEY, requested)
            return requested

        stored = normalize_locale(session.get(self.SESSION_KEY)) if session else None
        if stored in supported:
            return stored

        # Always land on a concrete value. Leaving it unset made the locale
        # sticky across visitors, because the previous request's choice was
        # still in place.
        return self._from_header(request) or self.default()

    def handle(self, request: Any, next_callable: Callable) -> Any:
        from engine.support.translation import current_locale

        session = request.session() if getattr(request, "has_session", lambda: False)() else None
        locale = self.resolve(request, session)

        request.state.locale = locale
        token = current_locale.set(locale)
        try:
            return next_callable(request)
        finally:
            current_locale.reset(token)


class VerifyCsrfToken(Middleware):
    """Reject state-changing requests that carry no valid CSRF token."""

    alias_parameters = ()

    #: Methods that are safe by definition and never checked.
    READ_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")

    #: URI patterns exempt from verification (fnmatch syntax).
    except_paths: List[str] = ["api/*"]

    def __init__(self, app: Any = None, except_paths: Optional[List[str]] = None):
        self.app = app
        if except_paths is not None:
            self.except_paths = list(except_paths)

    def _enabled(self) -> bool:
        try:
            return bool(_container(self.app).make("config").get("session.csrf", True))
        except Exception:
            return True

    def is_exempt(self, path: str) -> bool:
        normalised = path.lstrip("/")
        return any(
            fnmatch.fnmatch(normalised, pattern.lstrip("/")) for pattern in self.except_paths
        )

    def token_from(self, request: Any) -> Optional[str]:
        header = request.headers.get("x-csrf-token") or request.headers.get("x-xsrf-token")
        if header:
            return header
        # Only the parsed body counts - a token in the query string could be
        # planted by a crafted cross-site link.
        if hasattr(request, "post"):
            return request.post("_token")
        return None

    def _expected_origin(self, request: Any) -> str:
        """The origin this request must have come from: `scheme://host[:port]`.

        `app.APP_URL` when configured (the deployment's own canonical
        address); falls back to the request's own `Host` header for a
        same-origin check when it is not.
        """
        try:
            app_url = str(_container(self.app).make("config").get("app.APP_URL", "") or "")
        except Exception:
            app_url = ""
        if app_url:
            return app_url.rstrip("/")
        host = str(getattr(request, "header", lambda _n: "")("host") or "")
        scheme = "https" if getattr(request, "is_secure", lambda: False)() else "http"
        return f"{scheme}://{host}" if host else ""

    def origin_is_trusted(self, request: Any) -> bool:
        """Extra defense-in-depth layer, alongside the token check.

        The token proves the request carries a value only same-origin
        JavaScript could have read (from the DOM or a cookie the same-origin
        policy protects); `Origin`/`Referer` proves the *browser* itself
        believes the request came from this origin - a second, independent
        signal an attacker who somehow obtained a valid token (an XSS
        elsewhere on the same origin, say) still cannot forge, because the
        browser sets these headers itself and refuses script control over
        them. Absent both headers (some legitimate older clients, or a
        same-origin `fetch` under some privacy settings) this does not fail
        the request on its own - only a header that is PRESENT and WRONG
        does. The token check is still the primary defense.
        """
        origin = request.headers.get("origin") or request.headers.get("referer")
        if not origin:
            return True
        expected = self._expected_origin(request)
        if not expected:
            return True
        from urllib.parse import urlsplit

        origin_root = urlsplit(origin)
        expected_root = urlsplit(expected)
        return (origin_root.scheme, origin_root.netloc) == (expected_root.scheme, expected_root.netloc)

    def handle(self, request: Any, next_callable: Callable) -> Any:
        if (
            request.method.upper() in self.READ_METHODS
            or not self._enabled()
            or self.is_exempt(request.url.path)
        ):
            return next_callable(request)

        if not getattr(request, "has_session", lambda: False)():
            # Passing silently here would disable CSRF protection whenever
            # StartSession is missing from the stack - fail loudly instead.
            raise RuntimeError(
                "VerifyCsrfToken requires a session. Add StartSession before it "
                "in the middleware stack in bootstrap/app.py."
            )

        if not self.origin_is_trusted(request):
            from engine.exceptions.handler import CraftException

            error = CraftException("Cross-origin request rejected.")
            error.status_code = 403
            raise error

        expected = request.session().token()
        provided = self.token_from(request) or ""

        if not secrets.compare_digest(str(expected), str(provided)):
            from engine.exceptions.handler import CraftException

            error = CraftException("CSRF token mismatch.")
            error.status_code = 419  # the framework's "page expired"
            raise error

        return next_callable(request)


class Authenticate(Middleware):
    """Resolve the session's user onto the auth manager."""

    SESSION_KEY = "auth_user_id"

    def __init__(self, app: Any = None):
        self.app = app

    def handle(self, request: Any, next_callable: Callable) -> Any:
        auth = _container(self.app).make("auth")

        # The auth manager is a singleton, so a user resolved on a previous
        # request must not leak into this one. `reset()` clears memory without
        # ending the session - `logout()` here would erase the very key we are
        # about to read.
        auth.reset()

        if getattr(request, "has_session", lambda: False)():
            session = request.session()
            auth.set_session(session)
            user_id = session.get(self.SESSION_KEY)
            if user_id is not None:
                user = auth.user_model().find(user_id)
                if user is None:
                    # The user was deleted while the session lived on.
                    session.forget(self.SESSION_KEY)
                else:
                    auth.set_user(user)
        else:
            auth.set_session(None)

        return next_callable(request)


class ScopeTenant(Middleware):
    """Bind the request's tenant, so row-level security can isolate it.

    Register it after `Authenticate` - it may resolve the tenant from the
    authenticated user - and before anything that reads data.

    It refuses to run on a driver without row-level security rather than
    warning. The schema-per-tenant middleware this replaces logged a line and
    kept serving requests against shared tables, which is a data-isolation
    failure wearing the costume of a working feature. `require_isolation=False`
    is the explicit opt-out for a single-tenant deployment that still wants the
    binding, and for the test-suite.
    """

    def __init__(self, app: Any = None, require_isolation: bool = True):
        self.app = app
        self.require_isolation = require_isolation

    def handle(self, request: Any, next_callable: Callable) -> Any:
        container = _container(self.app)
        tenant = container.make("tenant")

        if self.require_isolation:
            container.make("db").dialect.require(
                "rls", "is what isolates one tenant's rows from another's"
            )
            # The driver having policies is not the same as the *role* being
            # subject to them: a superuser or a BYPASSRLS grant makes every
            # policy inert, and nothing about the table says so. Checked once
            # per process; see `TenantManager.enforcement`.
            tenant.assert_enforced()

        resolved = self.resolve(request, container)
        tenant.bind(resolved)
        self._guardian(container).check(context="request", tenant_id=resolved)

        # No try/finally: the kernel's `db.release()` clears the session
        # variable at checkin, and the ContextVar dies with the thread's copied
        # context. A reset here would be a second belt on a holding one.
        return next_callable(request)

    @staticmethod
    def _guardian(container: Any) -> Any:
        from engine.orm.tenant_guardian import TenantScopeGuardian

        try:
            mode = container.make("config").get("database.tenancy.guardian_mode", "warn")
        except Exception:
            mode = "warn"
        return TenantScopeGuardian(mode=mode)

    def resolve(self, request: Any, container: Any) -> Any:
        """Tenant from the host, checked against the session's own tenant.

        Host first, because it is the boundary a customer can see and an
        operator can reason about. A host naming a subdomain that isn't
        reserved MUST resolve to a real, active tenant, or this raises rather
        than quietly falling through to the authenticated user's tenant — a
        fall-through there is how a stale session or a typo'd subdomain would
        otherwise land a request in someone else's data. Override this method
        to resolve differently - a header, a path segment, an API token claim.
        """
        # Host headers are case-insensitive (RFC 7230 §5.4). Comparing an
        # un-lowercased host against RESERVED_SUBDOMAINS meant `WWW.example.com`
        # missed the reserved-subdomain check, fell into the tenant lookup,
        # matched no tenant, and 404'd a request that should have been treated
        # as the reserved `www` host.
        host = str(getattr(request, "header", lambda _n: "")("host") or "").split(":")[0].lower()
        subdomain = host.split(".")[0] if host.count(".") >= 2 else None
        if subdomain and subdomain not in self.RESERVED_SUBDOMAINS:
            from engine.orm.tenancy import TenantHostMismatchError, TenantSuspendedError, UnboundTenantHostError

            record = self.tenant_record_for_subdomain(subdomain)
            if record is None:
                raise UnboundTenantHostError(host)
            if record["status"] == "suspended":
                raise TenantSuspendedError(record["id"])

            user = self._authenticated_user(container)
            session_tenant_id = user.get_attribute("tenant_id") if user is not None else None
            if session_tenant_id not in (None, record["id"]):
                raise TenantHostMismatchError(host, record["id"], session_tenant_id)
            return record["id"]

        user = self._authenticated_user(container)
        return user.get_attribute("tenant_id") if user is not None else None

    @staticmethod
    def _authenticated_user(container: Any) -> Any:
        try:
            return container.make("auth").user()
        except Exception:
            return None

    #: Hosts that never name a tenant. `api` is here because an API host is
    #: usually shared and identifies its tenant by token, not by name.
    RESERVED_SUBDOMAINS = ("www", "app", "api", "admin", "static", "cdn")

    def tenant_for_subdomain(self, subdomain: str) -> Any:
        """Resolve a subdomain to a tenant id, or `None`.

        Kept for backward compatibility (NR-05): its original contract
        collapsed "no such tenant" and "suspended tenant" into the same
        `None`, so this preserves that. `resolve()` itself uses
        `tenant_record_for_subdomain()` instead, specifically to keep those
        two cases distinguishable.
        """
        record = self.tenant_record_for_subdomain(subdomain)
        if record is None or record["status"] == "suspended":
            return None
        return record["id"]

    def tenant_record_for_subdomain(self, subdomain: str) -> Any:
        """Resolve a subdomain against the framework's `tenants` table.

        A query rather than a hook returning None: `tenants` ships with the
        framework, so the engine owns it and does not have to reach into `app/`
        to read it. Override this to resolve from somewhere else - a header, a
        path segment, a cache in front of the lookup.

        Soft-deleted tenants resolve to nothing (indistinguishable from a
        subdomain that never existed) — a suspended tenant, still present but
        with `status = 'suspended'`, resolves to its record instead, so
        `resolve()` can tell the two apart.

        Returns:
            A `{"id": ..., "status": ...}` mapping, or `None` if the slug
            matches no non-deleted tenant.
        """
        container = _container(self.app)
        try:
            row = container.make("db").statement(
                "SELECT id, status, is_active FROM tenants WHERE slug = ? AND deleted_at IS NULL",
                [subdomain],
                read=True,
            ).fetchone()
        except Exception:
            # A missing table is not a reason to fail every request - the app
            # may resolve tenants some other way entirely.
            logging.getLogger("craft").debug(
                "Could not resolve tenant for subdomain %r", subdomain, exc_info=True
            )
            return None
        if row is None:
            return None
        # `is_active` predates `status` and some callers still only write that
        # boolean - honour it as "suspended" until a later release drops the
        # column, so a row that never got a `status` write doesn't silently
        # read as active. SQLite has no boolean type, so this is a falsiness
        # check (0/False), not an identity check - `is False` would miss the
        # integer 0 that SQLite actually stores.
        is_active = row["is_active"]
        status = "suspended" if is_active is not None and not is_active else (row["status"] or "active")
        return {"id": row["id"], "status": status}


class RequireAuth(Middleware):
    """Terminate the request when nobody is authenticated."""

    alias_parameters = ()

    def __init__(self, app: Any = None, redirect_to: str = "/login"):
        self.app = app
        self.redirect_to = redirect_to

    def handle(self, request: Any, next_callable: Callable) -> Any:
        if _container(self.app).make("auth").check():
            return next_callable(request)

        if getattr(request, "expects_json", lambda: False)():
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException("Unauthenticated.")

        from starlette.responses import RedirectResponse

        return RedirectResponse(self.redirect_to, status_code=302)


class RequireRole(Middleware):
    """Terminate the request unless the authenticated user has the role.

    Resolved from the `role:<slug>` route middleware alias - see
    `Kernel.resolve_route_middleware`.
    """

    alias_parameters = ("role",)

    def __init__(self, role: str, app: Any = None, redirect_to: str = "/login"):
        self.role = role
        self.app = app
        self.redirect_to = redirect_to

    def handle(self, request: Any, next_callable: Callable) -> Any:
        user = _container(self.app).make("auth").user()

        if user is not None and getattr(user, "has_role", None) and user.has_role(self.role):
            return next_callable(request)

        if getattr(request, "expects_json", lambda: False)():
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException(f"Missing role: {self.role}")

        if user is None:
            from starlette.responses import RedirectResponse

            return RedirectResponse(self.redirect_to, status_code=302)

        from engine.exceptions.handler import AuthorizationException

        raise AuthorizationException(f"Missing role: {self.role}")


class RequireFreshAuth(Middleware):
    """Terminate the request unless the session authenticated recently enough.

    Resolved from the `fresh:<seconds>` route middleware alias (e.g.
    `fresh:300` for five minutes) or bare `fresh` for the default window —
    see `Kernel.route_middleware_aliases`. For a sensitive action (change
    password, view billing, grant admin) where "logged in" is not enough;
    "logged in within the last few minutes" is what step-up auth checks.
    Register AFTER `auth`/`RequireAuth`, so a guest gets the "please log in"
    redirect rather than a confusing "please re-authenticate."
    """

    alias_parameters = ("max_age_seconds",)

    def __init__(self, max_age_seconds: Any = None, app: Any = None, redirect_to: str = "/login"):
        from engine.auth.step_up import DEFAULT_MAX_AGE_SECONDS

        self.max_age_seconds = int(max_age_seconds) if max_age_seconds else DEFAULT_MAX_AGE_SECONDS
        self.app = app
        self.redirect_to = redirect_to

    def handle(self, request: Any, next_callable: Callable) -> Any:
        from engine.auth.step_up import StepUpAuth

        session = request.session() if getattr(request, "has_session", lambda: False)() else None
        if StepUpAuth.is_fresh(session, self.max_age_seconds):
            return next_callable(request)

        if getattr(request, "expects_json", lambda: False)():
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException("Re-authentication required.")

        from starlette.responses import RedirectResponse

        return RedirectResponse(self.redirect_to, status_code=302)


class RequireGroup(Middleware):
    """Terminate the request unless the authenticated user is in the group.

    Resolved from the `group:<slug>` route middleware alias - see
    `Kernel.resolve_route_middleware`. Useful when a whole area belongs to a
    team ("the support console"), where naming the team is more honest than
    inventing a permission that means "is on the support team".
    """

    alias_parameters = ("group",)

    def __init__(self, group: str, app: Any = None, redirect_to: str = "/login"):
        self.group = group
        self.app = app
        self.redirect_to = redirect_to

    def handle(self, request: Any, next_callable: Callable) -> Any:
        user = _container(self.app).make("auth").user()

        if user is not None and callable(getattr(user, "in_group", None)) and user.in_group(self.group):
            return next_callable(request)

        if getattr(request, "expects_json", lambda: False)():
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException(f"Missing group: {self.group}")

        if user is None:
            from starlette.responses import RedirectResponse

            return RedirectResponse(self.redirect_to, status_code=302)

        from engine.exceptions.handler import AuthorizationException

        raise AuthorizationException(f"Missing group: {self.group}")


class RequirePermission(Middleware):
    """Terminate the request unless the authenticated user has the permission.

    Resolved from the `permission:<slug>` route middleware alias - see
    `Kernel.resolve_route_middleware`.

    Note that this asks for the permission with **no resource in hand**, so a
    grant narrowed by attribute conditions ("only your own") does not satisfy
    it - route middleware cannot know which record the controller will load.
    Guard those in the controller with `Gate.authorize(ability, user, record)`
    once the record exists.
    """

    alias_parameters = ("permission",)

    def __init__(self, permission: str, app: Any = None, redirect_to: str = "/login"):
        self.permission = permission
        self.app = app
        self.redirect_to = redirect_to

    def handle(self, request: Any, next_callable: Callable) -> Any:
        user = _container(self.app).make("auth").user()

        if (
            user is not None
            and getattr(user, "has_permission", None)
            and user.has_permission(self.permission)
        ):
            return next_callable(request)

        if getattr(request, "expects_json", lambda: False)():
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException(f"Missing permission: {self.permission}")

        if user is None:
            from starlette.responses import RedirectResponse

            return RedirectResponse(self.redirect_to, status_code=302)

        from engine.exceptions.handler import AuthorizationException

        raise AuthorizationException(f"Missing permission: {self.permission}")


class AuthenticateApiToken(Middleware):
    """Require a valid `Authorization: Bearer <token>` for the api guard.

    This *rejects*. It used to resolve a user when a token happened to match
    and call the next handler regardless - so a route carrying the `api` alias
    accepted anonymous requests, and the only thing standing between the
    public internet and a write was whatever check the controller happened to
    run. A middleware named "authenticate" that never denies is worse than no
    middleware, because the route reads as protected.

    Use `RequireAuth`/`Authenticate` if what you actually want is "resolve the
    user if one is present, but let guests through".
    """

    alias_parameters = ()

    def __init__(self, app: Any = None, column: Optional[str] = None):
        self.app = app
        self.column = column

    def handle(self, request: Any, next_callable: Callable) -> Any:
        app = _container(self.app)
        auth = app.make("auth")
        auth.logout()

        token = getattr(request, "bearer_token", lambda: None)()
        user = None

        if token:
            import hashlib

            try:
                column = self.column or app.make("config").get(
                    "auth.guards.api.token_name", "api_token"
                )
            except Exception:
                column = self.column or "api_token"

            # Check hashed token first (SHA-256) or fallback to plain token
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            user = auth.user_model().query().where(column, token_hash).first()
            if user is None:
                user = auth.user_model().query().where(column, token).first()

        if user is None:
            from engine.exceptions.handler import AuthorizationException

            # Deliberately identical for "no token" and "bad token": telling
            # the caller which one it was confirms whether a token exists.
            raise AuthorizationException("Unauthenticated.")

        auth.login(user)
        return next_callable(request)


class SecurityHeaders(Middleware):
    """Set baseline and configurable security response headers."""

    def __init__(self, app: Any = None):
        self.app = app

    def _csp_for_path(self, config: Any, path: str) -> Optional[str]:
        """The policy for this path: the longest matching prefix wins.

        `/admin/reports` matches a configured `/admin` prefix over a bare
        `/` default, so an admin console and a public site can carry
        different policies without one route accidentally inheriting the
        other's.
        """
        prefixes = config.get("security.csp.prefixes", {}) or {}
        best_match: Optional[str] = None
        best_length = -1
        for prefix, policy in prefixes.items():
            if path.startswith(str(prefix)) and len(str(prefix)) > best_length:
                best_match, best_length = str(policy), len(str(prefix))
        if best_match is not None:
            return best_match
        default = config.get("security.csp.default", "") or config.get("app.CSP", "")
        return str(default) if default else None

    def handle(self, request: Any, next_callable: Callable) -> Any:
        response = next_callable(request)
        starlette_response = _as_starlette(response)
        if starlette_response is None:
            return response

        starlette_response.headers.setdefault("X-Content-Type-Options", "nosniff")
        starlette_response.headers.setdefault("X-Frame-Options", "DENY")
        starlette_response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        starlette_response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        try:
            config = _container(self.app).make("config")
            path = str(getattr(getattr(request, "url", None), "path", "") or "")
            policy = self._csp_for_path(config, path)
            if policy:
                report_uri = config.get("security.csp.report_uri", "")
                if report_uri:
                    policy = f"{policy}; report-uri {report_uri}"
                header_name = (
                    "Content-Security-Policy-Report-Only"
                    if config.get("security.csp.report_only", False)
                    else "Content-Security-Policy"
                )
                starlette_response.headers.setdefault(header_name, policy)
            hsts = config.get("security.hsts") or config.get("app.HSTS")
            if hsts:
                starlette_response.headers.setdefault("Strict-Transport-Security", str(hsts))
        except Exception:
            pass

        return starlette_response


class ThrottleRequests(Middleware):
    """Fixed-window per-IP+route rate limit - closes the "no rate limiting
    on authentication endpoints" gap called out in SECURITY.md. Backed by
    the cache store, so it works with the array/file/redis driver alike."""

    alias_parameters = ("max_attempts", "decay_seconds")

    def __init__(self, app: Any = None, max_attempts: int = 10, decay_seconds: int = 60):
        self.app = app
        self.max_attempts = max_attempts
        self.decay_seconds = decay_seconds

    def _cache(self) -> Any:
        return _container(self.app).make("cache")

    def _key(self, request: Any) -> str:
        client = getattr(request, "client", None)
        ip = getattr(client, "host", None) or "unknown"
        return f"throttle:{request.url.path}:{ip}"

    def handle(self, request: Any, next_callable: Callable) -> Any:
        cache = self._cache()
        key = self._key(request)

        attempts = cache.get(key)
        if attempts is None:
            cache.put(key, 1, self.decay_seconds)
        elif int(attempts) >= self.max_attempts:
            from engine.exceptions.handler import CraftException

            error = CraftException("Too many attempts. Please try again later.")
            error.status_code = 429
            raise error
        else:
            cache.increment(key)

        return next_callable(request)


from engine.security.firewall import FirewallMiddleware

__all__ = [
    "Middleware",
    "StartSession",
    "SetLocale",
    "VerifyCsrfToken",
    "Authenticate",
    "RequireAuth",
    "RequireRole",
    "RequirePermission",
    "RequireGroup",
    "AuthenticateApiToken",
    "SecurityHeaders",
    "ThrottleRequests",
    "FirewallMiddleware",
]

