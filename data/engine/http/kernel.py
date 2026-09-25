"""
Kernel - Builds the Starlette ASGI app: mounts the router, static files, and
runs each request through the registered middleware stack.
Category: Core Framework (HTTP).
Relations:
  - Built once in `bootstrap/app.py`; consumes `engine/http/router.py` and
    `engine/http/middleware.py`.
References:
  - Guide: `documentation/routing.md`, `documentation/deployment.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import inspect
import logging
import os
from typing import Any, List, Optional

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.routing import Mount
from starlette.routing import Route as StarletteRoute
from starlette.staticfiles import StaticFiles

from engine.container.application import Container
from engine.http.static_files import CachedStaticFiles

logger = logging.getLogger("craft.http")


def render_exception(app: Any, request: Any, exc: Exception) -> StarletteResponse:
    """Turn an exception into a response via the registered handler.

    Shared by the kernel's outer catch and by middleware (StartSession) that
    needs to materialise an exception-driven response early enough to still
    attach the session cookie to it.
    """
    status = getattr(exc, "status_code", None)
    headers = getattr(exc, "headers", None)
    if status in (301, 302, 303, 307, 308) and headers and "location" in headers:
        return RedirectResponse(headers["location"], status_code=status)

    try:
        handler = app.make("exception_handler")
    except Exception:
        handler = None

    if handler is not None and hasattr(handler, "render"):
        wants_json = getattr(request, "expects_json", lambda: True)()
        return handler.render(exc, wants_json=wants_json)

    return _fallback_response(exc, status or 500)


def _fallback_response(exc: Exception, status: int) -> StarletteResponse:
    """Answer without an exception handler, never echoing the exception text.

    `str(exc)` of a database error carries the SQL, constraint names and row
    values (`DETAIL: Key (email)=(...)`); it belongs in the log, not the body.

    Args:
        exc: The unhandled exception.
        status: The HTTP status to answer with.

    Returns:
        A JSON error carrying only a stable code and translation key.
    """
    logger.error("unhandled_exception", exc_info=exc, extra={"status": status})
    code = getattr(exc, "code", None) if status < 500 else None
    message_key = getattr(exc, "message_key", None) if status < 500 else None
    return JSONResponse(
        {"error": {"code": code or "SERVER_ERROR", "message_key": message_key or "error.server"}},
        status_code=status,
    )


_SCALAR_CASTS = {int: int, float: float, str: str}


def cast_route_value(value: str, annotation: Any) -> Any:
    """Convert a path segment to the type its parameter declares.

    Args:
        value: The raw path segment.
        annotation: The parameter annotation (`int`, `float`, `bool`, `UUID`...).

    Returns:
        The converted value, or `value` unchanged for undeclared types.

    Raises:
        NotFoundHttpException: When the segment cannot be converted — `/posts/abc`
            for `id: int` is a missing page, not a server error.
    """
    import uuid

    from engine.exceptions.handler import NotFoundHttpException

    caster = _SCALAR_CASTS.get(annotation) or ({bool: _to_bool, uuid.UUID: uuid.UUID}).get(annotation)
    if caster is None:
        return value
    try:
        return caster(value)
    except (TypeError, ValueError) as exc:
        raise NotFoundHttpException(f"ROUTE_PARAMETER_INVALID: {value!r}") from exc


def _to_bool(value: str) -> bool:
    lowered = str(value).lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off"):
        return False
    raise ValueError(value)


def _is_request_parameter(position: int, name: str, param: inspect.Parameter, path_params: dict) -> bool:
    """Whether a parameter receives the request object.

    By name (`request`), by annotation, or — for handlers written as
    `def show(req, id)` — by being the first parameter while not naming a
    path placeholder.
    """
    if name == "request" or getattr(param.annotation, "__name__", "") in ("Request", "StarletteRequest"):
        return True
    return position == 0 and name not in path_params and param.annotation is inspect.Parameter.empty


def bind_route_arguments(target: Any, request: Any) -> dict:
    """Build the keyword arguments for a route action.

    Path parameters bind by name and are cast to the declared annotation. A
    placeholder whose name matches no parameter binds positionally, and only to
    a parameter WITHOUT a default: a defaulted parameter such as `page=1` used
    to receive an unrelated path segment.

    Args:
        target: The controller method or route function.
        request: The current request.

    Returns:
        Keyword arguments for `target`.
    """
    path_params = dict(getattr(request, "path_params", {}) or {})
    parameters = inspect.signature(target).parameters
    spare = [key for key in path_params if key not in parameters]
    kwargs: dict = {}
    for position, (name, param) in enumerate(parameters.items()):
        if _is_request_parameter(position, name, param, path_params):
            kwargs[name] = request
        elif name in path_params:
            kwargs[name] = cast_route_value(path_params[name], param.annotation)
        elif spare and param.default is inspect.Parameter.empty:
            kwargs[name] = cast_route_value(path_params[spare.pop(0)], param.annotation)
    return kwargs


class DynamicStarletteApp:
    def __init__(self, kernel: "Kernel"):
        self.kernel = kernel
        self._app: Optional[Starlette] = None
        self._version: Any = None

    #: Verbs a browser cannot send from a form, and so may be spoofed.
    SPOOFABLE_METHODS = ("PUT", "PATCH", "DELETE")

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") == "lifespan":
            # Handled here rather than by the inner Starlette app, which is
            # rebuilt whenever the route table changes: a shutdown hook
            # registered on an instance that has since been replaced would
            # never run, which is precisely the bug this must not have.
            await self._lifespan(scope, receive, send)
            return

        # Rebuild only when the route table changed - rebuilding the whole
        # Starlette app per request was pure waste.
        router = self.kernel.app.make("router")
        version = getattr(router, "_version", None)
        if version is None:
            version = len(router.routes)
        if self._app is None or self._version != version:
            self._app = self.kernel._build_starlette_app()
            self._version = version

        scope, receive = await self._apply_method_override(scope, receive)
        # Every request gets its own `scoped()` instances, discarded on exit.
        token = Container.begin_request_scope()
        try:
            await self._app(scope, receive, send)
        finally:
            Container.end_request_scope(token)

    async def _lifespan(self, scope: Any, receive: Any, send: Any) -> None:
        """Run the process-level startup and shutdown protocol.

        The shutdown half is what makes a rolling deploy safe: the server stops
        accepting connections and waits for in-flight requests before sending
        `lifespan.shutdown`, so by the time the hooks below run there is nobody
        left holding a pooled connection and the pool can be closed for real.
        Without this the process exited with connections still open on the
        server, which a managed database counts against `max_connections` until
        it notices the socket is gone.
        """
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    await self.kernel.on_startup()
                except Exception as exc:  # pragma: no cover - boot failure path
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                    return
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                try:
                    await self.kernel.on_shutdown()
                finally:
                    await send({"type": "lifespan.shutdown.complete"})
                return

    async def _apply_method_override(self, scope: Any, receive: Any):
        """Honour a `_method` form field, before Starlette routes the request.

        HTML forms can only issue GET and POST, so the framework emits a hidden
        `_method` input - the `@method("PUT")` view directive and every
        edit/delete form the CRUD builder generates rely on it. Nothing ever
        read it back: the browser sent POST, `Route.resource()` had registered
        the route under PUT/DELETE, and the request 405'd. The directive
        produced decorative HTML and generated admin forms simply did not work.

        This has to happen at the ASGI layer: Starlette matches on the method
        before any endpoint or middleware of ours runs, so rewriting it later
        is already too late.
        """
        if scope.get("type") != "http" or scope.get("method") != "POST":
            return scope, receive

        content_type = b""
        for header, value in scope.get("headers", []):
            if header == b"content-type":
                content_type = value
                break
        if not content_type.startswith((b"application/x-www-form-urlencoded", b"multipart/form-data")):
            return scope, receive

        # The body can only be consumed once, so buffer it and hand the app a
        # receive channel that replays exactly what we read.
        body = b""
        messages = []
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break

        override = self._extract_method(body, content_type)
        if override in self.SPOOFABLE_METHODS:
            scope = dict(scope)
            scope["method"] = override

        replay = iter(messages)

        async def replaying_receive():
            try:
                return next(replay)
            except StopIteration:
                return await receive()

        return scope, replaying_receive

    @staticmethod
    def _extract_method(body: bytes, content_type: bytes) -> Optional[str]:
        import re
        from urllib.parse import parse_qs

        try:
            if content_type.startswith(b"application/x-www-form-urlencoded"):
                values = parse_qs(body.decode("latin-1")).get("_method")
                return values[0].upper() if values else None

            # Multipart: a targeted scan beats parsing the whole payload, which
            # may carry file uploads we have no reason to buffer twice.
            match = re.search(rb'name="_method"\r?\n\r?\n([A-Za-z]+)', body)
            return match.group(1).decode("latin-1").upper() if match else None
        except Exception:
            return None


class Kernel:
    """HTTP Kernel wrapping Starlette app with Craft pipeline dispatching."""

    def __init__(self, app: Any):
        self.app = app
        self.middleware_classes: List[Any] = []
        self._middleware: Optional[List[Any]] = None
        self._aliases: dict = {}

    #: Worker threads per DB connection. The whole request chain is
    #: synchronous, so concurrency is threads, and a thread that cannot get a
    #: connection just waits out `pool_timeout` and fails. Slightly more
    #: threads than connections keeps requests that never touch the database
    #: moving; many more only converts a fast rejection into a slow one.
    THREADS_PER_CONNECTION = 2
    MIN_THREADPOOL_SIZE = 8

    async def on_startup(self) -> None:
        """Bound the worker pool, and declare the metrics this process reports."""
        self._apply_threadpool_limit()
        try:
            from engine.support.metrics import register_default_metrics

            register_default_metrics(self.app)
        except Exception:
            pass

    async def on_shutdown(self) -> None:
        """Release process-wide resources once the server has drained."""
        for closer in ("db",):
            try:
                self.app.make(closer).purge()
            except Exception:
                # Shutdown must not raise: an exception here would replace an
                # orderly exit with a stack trace and a non-zero status.
                pass

    def _apply_threadpool_limit(self) -> None:
        size = self.threadpool_size()
        if size <= 0:
            return
        try:
            import anyio.to_thread

            anyio.to_thread.current_default_thread_limiter().total_tokens = size
        except Exception:  # pragma: no cover - depends on the anyio version
            pass

    def threadpool_size(self) -> int:
        """How many requests this process serves at once.

        Defaults from `pool_size` rather than a fixed number, because the two
        are the same setting seen from opposite ends: anyio's default of 40
        threads against a pool of 4 means 36 threads queueing on a connection
        timeout instead of being turned away at the door.
        """
        try:
            config = self.app.make("config")
            explicit = config.get("framework.HTTP_THREADPOOL_SIZE", 0)
            if explicit:
                return max(1, int(explicit))
            name = config.get("database.default") or "sqlite"
            settings = config.get(f"database.connections.{name}", {}) or {}
            pool_size = int(settings.get("pool_size") or 0)
        except Exception:
            return 0
        if not pool_size:
            return 0
        return max(self.MIN_THREADPOOL_SIZE, pool_size * self.THREADS_PER_CONNECTION)

    def with_middleware(self, *middleware) -> "Kernel":
        self.middleware_classes.extend(middleware)
        self._middleware = None  # rebuild the stack on next request
        return self

    def middleware(self) -> List[Any]:
        """Middleware instances, built once and reused.

        Building them per request was a correctness bug, not just waste: a
        middleware that caches anything - the session store and its signing key,
        for one - got a fresh copy every time, so nothing survived a request.
        """
        if self._middleware is None:
            self._middleware = [self._instantiate(cls) for cls in self.middleware_classes]
        return self._middleware

    #: Short names usable in `Route.get(...).middleware("auth")`.
    def route_middleware_aliases(self) -> dict:
        from engine.http import middleware as mw

        return {
            "auth": mw.RequireAuth,
            "api": mw.AuthenticateApiToken,
            "session": mw.StartSession,
            "csrf": mw.VerifyCsrfToken,
            "throttle": mw.ThrottleRequests,
            "role": mw.RequireRole,
            "permission": mw.RequirePermission,
            "group": mw.RequireGroup,
            "firewall": mw.FirewallMiddleware,
            "fresh": mw.RequireFreshAuth,
        }

    def alias_middleware(self, name: str, middleware_class: Any) -> "Kernel":
        """Register an extra route-middleware alias."""
        self._aliases[name] = middleware_class
        return self

    def resolve_route_middleware(self, entries: List[Any]) -> List[Any]:
        """Turn a route's middleware list into instances.

        Accepts alias strings and classes. Aliases may carry a parameter after
        a colon - `"role:admin"` / `"permission:manage-users"` - which is
        passed as the first positional argument to the resolved middleware
        class (e.g. `RequireRole(role="admin")`). Unknown aliases raise rather
        than being skipped - a route that declares protection which silently
        does nothing is worse than one that fails loudly at boot.
        """
        aliases = {**self.route_middleware_aliases(), **self._aliases}
        resolved = []
        for entry in entries or []:
            if isinstance(entry, str):
                if entry in aliases:
                    # Some aliases (`role`, `permission`) are only meaningful
                    # with a `:param` - a bare use is a caller mistake, not a
                    # silently-do-nothing middleware, so it must still raise.
                    try:
                        resolved.append(self._instantiate(aliases[entry]))
                        continue
                    except TypeError:
                        raise KeyError(
                            f"Route middleware [{entry}] requires a parameter - "
                            f"use '{entry}:<value>' (e.g. '{entry}:admin')."
                        ) from None

                base_alias, _, param = entry.partition(":")
                if param and base_alias in aliases:
                    resolved.append(self._instantiate(aliases[base_alias], param))
                    continue

                raise KeyError(
                    f"Unknown route middleware [{entry}]. Register it with "
                    f"kernel.alias_middleware('{entry}', SomeMiddleware)."
                )
            elif isinstance(entry, type):
                resolved.append(self._instantiate(entry))
            else:
                resolved.append(entry)
        return resolved

    #: Name of the sub-application serving `public/`.
    STATIC_MOUNT_NAME = "static"

    #: Dotted module recorded as the attribution of the static mount.
    STATIC_MOUNT_PROVIDER = "engine.http.kernel"

    def register_engine_routes(self, *, refresh: bool = False) -> List[Any]:
        """Record the framework's own routes on the router, and return them.

        The probes, the manifest and the static mount used to be appended
        straight onto the ASGI route table, so they answered requests that no
        listing could account for. Registering them here makes the router the
        one place every route that answers is written down, whoever attached
        it, and `RouteEntry.origin` says which layer that was.

        Args:
            refresh: Drop what was registered and read the configuration
                again. Registration is otherwise idempotent, so the default
                leaves an already-registered table untouched.

        Returns:
            The engine routes now on the router.
        """
        from engine.http.health import register_health_routes
        from engine.http.msr import register_msr_route

        router = self.app.make("router")
        if refresh:
            router.clear_engine_routes()

        register_health_routes(self.app, router)
        register_msr_route(self.app, router)
        self._register_static_mount(router)
        return router.engine_routes()

    def engine_routes(self) -> List[Any]:
        """Return the routes the framework attached, for listings and audits.

        Returns:
            The `RouteEntry` objects marked with the engine origin; each
            carries `uri`, `methods`, its name, and the `provider` module that
            registered it. `RouteEntry.describe()` renders one as a mapping.
        """
        return self.app.make("router").engine_routes()

    def _register_static_mount(self, router: Any) -> None:
        """Record the `public/` mount, which serves the application's assets.

        Infrastructure rather than a feature, so it is always registered when
        the directory exists - but it is registered, not hidden, and the
        kernel places it after every other route so it shadows nothing.

        Args:
            router: The router the mount is recorded on.
        """
        public_dir = os.path.join(self.app.base_path, "public")
        if not os.path.isdir(public_dir):
            return
        router.add_engine_mount(
            "/",
            CachedStaticFiles(directory=public_dir),
            name=self.STATIC_MOUNT_NAME,
            provider=self.STATIC_MOUNT_PROVIDER,
        )

    def _engine_starlette_routes(self, router: Any) -> List[Any]:
        """Build the engine routes, outside the application middleware stack.

        Plain routes come before mounts so the static mount on `/` never
        shadows a probe, and an application route on the same path is left to
        win by being earlier in the table the kernel assembles.

        Args:
            router: The router holding the registered entries.

        Returns:
            Starlette routes and mounts, in the order they must be appended.
        """
        claimed = router.claimed_uris()
        plain: List[Any] = []
        mounts: List[Any] = []
        for entry in router.engine_routes():
            if entry.is_mount:
                mounts.append(Mount(entry.uri, app=entry.action, name=entry._name))
            elif entry.uri not in claimed:
                plain.append(StarletteRoute(entry.uri, endpoint=entry.action, methods=entry.methods))
        return plain + mounts

    def _build_starlette_app(self) -> Starlette:
        self.register_engine_routes()
        router = self.app.make("router")
        routes = []

        for r in router.application_routes():
            endpoint = self._create_endpoint(r.action, r._module, r.middleware_list, route_uri=r.uri)
            for m in r.methods:
                routes.append(StarletteRoute(r.uri, endpoint=endpoint, methods=[m]))

        # Appended after the application's own routes, so a project that
        # declares `/health` keeps its own.
        routes.extend(self._engine_starlette_routes(router))

        # Never hardcode debug - it leaks stack traces to clients in production.
        try:
            debug = bool(self.app.make("config").get("app.APP_DEBUG", False))
        except Exception:
            debug = False

        return Starlette(debug=debug, routes=routes)

    def get_starlette_app(self) -> DynamicStarletteApp:
        return DynamicStarletteApp(self)

    def _instantiate(self, mw_cls: Any, param: Optional[str] = None) -> Any:
        """Build a middleware, passing the app and an alias parameter when accepted."""
        try:
            signature = inspect.signature(mw_cls.__init__)
        except TypeError, ValueError:
            return mw_cls()

        kwargs = {}
        if "app" in signature.parameters:
            kwargs["app"] = self.app

        declared = getattr(mw_cls, "alias_parameters", None)
        if param is not None and declared is not None:
            kwargs.update(_alias_arguments(mw_cls, declared, param, signature))
        elif param is not None:
            # Legacy rule for middleware that does not declare its alias
            # parameters: the first parameter after `self`/`app` gets the raw
            # string.
            positional = [name for name in signature.parameters if name not in ("self", "app")]
            if positional:
                kwargs[positional[0]] = param

        return mw_cls(**kwargs)

    def _create_endpoint(
        self,
        action: Any,
        module_name: Optional[str] = None,
        route_middleware: Optional[List[Any]] = None,
        route_uri: Optional[str] = None,
    ) -> Any:
        route_stack = self.resolve_route_middleware(route_middleware or [])

        async def endpoint(request: StarletteRequest) -> StarletteResponse:
            # Middleware and controllers are synchronous, so the body has to be
            # read here - they cannot await `request.form()` themselves.
            from engine.http.request import from_starlette

            request = await from_starlette(request).prepare()
            # The pattern, not the path: metrics labelled `/posts/{id}` are one
            # series, while `/posts/1`, `/posts/2` and so on are as many series
            # as there are posts.
            request.route_uri = route_uri

            if module_name:
                # Ask the ModuleManager rather than issuing a SELECT here: it is
                # the single source of truth for module state and it caches the
                # answer, so a module-scoped route no longer costs a query per
                # request. A module the manager has never heard of (`None`)
                # falls back to config, which defaults to enabled.
                state = None
                try:
                    state = self.app.make("module").state(module_name)
                except Exception:
                    state = None

                if state is None:
                    config = self.app.make("config")
                    enabled = bool(config.get(f"modules.{module_name}.enabled", True))
                else:
                    enabled = state

                if not enabled:
                    return JSONResponse({"error": "Module Disabled"}, status_code=404)

            def handle_action(req):
                if isinstance(action, list):
                    controller_cls, method_name = action[0], action[1]
                    controller_inst = (
                        self.app.make(controller_cls) if isinstance(controller_cls, type) else controller_cls()
                    )
                    method = getattr(controller_inst, method_name)

                    result = method(**bind_route_arguments(method, req))

                elif callable(action):
                    result = action(**bind_route_arguments(action, req))
                else:
                    result = action

                if inspect.iscoroutine(result):
                    # Async controller action. This chain already runs on a
                    # worker thread (see `serve` below), which has no event
                    # loop, so the coroutine can run to completion right here.
                    # It must be *this* thread: the pooled connection is
                    # thread-local, and running the coroutine on another thread
                    # checked out a second connection that `release()` never saw.
                    import asyncio

                    result = asyncio.run(result)

                if hasattr(result, "to_starlette"):
                    return result.to_starlette()
                if isinstance(result, StarletteResponse):
                    return result
                if isinstance(result, (dict, list)):
                    return JSONResponse(result)
                return HTMLResponse(str(result))

            # Route middleware runs inside the global stack, so it can rely on
            # the session and resolved user that the global stack sets up.
            current_call = handle_action
            for mw_inst in reversed(self.middleware() + route_stack):
                prev_call = current_call
                current_call = lambda req, inst=mw_inst, next_fn=prev_call: inst.handle(req, next_fn)

            # The whole middleware + controller chain is synchronous and every
            # ORM call blocks. Running it inline blocked the event loop for the
            # duration of the request, so the process served exactly one at a
            # time - the measured ~30 req/s ceiling, flat from 1 to 100 clients.
            # Offloading to the thread pool is only safe because the connection
            # layer now keeps one session per thread, and because the auth
            # manager's per-request state is thread-local; without those, two
            # requests would share a cursor and an identity.
            def serve(req):
                try:
                    return current_call(req)
                finally:
                    # End of the request on this thread: give the pooled
                    # connection back. Inside the worker thread, because that is
                    # the thread that borrowed it.
                    try:
                        self.app.make("db").release()
                    except Exception:
                        pass

            try:
                return await run_in_threadpool(serve, request)
            except Exception as exc:
                return self._render_exception(request, exc)

        return endpoint

    def _render_exception(self, request: Any, exc: Exception) -> StarletteResponse:
        """Turn an exception into a response via the registered handler."""
        return render_exception(self.app, request, exc)


class MiddlewareAliasError(KeyError):
    """A route middleware string the kernel cannot turn into a middleware.

    A `KeyError` so existing handlers keep catching it; `str()` is the plain
    message rather than the quoted repr `KeyError` prints.
    """

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


def _alias_arguments(mw_cls: Any, declared: Any, param: str, signature: Any) -> dict:
    """Map the `alias:value[,value]` parameter onto the declared constructor names.

    Args:
        mw_cls: The middleware class the alias resolved to.
        declared: Its `alias_parameters`, in order.
        param: The text after the colon.
        signature: `inspect.signature(mw_cls.__init__)`.

    Returns:
        Keyword arguments for the constructor, converted to each default's type.

    Raises:
        MiddlewareAliasError: The alias takes no parameter, too many values
            were given, or a value does not convert.
    """
    name = mw_cls.__name__
    if not declared:
        raise MiddlewareAliasError(
            f"{name} takes no route parameter, but got ':{param}'. Remove it. "
            f"Authentication by API token is the 'api' alias, not 'auth:api'."
        )
    values = [value.strip() for value in param.split(",")]
    if len(values) > len(declared):
        raise MiddlewareAliasError(
            f"{name} takes {len(declared)} route parameter(s) ({', '.join(declared)}), got "
            f"{len(values)}: ':{param}'. To require any of several roles or permissions, "
            f"check them in a Gate or policy instead of listing them in one alias."
        )
    arguments = {}
    # Fewer values than declared is fine: the rest keep their defaults.
    for key, value in zip(declared, values, strict=False):
        default = signature.parameters[key].default
        if isinstance(default, int) and not isinstance(default, bool):
            try:
                arguments[key] = int(value)
            except ValueError:
                raise MiddlewareAliasError(
                    f"{name} parameter '{key}' must be an integer, got '{value}'."
                ) from None
        else:
            arguments[key] = value
    return arguments
