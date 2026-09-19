"""Support package exports."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.http.response import JsonResponse, Response, redirect
from engine.support import clock, icu
from engine.support.collection import Collection
from engine.support.translation import __, locale_chain, normalize_locale, translate


def view(template_name: str, data: dict = None) -> Response:
    """Render a template.

    Errors propagate to the exception handler, matching `Controller.view`.
    This helper used to catch everything and return `"View x rendered"` with
    HTTP 200 — so a missing template, a syntax error, or an undefined variable
    all produced a page that looked like a successful render. The same placebo
    was already removed from the controller and the view engine; this copy was
    missed, and `DocsController` still routes through it.
    """
    from engine.container.application import Container

    forge = Container.getInstance().make("view")
    return Response(forge.render(template_name, data or {}))
