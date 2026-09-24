"""The native `/.well-known/msr.json` endpoint (MSR JSON protocol).

Registries and AI agents fetch the manifest cross-origin, so every response
carries `Access-Control-Allow-Origin: *`, as the protocol requires. The route
is mounted outside the middleware stack like the health probes: it needs no
session, no CSRF check and no user lookup.

A hand-written `public/.well-known/msr.json` wins over the generated manifest
and is served verbatim. An incomplete configuration answers 404 instead of a
manifest with guessed values.

Category: Core Framework (HTTP).
Relations:
  - Registered on `engine/http/router.py` as an engine route and dispatched
    by `engine/http/kernel.py` after the application's own routes.
  - Builds the manifest with `engine/support/msr.py`.
References:
  - Guide: `documentation/msr.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from engine.support.msr import MANIFEST_PATH, ManifestBuilder, ManifestIncompleteError

logger = logging.getLogger(__name__)

#: Headers every manifest response carries. Five minutes of caching keeps a
#: crawler burst off the translation store without hiding a release for long.
RESPONSE_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "public, max-age=300",
}


#: Dotted module recorded as the attribution of the route below.
PROVIDER = "engine.http.msr"


def register_msr_route(app: Any, router: Any) -> None:
    """Register the manifest route, if the application asked for it.

    Off unless `msr.ENABLED` says otherwise. The manifest publishes the exact
    version, release date, vendor and pricing of the installation, which is
    the single most useful input for matching a published vulnerability to a
    running instance. Publishing it is a business decision the owner makes,
    not a default an application inherits. An application route on the same
    path always wins.

    Args:
        app: The application container.
        router: The router the route is recorded on.
    """
    config = app.make("config")
    if not config.get("msr.ENABLED", False) or MANIFEST_PATH in router.claimed_uris():
        return

    async def endpoint(request: Any) -> Any:
        return await _respond(app)

    router.add_engine_route(["GET", "HEAD"], MANIFEST_PATH, endpoint, name="msr.manifest", provider=PROVIDER)


def build_manifest(app: Any) -> dict[str, Any]:
    """Build the application's manifest from its configuration and translations.

    Args:
        app: The application container.

    Returns:
        The manifest mapping.

    Raises:
        ManifestIncompleteError: If a required field cannot be resolved.
    """
    from engine.support.translation import translate

    settings = {**(app.make("config").get("msr") or {})}
    return ManifestBuilder(settings, Path(app.base_path), lambda key, locale: translate(key, locale=locale)).build()


async def _respond(app: Any) -> Any:
    from starlette.concurrency import run_in_threadpool
    from starlette.responses import FileResponse, JSONResponse, Response

    static = Path(app.base_path) / "public" / MANIFEST_PATH.lstrip("/")
    if static.is_file():
        return FileResponse(static, media_type="application/json", headers=RESPONSE_HEADERS)
    try:
        manifest = await run_in_threadpool(_build_and_release, app)
    except ManifestIncompleteError as exc:
        logger.warning("msr_manifest_incomplete", extra={"field": exc.field})
        return Response(status_code=404)
    return JSONResponse(manifest, headers=RESPONSE_HEADERS)


def _build_and_release(app: Any) -> dict[str, Any]:
    # Descriptions come from the translation store, a blocking query: release
    # the pooled connection at this request boundary, as the kernel does.
    try:
        return build_manifest(app)
    finally:
        app.make("db").release()


def render_manifest(manifest: dict[str, Any]) -> str:
    """Serialize a manifest the way it is published.

    Args:
        manifest: The manifest mapping.

    Returns:
        Indented UTF-8 JSON text.
    """
    return json.dumps(manifest, indent=2, ensure_ascii=False)


__all__ = ["PROVIDER", "RESPONSE_HEADERS", "build_manifest", "register_msr_route", "render_manifest"]
