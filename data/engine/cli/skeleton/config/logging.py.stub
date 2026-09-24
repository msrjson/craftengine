"""Logging configuration."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

from craft.config import env

# `text` is readable in a terminal; `json` is what a log platform can filter
# and aggregate on. Every record carries the identifier of the request that
# produced it either way - as a field in JSON, appended to the line in text -
# which is what makes an incident traceable once more than one instance is
# serving and their output is interleaved.
_format = env("LOG_FORMAT", "text")

channels = {
    "single": {
        "driver": "single",
        "path": "storage/logs/craft.log",
        "level": "debug",
        "format": _format,
    },
    "daily": {
        "driver": "daily",
        "path": "storage/logs/craft.log",
        "level": "debug",
        "days": 7,
        "format": _format,
    },
    "stderr": {
        "driver": "stderr",
        "level": "debug",
        # Containers log to stdout and a platform collects it, so this channel
        # defaults to the machine-readable form.
        "format": env("LOG_FORMAT", "json"),
    },
}

default = env("LOG_CHANNEL", "single")
