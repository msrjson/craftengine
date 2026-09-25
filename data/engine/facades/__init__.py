"""Concrete Facades for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.facades.base import Facade


class Route(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "router"


class DB(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "db"


class Lock(Facade):
    """Distributed locks on database advisory locks.

    `Lock.transaction(key)` is the safe default — the database releases it at
    COMMIT or ROLLBACK, including when the process dies mid-block.
    `Lock.key(key)` is the session-scoped form for work that spans statements,
    and it must be released by the same connection that took it.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "lock"


class Tenant(Facade):
    """The current tenant — and the session variable isolation policies read.

    `Tenant.scope(tenant_id)` runs a block as one tenant and restores the
    previous one after; `Tenant.id_or_fail()` is what `TenantScoped` models
    call, so a query built with nothing bound refuses instead of silently
    matching nothing.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "tenant"


class Broadcast(Facade):
    """Publish events to listening processes over the database.

    The publish happens inside the transaction that produced the event, so a
    client cannot be told about a row that then rolls back.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "broadcast"


class Config(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "config"


class Auth(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "auth"


class Event(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "events"


class Queue(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "queue"


class Log(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "log"


class Cache(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "cache"


class Hash(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "hash"


class Vault(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "vault"


class Signer(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "signer"


class Migrator(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "migrator"


class Gate(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "gate"


class Nav(Facade):
    """The navigation registry — declare a menu, resolve it per visitor.

    `Nav.for_user(user, path)` returns only the sections and items that user
    may actually reach, so the menu never offers a link that ends in a 403.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "nav"


class Access(Facade):
    """Roles, groups and permissions — including a grant's attribute conditions.

    `Gate` answers "may this user do X?" and consults `Access` on the way.
    Reach for `Access` directly to *inspect* authorization: which roles or
    groups a user has, every permission they can reach, and `explain()` for
    why a particular permission reaches them.
    """

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "access"


class View(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "view"


class Schema(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "schema"


class Module(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "module"


class Plugin(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "plugin"


class Setting(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "setting"


class PQC(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "pqc"


class Captcha(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "captcha"


class Schedule(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "schedule"


class Firewall(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "firewall"


class Honeypot(Facade):
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "honeypot"


class AntiSpam(Facade):
    """Form honeypot, cryptographic time-trap, and heuristic anti-spam facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "antispam"


class Image(Facade):
    """Fluent image manipulation and optimization facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "image"


class Media(Facade):
    """Multimedia processing and video thumbnail facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "media"


class AI(Facade):
    """Unified AI SDK and Agent Orchestrator facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "ai"


class Agent(Facade):
    """Agent Tool registration and discovery facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "agent"


class MCP(Facade):
    """Model Context Protocol server facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "agent"


class Storage(Facade):
    """Local and Cloud Object Storage facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "storage"


class Mail(Facade):
    """Email and Notification delivery facade."""

    @classmethod
    def get_facade_accessor(cls) -> str:
        return "mail"


#: Names agents reach for in this module that live elsewhere.
_ELSEWHERE = {
    "Validator": "craft.validation.Validator(data, rules, messages)",
    "FormRequest": "craft.validation.FormRequest",
    "Request": "craft.http.request.Request",
    "Response": "craft.http.response.Response",
    "Model": "craft.orm.model.Model",
    "Session": "request.session() inside an action",
}


def __getattr__(name: str) -> object:
    """Explain an import of a facade that does not exist.

    `from craft.facades import Validator` used to fail with a bare
    ImportError; this names where the thing lives, or the closest facade.

    An ImportError rather than an AttributeError: for `from ... import`,
    Python replaces an AttributeError's message with its own generic one.

    Raises:
        AttributeError: For dunder names, so introspection behaves normally.
        ImportError: For any other name, carrying the explanation.
    """
    from engine.support.diagnostics import closest, describe

    if name.startswith("__"):
        raise AttributeError(name)
    facades = sorted(
        key for key, value in globals().items()
        if isinstance(value, type) and issubclass(value, Facade) and value is not Facade
    )
    if name in _ELSEWHERE:
        raise ImportError(describe("FACADE_IMPORT_ELSEWHERE", name=name, location=_ELSEWHERE[name]), name=name)
    raise ImportError(
        describe("FACADE_IMPORT_UNKNOWN", name=name, closest=closest(name, facades), facades=", ".join(facades)),
        name=name,
    )
