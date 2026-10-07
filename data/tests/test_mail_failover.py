"""Mail failover and quotas: a provider outage or cap does not lose a message."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

from craft.cache.manager import CacheManager
from craft.mail.mailable import Mailable
from craft.mail.manager import MailManager
from craft.orm.tenancy import TenantManager


class _Config:
    def __init__(self, data):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _App:
    def __init__(self, data):
        self._config = _Config(data)
        self._cache = CacheManager()

    def make(self, name):
        if name == "config":
            return self._config
        if name == "cache":
            return self._cache
        raise KeyError(name)


class _Driver:
    def __init__(self, ok=True, raises=False):
        self.ok = ok
        self.raises = raises
        self.calls = 0

    def send(self, message):
        self.calls += 1
        if self.raises:
            raise RuntimeError("provider is down")
        return self.ok


def _manager(mailers=None, default="primary"):
    data = {
        "mail.default": default,
        "mail.from_address": {"address": "noreply@example.com", "name": "Example"},
        "mail.mailers": mailers if mailers is not None else {
            "primary": {"transport": "log", "fallback": "backup"},
            "backup": {"transport": "log"},
        },
    }
    return MailManager(_App(data))


def _message():
    return Mailable().to("user@example.com").with_subject("Hi").text("Hello")


def test_a_failed_mailer_hands_the_message_to_its_fallback():
    manager = _manager()
    primary, backup = _Driver(ok=False), _Driver()
    manager.set_mailer("primary", primary)
    manager.set_mailer("backup", backup)

    assert manager.send_mailable(_message()) is True
    assert primary.calls == 1 and backup.calls == 1


def test_a_mailer_that_raises_still_fails_over():
    manager = _manager()
    manager.set_mailer("primary", _Driver(raises=True))
    backup = _Driver()
    manager.set_mailer("backup", backup)

    assert manager.send_mailable(_message()) is True
    assert backup.calls == 1


def test_when_every_mailer_fails_the_send_is_refused():
    manager = _manager()
    manager.set_mailer("primary", _Driver(ok=False))
    manager.set_mailer("backup", _Driver(ok=False))
    assert manager.send_mailable(_message()) is False


def test_a_mailer_over_its_quota_is_skipped_for_the_fallback():
    manager = _manager({
        "primary": {"transport": "log", "fallback": "backup",
                    "quota": {"limit": 2, "window": 3600, "per_tenant": False}},
        "backup": {"transport": "log"},
    })
    primary, backup = _Driver(), _Driver()
    manager.set_mailer("primary", primary)
    manager.set_mailer("backup", backup)

    for _ in range(3):
        assert manager.send_mailable(_message()) is True

    assert primary.calls == 2          # the cap held
    assert backup.calls == 1           # the third message failed over


def test_every_mailer_over_quota_refuses_the_send():
    manager = _manager({
        "primary": {"transport": "log",
                    "quota": {"limit": 1, "window": 3600, "per_tenant": False}},
    })
    manager.set_mailer("primary", _Driver())

    assert manager.send_mailable(_message()) is True
    assert manager.send_mailable(_message()) is False


def test_a_per_tenant_quota_does_not_charge_another_tenant():
    manager = _manager({
        "primary": {"transport": "log",
                    "quota": {"limit": 1, "window": 3600, "per_tenant": True}},
    })
    primary = _Driver()
    manager.set_mailer("primary", primary)

    tenant_a, tenant_b = str(uuid.uuid4()), str(uuid.uuid4())
    TenantManager().bind(tenant_a)
    try:
        assert manager.send_mailable(_message()) is True
        assert manager.send_mailable(_message()) is False   # A is capped
    finally:
        TenantManager().bind(None)

    TenantManager().bind(tenant_b)
    try:
        assert manager.send_mailable(_message()) is True    # B has its own quota
    finally:
        TenantManager().bind(None)
