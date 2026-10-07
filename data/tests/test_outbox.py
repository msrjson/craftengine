"""The transactional outbox: committed message, at-least-once delivery."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.events.outbox import Outbox
from craft.orm.tenancy import TenantManager, current_tenant_id

_SUFFIX = uuid.uuid4().hex[:8]


@pytest.fixture(autouse=True)
def clean_handlers():
    Outbox.clear_handlers()
    yield
    Outbox.clear_handlers()


@pytest.fixture
def outbox(migrated_database):
    return Outbox(migrated_database)


def _topic(name):
    return f"test.{name}.{_SUFFIX}"


def _row(outbox, topic):
    rows = (
        outbox.db.table("outbox_messages")
        .where("topic", topic)
        .order_by("id")
        .limit(1)
        .get()
    )
    return rows[0]


def test_a_published_message_is_relayed_to_its_handler(outbox):
    received = []
    Outbox.on(_topic("delivered"), received.append)
    outbox.publish(_topic("delivered"), {"order": 1})

    assert outbox.relay() == 1
    assert received[0].payload == {"order": 1}
    # Already published: a second relay does nothing.
    assert outbox.relay() == 0


def test_a_rollback_discards_the_message(migrated_database, outbox):
    topic = _topic("rolled_back")

    def work():
        outbox.publish(topic, {"order": 2})
        raise RuntimeError("the transaction rolled back")

    with pytest.raises(RuntimeError):
        migrated_database.make("db").transaction(work)

    assert all(str(row["topic"]) != topic for row in outbox.due())


def test_a_message_with_no_handler_is_consumed_not_retried(outbox):
    topic = _topic("unheard")
    outbox.publish(topic, {})
    outbox.relay()
    # A second relay finds nothing due: the message will not spin forever.
    assert all(str(row["topic"]) != topic for row in outbox.due())
    assert _row(outbox, topic)["last_error"] == "no_handler"


def test_a_failing_handler_reschedules_with_backoff(outbox):
    def boom(message):
        raise RuntimeError("handler is broken")

    topic = _topic("failing")
    Outbox.on(topic, boom)
    outbox.publish(topic, {})

    assert outbox.relay() == 0
    # Not due again yet: the retry is scheduled in the future.
    assert all(str(row["topic"]) != topic for row in outbox.due())

    row = _row(outbox, topic)
    assert int(row["attempts"]) == 1
    assert "handler is broken" in str(row["last_error"])


def test_the_handler_runs_under_the_message_tenant(migrated_database):
    seen = []
    topic = _topic("tenanted")
    tenant = str(uuid.uuid4())
    Outbox.on(topic, lambda message: seen.append(current_tenant_id()))

    TenantManager(migrated_database).bind(tenant)
    try:
        Outbox(migrated_database).publish(topic, {})
    finally:
        TenantManager(migrated_database).bind(None)

    Outbox(migrated_database).relay()
    assert seen == [tenant]
    # The relay binds the message's tenant and releases it again.
    assert current_tenant_id() is None
