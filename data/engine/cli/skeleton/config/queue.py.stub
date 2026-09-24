"""Queue configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.config import env

default = env("QUEUE_CONNECTION", "sync")

connections = {
    "sync": {
        "driver": "sync",
    },
    "database": {
        "driver": "database",
        "table": "jobs",
        "retry_after": 90,
    },
    "redis": {
        "driver": "redis",
        "host": env("REDIS_HOST", "127.0.0.1"),
        "port": env("REDIS_PORT", 6379),
        "queue": "default",
    },
}
