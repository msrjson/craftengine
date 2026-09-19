"""Event service provider — register event listeners."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Event
from craft.providers import ServiceProvider


class EventServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        pass
