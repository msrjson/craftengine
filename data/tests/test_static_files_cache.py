"""Unit tests for CachedStaticFiles and RFC-compliant caching headers."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import tempfile
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from engine.http.static_files import (
    IMMUTABLE_CACHE_CONTROL,
    REVALIDATED_CACHE_CONTROL,
    CachedStaticFiles,
    cache_control_for,
)


def test_cache_control_for_fingerprinted_url():
    """Fingerprinted asset URLs with ?v=... receive immutable 1-year cache headers."""
    assert cache_control_for(b"v=a1b2c3d4e5") == IMMUTABLE_CACHE_CONTROL
    assert cache_control_for(b"foo=bar&v=123") == IMMUTABLE_CACHE_CONTROL


def test_cache_control_for_bare_url():
    """Bare asset URLs receive revalidated 5-minute cache headers."""
    assert cache_control_for(b"") == REVALIDATED_CACHE_CONTROL
    assert cache_control_for(b"other=value") == REVALIDATED_CACHE_CONTROL
    assert cache_control_for(b"v=") == REVALIDATED_CACHE_CONTROL


def test_cached_static_files_response_headers():
    """CachedStaticFiles stamps Cache-Control on responses for served assets."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "app.js"
        test_file.write_text("console.log('hello');")

        app = Starlette(routes=[Mount("/static", app=CachedStaticFiles(directory=temp_dir), name="static")])
        client = TestClient(app)

        # 1. Bare URL test
        bare_resp = client.get("/static/app.js")
        assert bare_resp.status_code == 200
        assert bare_resp.headers["Cache-Control"] == REVALIDATED_CACHE_CONTROL

        # 2. Fingerprinted URL test
        cached_resp = client.get("/static/app.js?v=9f8e7d6c5b")
        assert cached_resp.status_code == 200
        assert cached_resp.headers["Cache-Control"] == IMMUTABLE_CACHE_CONTROL
