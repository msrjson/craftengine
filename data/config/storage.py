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
    # Every key is prefixed with the bound tenant, so tenants share no
    # namespace on disk and one tenant can never name another's file. A call
    # with no tenant bound is refused. See documentation/storage.md.
    "tenant": {
        "driver": "local",
        "root": "storage/app",
        "url": "/storage",
        "tenant_scoped": True,
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
