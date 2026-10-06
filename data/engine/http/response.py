"""
Response — Response/JsonResponse wrappers and the `redirect()` helper.
Category: Core Framework (HTTP).
Relations:
  - Returned by `engine/http/controller.py` helpers; converted to a
    Starlette response by `engine/http/kernel.py`.
References:
  - Guide: `documentation/controllers.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
from typing import Any, Dict, Optional
from starlette.responses import Response as StarletteResponse, JSONResponse as StarletteJSONResponse, HTMLResponse as StarletteHTMLResponse, RedirectResponse as StarletteRedirectResponse


class Response:
    def __init__(self, content: Any = "", status: int = 200, headers: Optional[Dict[str, str]] = None):
        self._content = content
        self._status = status
        self._headers = headers or {}

    @property
    def status(self) -> int:
        return self._status

    @property
    def status_code(self) -> int:
        return self._status

    def to_starlette(self) -> StarletteResponse:
        if isinstance(self._content, (dict, list)):
            return JsonResponse(self._content, self._status, self._headers).to_starlette()
        return StarletteHTMLResponse(str(self._content), status_code=self._status, headers=self._headers)


class JsonResponse(Response):
    def __init__(self, content: Any = None, status: int = 200, headers: Optional[Dict[str, str]] = None):
        if content is None:
            content = {}
        super().__init__(content, status, headers)

    def to_starlette(self) -> StarletteResponse:
        content = self._serialize(self._content)
        return StarletteJSONResponse(content, status_code=self._status, headers=self._headers)

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if hasattr(obj, "to_array"):
            return self._serialize(obj.to_array())
        if hasattr(obj, "to_dict"):
            return self._serialize(obj.to_dict())
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return obj


class RedirectResponse(StarletteRedirectResponse):
    """Starlette RedirectResponse augmented with session flash helpers."""

    def with_errors(self, errors: Any) -> RedirectResponse:
        """Flash validation errors to the active session."""
        from engine.http.session import get_current_session

        session = get_current_session()
        if session is not None:
            if hasattr(errors, "to_dict"):
                err_dict = errors.to_dict()
            elif hasattr(errors, "errors"):
                inner = errors.errors
                err_dict = inner.to_dict() if hasattr(inner, "to_dict") else inner
            elif isinstance(errors, dict):
                err_dict = errors
            else:
                err_dict = {"error": [str(errors)]}
            session.flash("_errors", err_dict)
            session.flash("errors", err_dict)
        return self

    def with_input(self, input_data: Optional[Dict[str, Any]] = None) -> RedirectResponse:
        """Flash old input data to the active session."""
        from engine.http.session import get_current_session

        session = get_current_session()
        if session is not None:
            session.flash("_old_input", input_data if input_data is not None else {})
        return self

    def with_flash(self, key: str, value: Any) -> RedirectResponse:
        """Flash an arbitrary key-value pair to the active session."""
        from engine.http.session import get_current_session

        session = get_current_session()
        if session is not None:
            session.flash(key, value)
        return self


class RedirectHelper:
    """Callable redirect factory providing named route and back helpers."""

    def __call__(
        self,
        url: str = "",
        route: Optional[str] = None,
        status: int = 302,
        **kwargs,
    ) -> RedirectResponse:
        if route:
            from engine.facades import Route

            target_url = Route.url_for(route, **kwargs)
        else:
            target_url = url
        return RedirectResponse(url=target_url or "/", status_code=status)

    def back(self, request: Any = None, fallback: str = "/", status: int = 302) -> RedirectResponse:
        """Redirect back to the previous page of this site, or to `fallback`.

        The `Referer` header is client-controlled. Following it blindly made
        every form an open redirect to any site, so only a relative path or an
        absolute URL on the request's own host is followed.
        """
        referer = ""
        if request is not None and hasattr(request, "headers"):
            referer = request.headers.get("referer", "") or ""
            host = request.headers.get("host", "") or ""
            referer = referer if _same_site(referer, host) else ""
        return RedirectResponse(url=referer or fallback, status_code=status)


def _same_site(url: str, host: str) -> bool:
    """Return whether `url` is a relative path or an http(s) URL on this site.

    This site is the request's own `Host` or the configured `APP_URL`: behind
    a reverse proxy the Host header is internal while the browser used the
    public address, which is also what the CSRF origin check trusts.
    """
    from urllib.parse import urlsplit

    if url.startswith("/") and not url.startswith("//") and "\\" not in url:
        return True
    parts = urlsplit(url)
    allowed = {name.lower() for name in (host, _app_url_host()) if name}
    return parts.scheme in ("http", "https") and parts.netloc.lower() in allowed


def _app_url_host() -> str:
    """Return the `host[:port]` of `app.APP_URL`, or an empty string."""
    from urllib.parse import urlsplit

    from engine.container.application import Container

    try:
        app_url = str(Container.getInstance().make("config").get("app.APP_URL", "") or "")
    except KeyError:
        return ""
    return urlsplit(app_url).netloc


redirect = RedirectHelper()

__all__ = ["Response", "JsonResponse", "RedirectResponse", "redirect"]
