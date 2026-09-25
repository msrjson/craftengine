"""Base Facade class for Craft Framework with FacadeMeta metaclass."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Optional


class FacadeMeta(type):
    """Metaclass intercepting static method calls on Facades."""

    def __getattr__(cls, name: str) -> Any:
        # Never fabricate dunder or private attributes. Introspection — pytest
        # collection, inspect, copy, pickle — probes names like `__wrapped__`
        # and `__test__` on module-level objects. Forwarding those to the
        # container resolves it far too early: before the application boots,
        # `Container.getInstance()` builds an empty fallback container and
        # claims the global, so the real app's bindings are never visible.
        if name.startswith("_"):
            raise AttributeError(
                f"{cls.__name__} facade has no attribute '{name}'."
            )

        # A test double installed with `_swap` wins over the container, so the
        # facade points at the double for every call until `_clear_resolved`.
        swapped = cls.__dict__.get("_swapped")
        if swapped is not None:
            return getattr(swapped, name)

        from engine.container.application import Container

        app = getattr(cls, "_app", None) or Container.getInstance()
        service = app.make(cls.get_facade_accessor())
        try:
            return getattr(service, name)
        except AttributeError:
            raise AttributeError(_missing_method_message(cls, service, name)) from None


def _missing_method_message(facade: Any, service: Any, name: str) -> str:
    """Explain a call to a method the facade's service does not have.

    Names the facade, the service class and its container key, suggests the
    closest public method with its signature, and lists the rest - the facts
    needed to fix the call without opening the source.
    """
    import inspect

    from engine.support.diagnostics import closest, describe

    public = sorted(
        attr for attr in dir(service)
        if not attr.startswith("_") and callable(getattr(service, attr, None))
    )
    suggestion = closest(name, public)
    signature = ""
    if suggestion != "none":
        try:
            signature = str(inspect.signature(getattr(service, suggestion)))
        except (TypeError, ValueError):
            signature = "(...)"
    return describe(
        "FACADE_METHOD_MISSING", facade=facade.__name__, service=type(service).__name__,
        accessor=facade.get_facade_accessor(), name=name, closest=suggestion,
        signature=signature, public=", ".join(public),
    )


class Facade(metaclass=FacadeMeta):
    """Base class for expressive static Facades resolving from IoC Container."""

    _app: Any = None

    #: Test double installed by `_swap`, consulted by `FacadeMeta.__getattr__`.
    #: Read via `cls.__dict__` so a swap on one facade never leaks to another
    #: through normal attribute inheritance from this base class.
    _swapped: Any = None

    @classmethod
    def get_facade_accessor(cls) -> str:
        raise NotImplementedError("Facade must implement get_facade_accessor().")

    @classmethod
    def _clear_resolved(cls) -> None:
        """Drop any swapped double, so the facade resolves from the container
        again. Call it in test teardown — a leaked double silently rewires the
        facade for every test that runs afterwards."""
        cls._swapped = None

    @classmethod
    def _swap(cls, instance: Any) -> None:
        """Point the facade at `instance` instead of the container binding.

        This used to be `pass`: the method existed, the name promised a swap,
        and the facade went right on calling the real service — so a test that
        "mocked" a facade was silently exercising production behaviour, and
        asserting against a double that never received a call.
        """
        cls._swapped = instance
