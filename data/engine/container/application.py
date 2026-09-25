"""
Container / Application — IoC container, singleton resolution, autowiring,
and the `Application` bootstrap that boots providers and claims the global
container instance.
Category: Core Framework (Service Container).
Relations:
  - Resolved by facades (`engine/facades/base.py`) and models (`engine/orm/model.py`)
    via `Container.getInstance()`.
  - Boots service providers (`engine/providers/`) which register the
    framework's other subsystems (db, router, view, auth, ...).
References:
  - Guide: `documentation/container.md`
  - Skill: `craft-development` (workspace root, outside this repository)
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import inspect
import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

# Importing the package installs the `craft.*` -> `engine.*` import alias.
import engine  # noqa: F401


#: Per-request cache of `scoped()` bindings. A ContextVar rather than a
#: container attribute: requests run concurrently on a thread pool, so a shared
#: dict handed one request's (and one tenant's) instance to the next.
_request_scope: ContextVar[Optional[Dict[str, Any]]] = ContextVar("craft_request_scope", default=None)


class Container:
    """Inversion-of-Control container supporting bindings, singletons, scoped instances and auto-resolution."""

    _instance: Optional['Container'] = None

    def __init__(self):
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._scoped_instances: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}
        # Constructing a container deliberately does NOT claim the global
        # singleton. It used to, which meant building a second container
        # anywhere — a test fixture, a worker, a tenant-scoped app — silently
        # repointed every `Container.getInstance()` call in the process at it.
        # Claim it explicitly with `make_current()` or `scoped()`.

    @classmethod
    def getInstance(cls) -> 'Container':
        if cls._instance is None:
            cls._instance = Container()
        return cls._instance

    @classmethod
    def setInstance(cls, container: Optional['Container']) -> None:
        cls._instance = container

    def make_current(self) -> 'Container':
        """Make this container the one `getInstance()` returns."""
        Container._instance = self
        return self

    @classmethod
    @contextmanager
    def scoped_instance(cls, container: Optional['Container'] = None):
        """Temporarily swap the global container, restoring it on exit.

            with Container.scoped_instance(tenant_app):
                ...  # facades and models resolve from tenant_app

        Not to be confused with `scoped()`, which registers a request-scoped
        binding.
        """
        previous = cls._instance
        cls._instance = container
        try:
            yield container
        finally:
            cls._instance = previous

    def bind(self, abstract: Union[str, Type], concrete: Optional[Union[Callable, Type, str]] = None, shared: bool = False) -> None:
        key = self._normalize_key(abstract)
        # A class bound to itself builds itself; its normalized key is a string
        # that would resolve back to this same binding forever.
        if concrete is None:
            concrete = abstract

        self._bindings[key] = {
            "concrete": concrete,
            "shared": shared,
        }

    def singleton(self, abstract: Union[str, Type], concrete: Optional[Union[Callable, Type, str]] = None) -> None:
        self.bind(abstract, concrete, shared=True)

    def instance(self, abstract: Union[str, Type], instance: Any) -> None:
        key = self._normalize_key(abstract)
        self._instances[key] = instance

    def scoped(self, abstract: Union[str, Type], concrete: Optional[Union[Callable, Type, str]] = None) -> None:
        key = self._normalize_key(abstract)
        self._bindings[key] = {
            "concrete": concrete or abstract,
            "shared": False,
            "scoped": True,
        }

    def alias(self, abstract: Union[str, Type], alias: str) -> None:
        key = self._normalize_key(abstract)
        self._aliases[alias] = key

    def make(self, abstract: Union[str, Type], parameters: Optional[Dict[str, Any]] = None) -> Any:
        key = self._normalize_key(abstract)

        # Resolve alias if present
        while key in self._aliases:
            key = self._aliases[key]

        # Return cached singleton instance
        if key in self._instances:
            return self._instances[key]

        # Return cached scoped instance
        scoped_key, scoped_store = self._scoped_slot(key)
        if scoped_key in scoped_store:
            return scoped_store[scoped_key]

        binding = self._bindings.get(key)
        if binding:
            concrete = binding["concrete"]
            shared = binding.get("shared", False)
            is_scoped = binding.get("scoped", False)

            if callable(concrete) and not inspect.isclass(concrete):
                obj = concrete(self)
            elif isinstance(concrete, str):
                obj = self.make(concrete, parameters)
            elif inspect.isclass(concrete):
                obj = self._build(concrete, parameters)
            else:
                obj = concrete

            if shared:
                self._instances[key] = obj
            elif is_scoped:
                scoped_store[scoped_key] = obj

            return obj

        # Attempt auto-resolution for un-bound classes
        if inspect.isclass(abstract):
            return self._build(abstract, parameters)
        elif isinstance(abstract, str):
            cls = self._import_dotted(abstract)
            if cls is not None:
                return self._build(cls, parameters)

        raise KeyError(self._unbound_message(key))

    @staticmethod
    def _import_dotted(path: str) -> Any:
        """Import the class a dotted path names, or None if there is no such class.

        Only "this module or name does not exist" means "not resolvable". An
        error raised while importing a module that does exist - a syntax error,
        a failing import inside it - propagates: it used to be swallowed and
        reported as "not bound", hiding the real fault.
        """
        module_name, _, class_name = path.rpartition(".")
        if not module_name:
            return None
        try:
            module = __import__(module_name, fromlist=[class_name])
        except ModuleNotFoundError as exc:
            if exc.name and (module_name == exc.name or module_name.startswith(exc.name + ".")):
                return None
            raise
        cls = getattr(module, class_name, None)
        return cls if inspect.isclass(cls) else None

    def _unbound_message(self, key: str) -> str:
        """Describe an unresolvable key, with the closest bound names."""
        from engine.support.diagnostics import closest, describe

        known = set(self._bindings) | set(self._instances) | set(self._aliases)
        parts = [
            describe("CONTAINER_UNBOUND", key=key),
            describe("CONTAINER_CLOSEST", closest=closest(key, sorted(known), limit=3)),
        ]
        if not isinstance(self, Application):
            parts.append(describe("CONTAINER_NOT_BOOTED"))
        return " ".join(parts)

    def _build(self, concrete: Type, parameters: Optional[Dict[str, Any]] = None) -> Any:
        parameters = parameters or {}
        try:
            init_method = concrete.__init__
        except AttributeError:
            return concrete()

        if init_method is object.__init__:
            return concrete()

        signature = inspect.signature(init_method)
        args = []
        kwargs = {}

        for param_name, param in signature.parameters.items():
            if param_name == "self":
                continue

            if param_name in parameters:
                kwargs[param_name] = parameters[param_name]
                continue

            cause: Optional[Exception] = None
            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation
                try:
                    kwargs[param_name] = self.make(param_type)
                    continue
                except (KeyError, ValueError, TypeError) as exc:
                    cause = exc

            if param.default != inspect.Parameter.empty:
                kwargs[param_name] = param.default
            else:
                from engine.support.diagnostics import describe

                raise ValueError(describe(
                    "CONTAINER_PARAMETER_UNRESOLVABLE", parameter=param_name,
                    annotation=getattr(param.annotation, "__name__", param.annotation), owner=concrete.__name__,
                )) from cause

        return concrete(*args, **kwargs)

    def _normalize_key(self, abstract: Union[str, Type]) -> str:
        if inspect.isclass(abstract):
            return f"{abstract.__module__}.{abstract.__qualname__}"
        return str(abstract)

    def _scoped_slot(self, key: str) -> Tuple[str, Dict[str, Any]]:
        """Return the cache key and store for a scoped binding.

        Inside a request scope the store belongs to that request; outside one
        (console, worker, tests) it is this container's own dict.
        """
        store = _request_scope.get()
        if store is None:
            return key, self._scoped_instances
        return f"{id(self)}:{key}", store

    @staticmethod
    def begin_request_scope() -> Token:
        """Open a fresh scoped-instance cache for the current request.

        Returns:
            The token to pass to `end_request_scope`.
        """
        return _request_scope.set({})

    @staticmethod
    def end_request_scope(token: Token) -> None:
        """Discard the request's scoped instances and restore the outer scope.

        Args:
            token: The token returned by `begin_request_scope`.
        """
        _request_scope.reset(token)

    def forget_scoped_instances(self) -> None:
        """Drop the scoped instances visible from the current context."""
        store = _request_scope.get()
        if store is None:
            self._scoped_instances.clear()
            return
        prefix = f"{id(self)}:"
        for scoped_key in [k for k in store if k.startswith(prefix)]:
            del store[scoped_key]


class Application(Container):
    """Application bootstrap class representing the core framework context."""

    def __init__(self, base_path: Optional[str] = None, bind_as_global: Optional[bool] = None):
        """Bootstrap an application.

        `bind_as_global` controls whether this application becomes the one
        `Container.getInstance()` returns:

        * ``None`` (default) — claim it unless another *Application* already
          holds it. The real application wins; a scratch application built
          later (test fixture, worker, tenant scope) leaves the global alone.
          A bare fallback `Container` — which `getInstance()` creates when
          something resolves the container before boot — is always displaced,
          otherwise it would permanently shadow the real app's bindings.
        * ``True`` / ``False`` — claim it, or never claim it.

        Use ``Container.scoped_instance(app)`` to swap the global one temporarily.
        """
        super().__init__()
        self.base_path = base_path or os.getcwd()
        self._providers: List[Any] = []
        self._booted = False

        if bind_as_global is None:
            bind_as_global = not isinstance(Container._instance, Application)
        if bind_as_global:
            self.make_current()

        # Register self as container instance
        self.instance("app", self)
        self.instance(Container, self)
        self.instance(Application, self)

    def load_environment(self, filename: str = ".env") -> None:
        """Load the project's `.env` file into the process environment."""
        from engine.config.repository import load_dotenv

        load_dotenv(os.path.join(self.base_path, filename))

    def register_config(self) -> None:
        from engine.config.repository import ConfigRepository

        # .env must be loaded before config modules read it via env().
        self.load_environment()
        config_repo = ConfigRepository(os.path.join(self.base_path, "config"))
        self.instance("config", config_repo)

    def register_provider(self, provider_class: Type) -> Any:
        provider = provider_class(self)
        if hasattr(provider, "register"):
            provider.register()
        self._providers.append(provider)
        if self._booted and hasattr(provider, "boot"):
            provider.boot()
        return provider

    def boot(self) -> None:
        if self._booted:
            return

        for provider in self._providers:
            if hasattr(provider, "boot"):
                provider.boot()

        self._booted = True
