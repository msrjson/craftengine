"""
Router — Route registration (`get`/`post`/...), groups, `resource()`/
`api_resource()`, named routes, and `url_for()`.
Category: Core Framework (HTTP).
Relations:
  - Exposed via the `Route` facade; mounted into Starlette by
    `engine/http/kernel.py`; middleware aliases resolved by
    `engine/http/middleware.py`.
References:
  - Guide: `documentation/routing.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re
from typing import Any, Callable, Dict, List, Optional, Union

#: A route declared by the application itself, in `routes/*.py` or by a
#: provider. This is what a developer wrote down and expects to see listed.
APP_ORIGIN: str = "app"

#: A route attached by the framework: the health probes, the metrics scrape,
#: the MSR JSON manifest, the static-asset mount. These used to be appended
#: straight onto the ASGI route table, so they answered requests while no
#: listing could see them. They are registered here instead, marked, so the
#: router is the single record of everything that answers.
ENGINE_ORIGIN: str = "engine"


class RouteEntry:
    def __init__(self, methods: List[str], uri: str, action: Any, prefix: str = "", name_prefix: str = "", middleware: Optional[List[Any]] = None):
        self.methods = [m.upper() for m in methods]
        # Always produce an absolute path: a group prefix given without a
        # leading slash ("api") must not yield "api/posts" — Starlette asserts
        # on routes that do not start with "/".
        combined = "/".join(p for p in (prefix.strip("/"), uri.strip("/")) if p)
        self.uri = f"/{combined}" if combined else "/"
        self.action = action
        self._name = ""
        self.name_prefix = name_prefix
        self.middleware_list = middleware or []
        self._module: Optional[str] = None
        #: Which layer attached this route: `APP_ORIGIN` or `ENGINE_ORIGIN`.
        self.origin: str = APP_ORIGIN
        #: Dotted module that attached an engine route, for attribution.
        self.provider: Optional[str] = None
        #: True when `action` is an ASGI sub-application mounted on a prefix
        #: rather than an endpoint, which is how static assets are served.
        self.is_mount: bool = False

    def name(self, name: str) -> 'RouteEntry':
        self._name = f"{self.name_prefix}{name}"
        return self

    def middleware(self, *middleware) -> 'RouteEntry':
        self.middleware_list.extend(middleware)
        return self

    def module(self, module_name: str) -> 'RouteEntry':
        self._module = module_name
        return self

    def describe(self) -> Dict[str, Any]:
        """Return the route as a plain mapping, for listings and JSON output.

        Returns:
            The HTTP methods, URI, route name, declared middleware names, the
            layer that attached it and, for an engine route, the module that
            did.
        """
        return {
            "method": "|".join(self.methods),
            "uri": self.uri,
            "name": self._name or None,
            "middleware": [
                entry if isinstance(entry, str) else getattr(entry, "__name__", str(entry))
                for entry in self.middleware_list
            ],
            "origin": self.origin,
            "provider": self.provider,
            "mount": self.is_mount,
        }


class Router:
    def __init__(self, container: Optional[Any] = None):
        self.container = container
        self.routes: List[RouteEntry] = []
        #: Bumped on every registration so the kernel can cache the built
        #: Starlette app and rebuild only when the route table changes.
        self._version = 0
        self._named_routes: Dict[str, RouteEntry] = {}
        self._group_stack: List[Dict[str, Any]] = []
        #: Engine routes by URI, so registering twice is a no-op instead of a
        #: duplicate. The kernel re-registers on every rebuild.
        self._engine_index: Dict[str, RouteEntry] = {}

    def add_route(self, methods: Union[str, List[str]], uri: str, action: Any) -> RouteEntry:
        if isinstance(methods, str):
            methods = [methods]

        prefix = "".join([g.get("prefix", "") for g in self._group_stack])
        name_prefix = "".join([g.get("name", "") for g in self._group_stack])

        middleware = []
        for g in self._group_stack:
            if "middleware" in g:
                m_item = g["middleware"]
                if isinstance(m_item, list):
                    middleware.extend(m_item)
                else:
                    middleware.append(m_item)

        route = RouteEntry(methods, uri, action, prefix=prefix, name_prefix=name_prefix, middleware=middleware)
        self.routes.append(route)
        self._version += 1
        return route

    def get(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route(["GET", "HEAD"], uri, action)

    def post(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("POST", uri, action)

    def put(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("PUT", uri, action)

    def patch(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("PATCH", uri, action)

    def delete(self, uri: str, action: Any) -> RouteEntry:
        return self.add_route("DELETE", uri, action)

    def group(self, callback: Callable, prefix: str = "", middleware: Optional[Union[str, List[str]]] = None, name: str = "") -> None:
        group_attrs = {}
        if prefix:
            group_attrs["prefix"] = prefix
        if middleware:
            group_attrs["middleware"] = middleware
        if name:
            group_attrs["name"] = name

        self._group_stack.append(group_attrs)
        try:
            callback()
        finally:
            self._group_stack.pop()

    def resource(self, name: str, controller: Any, write_middleware: Optional[Union[str, List[str]]] = None) -> None:
        """Register the standard 7 CRUD routes.

        `write_middleware` — e.g. "auth" — is applied only to the
        state-changing actions (store/update/destroy), not to the read-only
        ones (index/show/create/edit), so a resource can stay publicly
        readable while still requiring a logged-in user to mutate it.
        """
        self.get(f"/{name}", [controller, "index"]).name(f"{name}.index")
        self.get(f"/{name}/create", [controller, "create"]).name(f"{name}.create")
        store = self.post(f"/{name}", [controller, "store"]).name(f"{name}.store")
        self.get(f"/{name}/{{id}}", [controller, "show"]).name(f"{name}.show")
        self.get(f"/{name}/{{id}}/edit", [controller, "edit"]).name(f"{name}.edit")
        update = self.put(f"/{name}/{{id}}", [controller, "update"]).name(f"{name}.update")
        destroy = self.delete(f"/{name}/{{id}}", [controller, "destroy"]).name(f"{name}.destroy")
        if write_middleware:
            mw = write_middleware if isinstance(write_middleware, list) else [write_middleware]
            for route in (store, update, destroy):
                route.middleware(*mw)

    def api_resource(self, name: str, controller: Any, write_middleware: Optional[Union[str, List[str]]] = None) -> None:
        """Same as `resource()` but without the HTML-only create/edit routes."""
        self.get(f"/{name}", [controller, "index"]).name(f"{name}.index")
        store = self.post(f"/{name}", [controller, "store"]).name(f"{name}.store")
        self.get(f"/{name}/{{id}}", [controller, "show"]).name(f"{name}.show")
        update = self.put(f"/{name}/{{id}}", [controller, "update"]).name(f"{name}.update")
        destroy = self.delete(f"/{name}/{{id}}", [controller, "destroy"]).name(f"{name}.destroy")
        if write_middleware:
            mw = write_middleware if isinstance(write_middleware, list) else [write_middleware]
            for route in (store, update, destroy):
                route.middleware(*mw)

    #: Methods reported for a mount, which answers whatever its sub-application does.
    MOUNT_METHODS: List[str] = ["ANY"]

    def add_engine_route(self, methods: List[str], uri: str, endpoint: Any, *, name: str, provider: str) -> RouteEntry:
        """Register a route the framework itself attaches.

        Args:
            methods: HTTP methods the route answers.
            uri: Absolute path, taken as given - group prefixes do not apply.
            endpoint: A ready-made ASGI endpoint, dispatched outside the
                application middleware stack.
            name: Route name, used by `url_for()` and by listings.
            provider: Dotted module attaching it, for attribution.

        Returns:
            The registered entry, or the one already registered for this URI.
        """
        return self._add_engine_entry(methods, uri, endpoint, name, provider, is_mount=False)

    def add_engine_mount(self, uri: str, asgi_app: Any, *, name: str, provider: str) -> RouteEntry:
        """Register an ASGI sub-application the framework mounts on a prefix.

        Args:
            uri: Prefix to mount on.
            asgi_app: The sub-application handling everything under it.
            name: Mount name, used by listings.
            provider: Dotted module attaching it, for attribution.

        Returns:
            The registered entry, or the one already registered for this URI.
        """
        return self._add_engine_entry(self.MOUNT_METHODS, uri, asgi_app, name, provider, is_mount=True)

    def _add_engine_entry(
        self, methods: List[str], uri: str, action: Any, name: str, provider: str, is_mount: bool
    ) -> RouteEntry:
        """Append a marked engine entry, once per URI."""
        existing = self._engine_index.get(uri)
        if existing is not None:
            return existing

        route = RouteEntry(methods, uri, action)
        route.origin = ENGINE_ORIGIN
        route.provider = provider
        route.is_mount = is_mount
        route.name(name)
        self.routes.append(route)
        self._engine_index[uri] = route
        self._version += 1
        return route

    def application_routes(self) -> List[RouteEntry]:
        """Return the routes the application declared."""
        return [route for route in self.routes if route.origin == APP_ORIGIN]

    def engine_routes(self) -> List[RouteEntry]:
        """Return the routes the framework attached."""
        return [route for route in self.routes if route.origin == ENGINE_ORIGIN]

    def claimed_uris(self) -> set:
        """Return the URIs the application's own routes answer.

        An engine route never takes a path the application declared: the
        application's definition of `/health` is the one that must win.
        """
        return {route.uri for route in self.application_routes()}

    def clear_engine_routes(self) -> int:
        """Drop every engine route, so they can be registered from scratch.

        Configuration decides which of them exist, and a flag flipped after
        boot has to be able to take one away as well as add one.

        Returns:
            How many entries were removed.
        """
        removed = len(self._engine_index)
        if not removed:
            return 0
        self.routes = [route for route in self.routes if route.origin != ENGINE_ORIGIN]
        self._engine_index.clear()
        self._version += 1
        return removed

    def url_for(self, name: str, **params) -> str:
        from urllib.parse import quote, urlencode

        for r in self.routes:
            if r._name == name:
                url = r.uri
                used = set()
                for k, v in params.items():
                    placeholder = f"{{{k}}}"
                    if placeholder in url:
                        url = url.replace(placeholder, quote(str(v), safe=""))
                        used.add(k)
                leftover = re.findall(r"\{(\w+)\}", url)
                if leftover:
                    raise ValueError(
                        f"Missing parameters {leftover} for route [{name}]."
                    )
                extra = {k: v for k, v in params.items() if k not in used}
                if extra:
                    url += "?" + urlencode(extra)
                return url

        # An unknown name used to be returned as the literal path `/{name}`,
        # so `route("posts.index")` rendered the dead link `/posts.index` and
        # a typo in a template produced silently broken navigation that only a
        # human clicking around would ever find.
        raise KeyError(f"No route named [{name}].")

    def absolute_url_for(self, name: str, **params) -> str:
        """`url_for()` prefixed with `app.APP_URL`.

        This is the only reader of `APP_URL`, which was declared in
        `config/app.py` and never used by anything — a setting the developer
        could change with no effect anywhere.
        """
        path = self.url_for(name, **params)
        try:
            from craft.facades import Config

            base = Config.get("app.APP_URL", "") or ""
        except Exception:
            base = ""
        return f"{base.rstrip('/')}{path}" if base else path
