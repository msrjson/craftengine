"""Framework Service Providers for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import importlib

from engine.providers.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    def register(self):
        from engine.orm.db import DatabaseManager
        from engine.migrations.schema import SchemaBuilder

        db_mgr = DatabaseManager(self.app)
        self.app.instance("db", db_mgr)
        self.app.instance("schema", SchemaBuilder(db_mgr))

    def boot(self):
        self.app.make("db").boot()
        self.listen_for_request_end()

    def listen_for_request_end(self) -> None:
        """Return the request's pooled connection when the kernel announces its end.

        The listener runs on the worker thread that borrowed the connection.
        """
        from engine.events.lifecycle import RequestTerminated

        db = self.app.make("db")
        self.app.make("events").listen(RequestTerminated, lambda _event: db.release())


class PostgresServiceProvider(ServiceProvider):
    """Bindings whose full behaviour needs PostgreSQL.

    Registered unconditionally on every driver. Each service raises through
    `Dialect.require` if used where it cannot work, which is deliberately
    louder than not registering it: a missing binding produces a container
    error that reads like a framework bug, while `require` names the driver,
    the capability and the way out.
    """

    def register(self):
        from engine.orm.locks import LockManager
        from engine.orm.tenancy import TenantManager
        from engine.queue.listener import Broadcaster

        self.app.singleton("lock", lambda c: LockManager(c))
        self.app.singleton("tenant", lambda c: TenantManager(c))
        self.app.singleton("broadcast", lambda c: Broadcaster(c))


class RouterServiceProvider(ServiceProvider):
    def register(self):
        from engine.http.router import Router
        self.app.singleton("router", lambda c: Router(c))


class ViewServiceProvider(ServiceProvider):
    def register(self):
        from engine.view.forge import Forge
        self.app.singleton("view", lambda c: Forge(c))


class AuthServiceProvider(ServiceProvider):
    def register(self):
        from engine.auth.access import AccessResolver
        from engine.auth.gate import GateManager
        from engine.auth.manager import AuthManager
        from engine.auth.password import Hash

        self.app.instance("auth", AuthManager(self.app))
        # `access` resolves roles, groups and permissions - including the
        # attribute conditions on a grant. The Gate consults it, and the
        # `role:`/`permission:`/`group:` middleware go through it too, so there
        # is exactly one implementation of "can this user do this?".
        self.app.instance("access", AccessResolver(self.app))
        self.app.instance("gate", GateManager(self.app))
        self.app.instance("hash", Hash())

        # The menu is data guarded by the same rules as the routes, so the
        # navigation and the router cannot describe different realities.
        from engine.support.navigation import Navigation

        self.app.instance("nav", Navigation(self.app))


class EventServiceProvider(ServiceProvider):
    def register(self):
        from engine.events.dispatcher import EventDispatcher
        self.app.instance("events", EventDispatcher(self.app))


class InternalProxyServiceProvider(ServiceProvider):
    """Bind the internal proxy that routes module-to-module calls in memory."""

    def register(self) -> None:
        """Register the proxy as the `proxy` singleton, also resolvable by its class."""
        from engine.container.internal_proxy import InternalProxy

        self.app.singleton("proxy", lambda container: InternalProxy(container))
        self.app.alias("proxy", f"{InternalProxy.__module__}.{InternalProxy.__qualname__}")


class QueueServiceProvider(ServiceProvider):
    def register(self):
        from engine.queue.manager import QueueManager
        self.app.singleton("queue", lambda c: QueueManager(c))


class LoggingServiceProvider(ServiceProvider):
    """Configure the `craft` logger from `config/logging.py`.

    This used to be `logging.getLogger("craft")` and nothing else, so the whole
    config file - channels, level, path, retention - was decoration: setting
    `level: "error"` or pointing `path` somewhere else changed nothing, and by
    default no handler existed at all, meaning framework warnings went nowhere.
    """

    def register(self):
        import logging

        self.app.singleton("log", lambda c: self._configure(logging.getLogger("craft")))

    def _configure(self, logger):
        import logging
        import os

        config = self.app.make("config")
        channel_name = config.get("logging.default", "single")
        channel = config.get(f"logging.channels.{channel_name}", {}) or {}

        level = str(channel.get("level", "debug")).upper()
        logger.setLevel(getattr(logging, level, logging.DEBUG))

        # Idempotent: the binding is a singleton, but a re-registered provider
        # (tests, a second Application) must not stack duplicate handlers and
        # print every line twice.
        if any(getattr(h, "_craft_managed", False) for h in logger.handlers):
            return logger

        from engine.support.logging import RequestContextFilter, formatter_for

        handler = self._build_handler(channel, os)
        handler.setFormatter(formatter_for(channel.get("format", "text")))
        handler._craft_managed = True
        logger.addHandler(handler)
        # The filter goes on the logger, not the handler: it enriches the
        # record itself, so a project that adds a second handler or its own
        # formatter still gets the request context.
        if not any(isinstance(f, RequestContextFilter) for f in logger.filters):
            logger.addFilter(RequestContextFilter())
        return logger

    def _build_handler(self, channel, os):
        import logging
        import logging.handlers

        driver = channel.get("driver", "single")

        if driver == "stderr":
            return logging.StreamHandler()

        path = channel.get("path", "storage/logs/craft.log")
        if not os.path.isabs(path):
            path = os.path.join(self.app.base_path, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        if driver == "daily":
            return logging.handlers.TimedRotatingFileHandler(
                path, when="midnight", backupCount=int(channel.get("days", 7)),
                encoding="utf-8",
            )

        return logging.FileHandler(path, encoding="utf-8")


class CacheServiceProvider(ServiceProvider):
    def register(self):
        from engine.cache.manager import CacheManager
        self.app.instance("cache", CacheManager(self.app))


class MigratorServiceProvider(ServiceProvider):
    def register(self):
        from engine.migrations.migrator import Migrator
        self.app.instance("migrator", Migrator(self.app))


class ExceptionServiceProvider(ServiceProvider):
    def register(self):
        from engine.exceptions.handler import ExceptionHandler
        self.app.instance("exception_handler", ExceptionHandler(self.app))


class PQCServiceProvider(ServiceProvider):
    def register(self):
        from engine.security.pqc import PQC
        self.app.singleton("pqc", lambda c: PQC())


class CaptchaServiceProvider(ServiceProvider):
    def register(self):
        from engine.security.captcha import Captcha
        self.app.singleton("captcha", lambda c: Captcha())


class VaultServiceProvider(ServiceProvider):
    def register(self):
        # Lazy: constructing eagerly would demand APP_KEY at boot even for an
        # app that never stores a secret. `container.make("vault")` on first
        # use is where VaultKeyMissingError should actually surface.
        from engine.security.vault import Vault
        self.app.singleton("vault", lambda c: Vault())


class SignerServiceProvider(ServiceProvider):
    def register(self):
        # Lazy, same reasoning as VaultServiceProvider.
        from engine.auth.signer import Signer
        self.app.singleton("signer", lambda c: Signer())


class FirewallServiceProvider(ServiceProvider):
    def register(self):
        from engine.security.firewall import Firewall
        self.app.singleton("firewall", lambda c: Firewall(c))


class HoneypotServiceProvider(ServiceProvider):
    def register(self):
        from engine.security.honeypot import HoneypotService
        self.app.singleton("honeypot", lambda c: HoneypotService(c))


class AntiSpamServiceProvider(ServiceProvider):
    def register(self):
        from engine.security.antispam import AntiSpamService
        self.app.singleton("antispam", lambda c: AntiSpamService(c))


class FrameworkSubsystemsServiceProvider(ServiceProvider):
    def register(self):
        from engine.modules.manager import ModuleManager
        from engine.plugins.manager import PluginManager
        from engine.schedule.manager import ScheduleManager
        from engine.support.settings import SettingManager

        self.app.singleton("module", lambda c: ModuleManager())
        self.app.singleton("plugin", lambda c: PluginManager())
        self.app.singleton("setting", lambda c: SettingManager())
        self.app.singleton("schedule", lambda c: ScheduleManager(c))

    def boot(self):
        """Bridge plugin hooks onto the event bus, then load enabled plugins.

        Done in `boot` rather than `register` because it needs the dispatcher,
        which another provider registers - `register` runs before every binding
        exists, `boot` runs after all of them do.
        """
        plugins = self.app.make("plugin")
        plugins.bridge_events(self.app.make("events"))
        plugins.load_enabled(self.app.base_path, self.app)
        self._load_scheduled_tasks()

    def _load_scheduled_tasks(self):
        """Import the application's console module so declared tasks reach the scheduler.

        The application names the module in `app.console_routes`; the engine
        never imports application code by a hardcoded path. A missing module
        is fine (not every app schedules anything); a *broken* one is logged
        rather than silenced, because a typo there would otherwise mean tasks
        vanish with no signal at all.
        """
        module_path = self.app.make("config").get("app.console_routes")
        if not module_path:
            return
        try:
            register_console = importlib.import_module(str(module_path)).register_console
        except (ImportError, AttributeError):
            return
        except Exception:
            import logging

            logging.getLogger("craft").warning(
                "routes/console.py failed to import; no scheduled tasks registered",
                exc_info=True,
            )
            return

        try:
            register_console()
        except Exception:
            import logging

            logging.getLogger("craft").warning(
                "register_console() raised; scheduled tasks may be incomplete",
                exc_info=True,
            )


class MediaServiceProvider(ServiceProvider):
    """Register Image and Media services in the application container."""

    def register(self):
        from engine.media.manager import ImageManager, MediaManager

        self.app.singleton("image", lambda c: ImageManager(c))
        self.app.singleton("media", lambda c: MediaManager(c))


class AIServiceProvider(ServiceProvider):
    """Register AI SDK and Agent Orchestrator in the application container."""

    def register(self):
        from engine.ai.manager import AIManager

        self.app.singleton("ai", lambda c: AIManager(c))


class AgentServiceProvider(ServiceProvider):
    """Register Agent Manager and MCP Server in the application container."""

    def register(self):
        from engine.agents.manager import AgentManager

        self.app.singleton("agent", lambda c: AgentManager(c))


class StorageServiceProvider(ServiceProvider):
    """Register Storage filesystem manager in the application container."""

    def register(self):
        from engine.storage.manager import StorageManager

        self.app.singleton("storage", lambda c: StorageManager(c))


class MailServiceProvider(ServiceProvider):
    """Register Mail and notification manager in the application container."""

    def register(self):
        from engine.mail.manager import MailManager

        self.app.singleton("mail", lambda c: MailManager(c))
