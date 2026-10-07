"""The in-memory cache is bounded, and any store can be flushed by key prefix."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.cache.manager import ArrayStore, CacheManager, FileStore


class _Config:
    def __init__(self, max_entries):
        self._max = max_entries

    def get(self, key, default=None):
        if key == "cache.default":
            return "memory"
        if key == "cache.stores.memory.max_entries":
            return self._max
        return default


class _App:
    base_path = "/tmp"

    def __init__(self, max_entries):
        self._config = _Config(max_entries)

    def make(self, key):
        return self._config


def test_the_array_store_evicts_the_oldest_over_its_bound():
    store = ArrayStore(max_entries=3)
    for index in range(5):
        store.put(f"k{index}", index)

    assert store.get("k0") is None
    assert store.get("k4") == 4


def test_the_array_store_drops_expired_entries_before_the_oldest():
    store = ArrayStore(max_entries=2)
    store.put("gone", 1, ttl=-1)
    store.put("a", 1)
    store.put("b", 2)

    assert store.get("a") == 1
    assert store.get("b") == 2


def test_an_unbounded_store_keeps_everything():
    store = ArrayStore()
    for index in range(10):
        store.put(f"k{index}", index)

    assert store.get("k0") == 0


def test_flush_prefix_drops_only_the_prefix():
    store = ArrayStore()
    store.put("page:1", 1)
    store.put("page:2", 2)
    store.put("other", 3)

    store.flush_prefix("page:")

    assert store.get("page:1") is None
    assert store.get("other") == 3


def test_the_file_store_flushes_by_prefix(tmp_path):
    store = FileStore(str(tmp_path))
    store.put("page:1", 1)
    store.put("other", 3)

    store.flush_prefix("page:")

    assert store.get("page:1") is None
    assert store.get("other") == 3


def test_the_manager_uses_the_configured_bound():
    manager = CacheManager(_App(2))

    assert manager.store.max_entries == 2

    manager.put("a", 1)
    manager.put("b", 2)
    manager.put("c", 3)

    assert manager.get("a") is None
    assert manager.get("c") == 3
