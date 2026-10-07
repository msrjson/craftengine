"""Cache manager for Craft Framework.

Supports `array` (in-process), `file` and `redis` stores behind a single
expressive API. TTLs are honoured by every store.

Category: Core Framework (Cache).
Relations:
  - Bound as `cache`, exposed via the `Cache` facade. Configured by
    `config/cache.py`; degrades to the array store if Redis is configured
    but unreachable.
References:
  - Guide: `documentation/cache.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, Optional


#: Stored in place of None so `remember` can tell "cached None" from "missing".
_CACHED_NONE = "__craft_cache_none__"


class Store:
    def get(self, key: str) -> Any:
        raise NotImplementedError

    def expires_in(self, key: str) -> Optional[float]:
        """Remaining TTL in seconds, or None when unknown/non-expiring."""
        return None

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError

    def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store only if the key is absent. True when this caller won.

        Atomic put-if-absent, which `has()` followed by `put()` is not: two
        callers racing the same key both see it missing and both proceed, so
        every guarantee built on that pair — the scheduler's overlap lock, most
        of all — silently does not hold. Each store implements it with whatever
        primitive it actually has.
        """
        raise NotImplementedError

    def forget(self, key: str) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        raise NotImplementedError

    def flush_prefix(self, prefix: str) -> None:
        """Drop every key starting with `prefix`.

        A tag-style invalidation: cache a page under `page:1`, `page:2` … and
        flush the `page:` prefix after one edit instead of the whole store.
        """
        raise NotImplementedError


class ArrayStore(Store):
    """In-memory store — the default, and the store used during tests."""

    def __init__(self, max_entries: Optional[int] = None) -> None:
        self._items: Dict[str, tuple] = {}
        self._lock = threading.Lock()
        #: 0 (or None) means unbounded; over the bound the oldest entry is dropped.
        self.max_entries = int(max_entries or 0)

    def _evict(self) -> None:
        """Keep the store within its bound: expired entries first, then the oldest.

        Called with the lock held. A long-lived worker that caches per key
        without a TTL would otherwise grow this dict for the life of the
        process. The oldest entry going is a cache miss, never an error.
        """
        if not self.max_entries or len(self._items) <= self.max_entries:
            return
        now = time.time()
        expired = [
            name
            for name, (_, expires_at) in self._items.items()
            if expires_at is not None and expires_at < now
        ]
        for name in expired:
            del self._items[name]
        while len(self._items) > self.max_entries:
            del self._items[next(iter(self._items))]

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and expires_at < time.time():
                del self._items[key]
                return None
            return value

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._items[key] = (value, time.time() + ttl if ttl else None)
            self._evict()

    def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        with self._lock:
            entry = self._items.get(key)
            if entry is not None:
                expires_at = entry[1]
                if expires_at is None or expires_at >= time.time():
                    return False
            self._items[key] = (value, time.time() + ttl if ttl else None)
            self._evict()
            return True

    def expires_in(self, key: str) -> Optional[float]:
        with self._lock:
            entry = self._items.get(key)
        if entry is None or entry[1] is None:
            return None
        remaining = entry[1] - time.time()
        return remaining if remaining > 0 else None

    def forget(self, key: str) -> None:
        with self._lock:
            self._items.pop(key, None)

    def flush(self) -> None:
        with self._lock:
            self._items.clear()

    def flush_prefix(self, prefix: str) -> None:
        with self._lock:
            for name in [key for key in self._items if key.startswith(prefix)]:
                del self._items[name]


class FileStore(Store):
    """Filesystem store writing JSON payloads under `storage/framework/cache`."""

    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def _path(self, key: str) -> str:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return os.path.join(self.directory, f"{digest}.cache")

    def get(self, key: str) -> Any:
        path = self._path(key)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None
        if payload.get("expires_at") and payload["expires_at"] < time.time():
            self.forget(key)
            return None
        return payload.get("value")

    def expires_in(self, key: str) -> Optional[float]:
        path = self._path(key)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None
        if not payload.get("expires_at"):
            return None
        remaining = payload["expires_at"] - time.time()
        return remaining if remaining > 0 else None

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        payload = {"key": key, "value": value, "expires_at": time.time() + ttl if ttl else None}
        try:
            with open(self._path(key), "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except (TypeError, OSError):
            pass

    def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Exclusive create — the filesystem does the arbitration.

        `O_CREAT | O_EXCL` fails if the file exists, atomically, across
        processes on the same host. An expired entry is removed first so a
        stale lock file does not block the key forever.
        """
        path = self._path(key)
        if self.get(key) is None:
            # Either absent or expired; only the expired case needs clearing.
            try:
                os.remove(path)
            except OSError:
                pass

        payload = {"key": key, "value": value, "expires_at": time.time() + ttl if ttl else None}
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        except OSError:
            return False

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except (TypeError, OSError):
            self.forget(key)
            return False
        return True

    def forget(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except OSError:
            pass

    def flush(self) -> None:
        if not os.path.isdir(self.directory):
            return
        for name in os.listdir(self.directory):
            if name.endswith(".cache"):
                try:
                    os.remove(os.path.join(self.directory, name))
                except OSError:
                    pass

    def flush_prefix(self, prefix: str) -> None:
        # The filename is a hash, so the original key is read back from the
        # payload. Entries written before this field existed simply do not match
        # and are left alone.
        if not os.path.isdir(self.directory):
            return
        for name in os.listdir(self.directory):
            if not name.endswith(".cache"):
                continue
            path = os.path.join(self.directory, name)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
            except (json.JSONDecodeError, OSError):
                continue
            if str(payload.get("key", "")).startswith(prefix):
                try:
                    os.remove(path)
                except OSError:
                    pass


class RedisStore(Store):
    """Redis-backed store. Requires the `redis` package."""

    def __init__(self, host: str = "127.0.0.1", port: int = 6379, password: Optional[str] = None, db: int = 0):
        import redis  # imported lazily so redis stays optional

        self.client = redis.Redis(host=host, port=port, password=password or None, db=db)

    def get(self, key: str) -> Any:
        raw = self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def expires_in(self, key: str) -> Optional[float]:
        ttl = self.client.ttl(key)
        return float(ttl) if ttl and ttl > 0 else None

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        payload = json.dumps(value, default=str)
        if ttl:
            self.client.setex(key, int(ttl), payload)
        else:
            self.client.set(key, payload)

    def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """`SET key value NX EX ttl` — one round trip, atomic across hosts."""
        return bool(
            self.client.set(key, json.dumps(value, default=str), nx=True, ex=ttl or None)
        )

    def forget(self, key: str) -> None:
        self.client.delete(key)

    def flush(self) -> None:
        self.client.flushdb()

    def flush_prefix(self, prefix: str) -> None:
        for key in self.client.scan_iter(match=prefix + "*"):
            self.client.delete(key)


class CacheManager:
    """Resolves the configured store and exposes the cache API."""

    def __init__(self, app: Any = None):
        self.app = app
        self._store: Optional[Store] = None

    @property
    def store(self) -> Store:
        if self._store is None:
            self._store = self._resolve_store()
        return self._store

    def _resolve_store(self) -> Store:
        config = None
        if self.app is not None:
            try:
                config = self.app.make("config")
            except Exception:
                config = None

        driver = (config.get("cache.default", "array") if config else "array") or "array"
        driver = str(driver).lower()

        max_entries = 0
        if config:
            try:
                max_entries = int(config.get("cache.stores.memory.max_entries", 0) or 0)
            except (TypeError, ValueError):
                max_entries = 0

        if driver == "file":
            base_path = getattr(self.app, "base_path", os.getcwd())
            directory = (
                config.get("cache.stores.file.path") if config else None
            ) or os.path.join(base_path, "storage", "framework", "cache")
            return FileStore(directory)

        if driver == "redis":
            try:
                return RedisStore(
                    host=(config.get("cache.stores.redis.host", "127.0.0.1") if config else "127.0.0.1"),
                    port=int(config.get("cache.stores.redis.port", 6379) if config else 6379),
                    password=(config.get("cache.stores.redis.password") if config else None),
                )
            except Exception:
                # Degrade rather than break the app — but say so. A silent
                # fallback makes every cache-backed guarantee per-process:
                # rate limiting stops being shared across workers, and the
                # only symptom is a brute-force limit that quietly multiplies
                # by the worker count.
                logging.getLogger("craft").warning(
                    "Cache driver 'redis' is unavailable; falling back to an "
                    "in-memory store. Anything relying on a shared cache "
                    "(rate limiting, scheduler overlap locks) is now "
                    "per-process.",
                    exc_info=True,
                )
                return ArrayStore(max_entries)

        if driver not in ("memory", "array"):
            # An unrecognised driver used to become in-memory with no signal,
            # so a typo in CACHE_DRIVER looked exactly like a working cache.
            logging.getLogger("craft").warning(
                "Unknown cache driver %r; using the in-memory store. "
                "Known drivers: memory, file, redis.", driver,
            )

        return ArrayStore(max_entries)

    # -- public API ------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        value = self.store.get(key)
        return default if value is None else value

    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.store.put(key, value, ttl)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.put(key, value, ttl)

    def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store only if absent. True when this caller won the race.

        Reach for this instead of `has()` then `put()` whenever the answer
        decides who does the work — a lock, a once-only side effect, a
        deduplicated dispatch. The pair is not atomic; this is.
        """
        return self.store.add(key, value, ttl)

    def has(self, key: str) -> bool:
        return self.store.get(key) is not None

    def forget(self, key: str) -> None:
        self.store.forget(key)

    def forever(self, key: str, value: Any) -> None:
        self.store.put(key, value, None)

    def flush(self) -> None:
        self.store.flush()

    def flush_prefix(self, prefix: str) -> None:
        """Drop every key under `prefix` - a tag-style invalidation.

        Cache each page as `page:<id>` and flush `page:` after one edit, rather
        than flushing the whole store and losing unrelated entries.
        """
        self.store.flush_prefix(prefix)

    def remember(self, key: str, ttl: Optional[int], callback: Callable[[], Any]) -> Any:
        cached = self.store.get(key)
        if cached is not None:
            return None if cached == _CACHED_NONE else cached
        value = callback()
        self.store.put(key, _CACHED_NONE if value is None else value, ttl)
        return value

    def remember_forever(self, key: str, callback: Callable[[], Any]) -> Any:
        return self.remember(key, None, callback)

    def pull(self, key: str, default: Any = None) -> Any:
        value = self.get(key, default)
        self.forget(key)
        return value

    def increment(self, key: str, amount: int = 1) -> int:
        value = int(self.get(key, 0) or 0) + amount
        # Keep whatever TTL the entry already had instead of promoting it to
        # forever.
        self.store.put(key, value, self.store.expires_in(key))
        return value

    def decrement(self, key: str, amount: int = 1) -> int:
        return self.increment(key, -amount)


__all__ = ["CacheManager", "ArrayStore", "FileStore", "RedisStore", "Store"]
