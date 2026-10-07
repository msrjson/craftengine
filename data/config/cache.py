"""Cache configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

default = env("CACHE_DRIVER", "memory")

stores = {
    "memory": {
        "driver": "memory",
        # The in-process store is bounded so a long-lived worker cannot grow it
        # without limit. 0 means unbounded; over the bound the oldest entry goes.
        "max_entries": env("CACHE_MEMORY_MAX_ENTRIES", 1000),
    },
    "file": {
        "driver": "file",
        "path": "storage/framework/cache",
    },
    "redis": {
        "driver": "redis",
        "host": env("REDIS_HOST", "127.0.0.1"),
        "port": env("REDIS_PORT", 6379),
    },
}
