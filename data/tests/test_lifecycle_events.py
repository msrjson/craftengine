"""Framework lifecycle events, and the plugin-hook bridge that rides on them.

The event dispatcher and the plugin hook registry were both fully implemented
and fully tested in isolation, but nothing in the framework ever emitted an
event or triggered a hook — both subsystems were inert in a running app. These
tests pin the emission points themselves, which is the part that was missing.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.events.lifecycle import (
    ModelCreated,
    ModelDeleted,
    ModelEvent,
    ModelUpdated,
    UserAuthenticated,
    UserLoggedOut,
    UserLoginFailed,
)
from craft.facades import DB, Event


@pytest.fixture
def events(migrated_database):
    """A clean dispatcher for each test, restored afterwards."""
    from craft.container.application import Container

    container = Container.getInstance()
    dispatcher = container.make("events")
    saved_listeners = dict(dispatcher._listeners)
    saved_wildcard = list(dispatcher._wildcard)
    dispatcher.flush()
    yield dispatcher
    dispatcher._listeners = saved_listeners
    dispatcher._wildcard = saved_wildcard


@pytest.fixture
def audit_user(migrated_database):
    from tests.support.models import User

    return User


@pytest.fixture
def email():
    """An address no other test uses: `users` rows persist for the session (NR-02)."""
    return f"events_{uuid.uuid4().hex[:8]}@craft.local"


@pytest.fixture
def private_db():
    """Bind the container's `db` to a private in-memory SQLite for one test.

    A test whose subject is a physical `DELETE` must not run it against the
    shared database, so the model writes land here and vanish with it.
    """
    from craft.container.application import Container
    from craft.orm.db import DatabaseManager

    container = Container.getInstance()
    original = container.make("db")
    db = DatabaseManager(config={"driver": "sqlite", "database": ":memory:"})
    db.statement(
        "CREATE TABLE gadgets (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, "
        "created_at TEXT, updated_at TEXT)"
    )
    container.instance("db", db)
    try:
        yield db
    finally:
        container.instance("db", original)


class TestModelEventsAreEmitted:
    def test_create_emits_model_created(self, events, audit_user, email):
        seen = []
        events.listen(ModelCreated, lambda e: seen.append(e))

        user = audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )

        assert len(seen) == 1
        assert seen[0].table == "users"
        assert seen[0].model.get_attribute("id") == user.get_attribute("id")

    def test_every_write_emits_its_event_and_a_base_listener_hears_all(
        self, events, private_db
    ):
        """Covers update and delete emission too — a listener on the base class
        sees all three, so they need no separate per-event test."""
        from craft.orm.model import Model

        class Gadget(Model):
            __table__ = "gadgets"
            fillable = ["name"]

        seen = []
        events.listen(ModelEvent, lambda e: seen.append(e.name))

        gadget = Gadget.create({"name": "Ev"})
        gadget.update({"name": "Renamed"})
        gadget.delete()  # nr02: private in-memory SQLite, not the shared database

        assert seen == ["model.created", "model.updated", "model.deleted"]


class TestAuthEventsAreEmitted:
    def test_successful_attempt_emits_authenticated(self, events, audit_user, email):
        audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )
        seen = []
        events.listen(UserAuthenticated, lambda e: seen.append(e))

        from craft.facades import Auth

        assert Auth.attempt({"email": email, "password": "s3cret"}) is True
        assert len(seen) == 1
        assert seen[0].user.get_attribute("email") == email

    def test_failed_attempt_emits_failure_without_the_password(self, events, audit_user):
        seen = []
        events.listen(UserLoginFailed, lambda e: seen.append(e))

        from craft.facades import Auth

        assert Auth.attempt({"email": "nobody@craft.local", "password": "hunter2"}) is False
        assert len(seen) == 1
        assert seen[0].email == "nobody@craft.local"
        # The submitted password must not ride along on the event.
        assert "hunter2" not in repr(vars(seen[0]))

    def test_a_listener_on_the_auth_base_class_can_read_user_on_any_of_them(
        self, events, audit_user, email
    ):
        """`AuthEvent` promises a user, and a failed login is still an
        `AuthEvent` — so `user` must be None there, not missing, or catching
        every auth event with one listener raises `AttributeError`."""
        from craft.events.lifecycle import AuthEvent
        from craft.facades import Auth

        seen = []
        events.listen(AuthEvent, lambda e: seen.append((e.name, e.user)))

        audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )
        Auth.attempt({"email": "nobody@craft.local", "password": "nope"})
        Auth.attempt({"email": email, "password": "s3cret"})

        names = [name for name, _ in seen]
        assert "auth.failed" in names and "auth.login" in names
        assert dict(seen)["auth.failed"] is None

    def test_logout_emits_logged_out(self, events, audit_user, email):
        audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )
        from craft.facades import Auth

        Auth.attempt({"email": email, "password": "s3cret"})

        seen = []
        events.listen(UserLoggedOut, lambda e: seen.append(e))
        Auth.logout()

        assert len(seen) == 1


class TestAFailingListenerCannotBreakTheWrite:
    """A lifecycle event fires from inside the INSERT path. A third-party
    listener raising there must not turn a successful write into a 500."""

    def test_insert_still_succeeds_when_a_listener_raises(self, events, audit_user, email):
        def explodes(event):
            raise RuntimeError("listener is broken")

        events.listen(ModelCreated, explodes)

        user = audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )

        assert user.get_attribute("id") is not None
        assert audit_user.query().where("email", email).first() is not None


class TestPluginHookBridge:
    """Plugins key hooks by string name; the framework emits typed events.
    The bridge is what connects the two without a second dispatch path."""

    def test_a_hook_registered_by_name_receives_the_event(self, events, audit_user, email):
        from craft.plugins.manager import PluginManager

        plugins = PluginManager()
        plugins.bridge_events(events)

        seen = []
        plugins.add_hook("model.created", lambda event: seen.append(event.table))

        audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )

        assert seen == ["users"]

    def test_a_broken_hook_does_not_break_the_write(self, events, audit_user, email):
        from craft.plugins.manager import PluginManager

        plugins = PluginManager()
        plugins.bridge_events(events)
        plugins.add_hook("model.created", lambda event: 1 / 0)

        user = audit_user.force_create(
            {"name": "Ev", "email": email, "password": "s3cret"}
        )
        assert user.get_attribute("id") is not None

    def test_events_without_a_name_do_not_reach_hooks(self, events):
        from craft.events.event import Event as BaseEvent
        from craft.plugins.manager import PluginManager

        plugins = PluginManager()
        plugins.bridge_events(events)
        seen = []
        plugins.add_hook("model.created", lambda event: seen.append(event))

        class Anonymous(BaseEvent):
            pass

        events.dispatch(Anonymous())
        assert seen == []
