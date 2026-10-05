"""Extension configuration: where the application keeps its modules, plugins and themes.

The engine never names an application directory (ADR 0003, EB-02); it reads
the roots listed here, relative to the application base path. Each directory
directly under a root that holds an `extension.toml` is one extension
(ADR 0004, `documentation/extensions.md`).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

paths = ["app/modules", "app/plugins", "app/themes"]

#: Unexpected failures of one extension, inside `failure_window` seconds, that
#: take it out of service: its routes answer 503, its proxy targets are
#: refused and its listeners are skipped, while every other extension serves.
failure_threshold = env("EXTENSIONS_FAILURE_THRESHOLD", 5)
failure_window = env("EXTENSIONS_FAILURE_WINDOW", 60)

#: Seconds an extension stays out of service before one trial call is allowed.
cooldown = env("EXTENSIONS_COOLDOWN", 30)

#: Seconds between two checks of the persisted states, so an extension
#: activated from another worker (the CLI, the panel) starts serving here too.
reconcile_interval = env("EXTENSIONS_RECONCILE_INTERVAL", 5)
