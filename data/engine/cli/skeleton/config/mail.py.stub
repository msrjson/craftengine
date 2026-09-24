"""Mail & Notification Configuration for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

default = os.getenv("MAIL_MAILER", "log")

from_address = {
    "address": os.getenv("MAIL_FROM_ADDRESS", "noreply@craftengine.dev"),
    "name": os.getenv("MAIL_FROM_NAME", "Craft Engine"),
}

mailers = {
    "smtp": {
        "transport": "smtp",
        "host": os.getenv("MAIL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MAIL_PORT", 587)),
        "encryption": os.getenv("MAIL_ENCRYPTION", "tls"),  # 'tls', 'ssl', or None
        "username": os.getenv("MAIL_USERNAME", ""),
        "password": os.getenv("MAIL_PASSWORD", ""),
        "timeout": 30,
    },
    "log": {
        "transport": "log",
        "channel": "craft",
    },
    "array": {
        "transport": "array",  # In-memory testing
    },
}
