"""API routes - JSON API endpoints."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route
from craft.http.response import JsonResponse


def status_handler(request):
    return JsonResponse({"status": "ok", "service": "Craft Engine API", "version": "v1"})


Route.group(
    lambda: (Route.get("/status", status_handler).name("status"),),
    prefix="/api/v1",
    name="api.",
)
