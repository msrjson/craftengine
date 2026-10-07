"""Amazon S3 and Cloud Storage Driver for Craft Framework.

Supports AWS S3, Cloudflare R2, MinIO, and Google Cloud Storage (S3-compatible).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import mimetypes
from typing import Any, BinaryIO, Dict, Optional, Union

from engine.storage.paths import normalize_key


class S3StorageDriver:
    """Cloud storage driver for S3-compatible object storage."""

    def __init__(self, config: Dict[str, Any]):
        self.key = config.get("key", "")
        self.secret = config.get("secret", "")
        self.region = config.get("region", "us-east-1")
        self.bucket = config.get("bucket", "")
        self.custom_url = config.get("url", "")
        self.endpoint = config.get("endpoint", "")
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import boto3
            client_kwargs = {
                "service_name": "s3",
                "region_name": self.region,
                "aws_access_key_id": self.key,
                "aws_secret_access_key": self.secret,
            }
            if self.endpoint:
                client_kwargs["endpoint_url"] = self.endpoint
            self._client = boto3.client(**client_kwargs)
            return self._client
        except ImportError as exc:
            raise ImportError(
                "The `boto3` package is required to use the S3 storage driver. "
                "Install it with `pip install boto3`."
            ) from exc

    def put(self, path: str, contents: Union[str, bytes, BinaryIO], **kwargs: Any) -> bool:
        client = self._get_client()
        clean_path = normalize_key(path)

        if hasattr(contents, "read") and callable(contents.read):
            body = contents.read()
            if isinstance(body, str):
                body = body.encode("utf-8")
        elif isinstance(contents, str):
            body = contents.encode("utf-8")
        else:
            body = bytes(contents)

        mime, _ = mimetypes.guess_type(clean_path)
        content_type = kwargs.get("content_type") or mime or "application/octet-stream"

        client.put_object(
            Bucket=self.bucket,
            Key=clean_path,
            Body=body,
            ContentType=content_type,
            **{k: v for k, v in kwargs.items() if k != "content_type"},
        )
        return True

    def get(self, path: str) -> Optional[bytes]:
        client = self._get_client()
        clean_path = normalize_key(path)
        try:
            resp = client.get_object(Bucket=self.bucket, Key=clean_path)
            return resp["Body"].read()
        except Exception:
            return None

    def exists(self, path: str) -> bool:
        client = self._get_client()
        clean_path = normalize_key(path)
        try:
            client.head_object(Bucket=self.bucket, Key=clean_path)
            return True
        except Exception:
            return False

    def delete(self, path: str) -> bool:
        client = self._get_client()
        clean_path = normalize_key(path)
        try:
            client.delete_object(Bucket=self.bucket, Key=clean_path)
            return True
        except Exception:
            return False

    def size(self, path: str) -> int:
        client = self._get_client()
        clean_path = normalize_key(path)
        try:
            resp = client.head_object(Bucket=self.bucket, Key=clean_path)
            return int(resp.get("ContentLength", 0))
        except Exception:
            return 0

    def mime_type(self, path: str) -> str:
        mime, _ = mimetypes.guess_type(path)
        return mime or "application/octet-stream"

    def url(self, path: str) -> str:
        clean_path = normalize_key(path)
        if self.custom_url:
            return f"{self.custom_url.rstrip('/')}/{clean_path}"
        if self.endpoint:
            return f"{self.endpoint.rstrip('/')}/{self.bucket}/{clean_path}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{clean_path}"

    def temporary_url(self, path: str, minutes: int = 5) -> str:
        client = self._get_client()
        clean_path = normalize_key(path)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": clean_path},
            ExpiresIn=minutes * 60,
        )
