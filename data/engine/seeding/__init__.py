"""
Seeder — Base class for `database/seeders/*`; subclasses implement `run()` and
can `call()` other seeders.
Category: Core Framework (Seeding).
Relations:
  - Invoked by `dev.py db seed` / `dev.py migrate --seed`
    (`engine/cli/app.py`); resolves `db` via `Container.getInstance()`.
References:
  - Guide: `documentation/migrations.md#seeders`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, List, Type, Union


class Seeder:
    """Base seeder. Subclasses implement `run()`."""

    def __init__(self, app: Any = None):
        self.app = app
        self.command_output: List[str] = []

    @property
    def db(self) -> Any:
        if self.app is not None:
            return self.app.make("db")
        from engine.container.application import Container

        return Container.getInstance().make("db")

    def run(self) -> None:  # pragma: no cover - overridden by user seeders
        raise NotImplementedError("Seeder must implement run().")

    def call(self, seeders: Union[Type["Seeder"], List[Type["Seeder"]]]) -> None:
        """Invoke one or many other seeders, honouring `SEED_ONCE`."""
        if not isinstance(seeders, (list, tuple)):
            seeders = [seeders]
        from engine.seeding.ledger import SeedLedger, once_key

        for seeder_class in seeders:
            instance = seeder_class(self.app) if _accepts_app(seeder_class) else seeder_class()
            instance.app = instance.app or self.app
            key = once_key(seeder_class)
            ledger = SeedLedger(self.app)
            if key and ledger.has(key):
                self.command_output.append(f"Skipped (already seeded): {seeder_class.__name__}")
                continue
            instance.run()
            if key:
                ledger.record(key, note="ran via Seeder.call()")
            self.command_output.append(f"Seeded: {seeder_class.__name__}")

    def info(self, message: str) -> None:
        self.command_output.append(message)


def _accepts_app(seeder_class: Type[Seeder]) -> bool:
    import inspect

    try:
        signature = inspect.signature(seeder_class.__init__)
    except (TypeError, ValueError):
        return False
    return len(signature.parameters) > 1


def run_seeder(name: str = "DatabaseSeeder", app: Any = None) -> Seeder:
    """Import and execute a seeder from `database/seeders` by class name.

    A seeder declaring `SEED_ONCE` runs at most once per node: the key is checked
    against, and then written to, the `seed_ledger` (`engine/seeding/ledger.py`).
    """
    import importlib

    from engine.seeding.ledger import SeedLedger, once_key

    module = importlib.import_module(f"database.seeders.{name}")
    seeder_class = getattr(module, name)
    seeder = seeder_class(app) if _accepts_app(seeder_class) else seeder_class()
    seeder.app = getattr(seeder, "app", None) or app

    key = once_key(seeder_class)
    ledger = SeedLedger(app)
    if key and ledger.has(key):
        seeder.info(f"Skipped (already seeded): {name}")
        return seeder
    seeder.run()
    if key:
        ledger.record(key, note="ran by release:sync / db seed")
    return seeder


__all__ = ["Seeder", "run_seeder"]
