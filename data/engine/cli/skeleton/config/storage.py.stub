"""Filesystem & Cloud Storage Configuration for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

default = os.getenv("FILESYSTEM_DISK", "local")

disks = {
    "local": {
        "driver": "local",
        "root": "storage/app",
        "url": "/storage",
    },
    "public": {
        "driver": "local",
        "root": "storage/app/public",
        "url": "/storage",
        "visibility": "public",
    },
    "s3": {
        "driver": "s3",
        "key": os.getenv("AWS_ACCESS_KEY_ID", ""),
        "secret": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        "region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "bucket": os.getenv("AWS_BUCKET", ""),
        "url": os.getenv("AWS_URL", ""),
        "endpoint": os.getenv("AWS_ENDPOINT", ""),  # For MinIO / Cloudflare R2 / GCS
    },
}
