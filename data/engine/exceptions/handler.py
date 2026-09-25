"""
ExceptionHandler - Turns raised exceptions into HTTP responses. Server faults
(5xx) log a stack trace; client errors (4xx) log at info level without one.
Category: Core Framework (Exceptions).
Relations:
  - Bound as `exception_handler`; invoked by `engine/http/kernel.py` around
    every request; escapes HTML on the debug exception page.
References:
  - Guide: `documentation/deployment.md#logging`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import traceback
from typing import Any, Callable, Dict, List, Optional


class CraftException(Exception):
    status_code = 500


class MisconfigurationError(CraftException):
    """The application is wired in a way that cannot work, and says how to fix it.

    Raised instead of degrading silently - a check that denies everyone, a
    parameter dropped on the floor - so the first request surfaces the mistake
    with the exact change to make.

    Attributes:
        code: Stable machine code for this failure, a key of
            `engine.support.diagnostics.CATALOG`.
        params: The values the message names.
        hint: The catalog message: what is wrong and the change that fixes it.
    """

    status_code = 500

    def __init__(self, code: str, **params: object) -> None:
        from engine.support.diagnostics import describe

        self.code = code
        self.params = params
        self.hint = describe(code, **params)
        super().__init__(": ".join((code, self.hint)))


class NotFoundHttpException(CraftException):
    status_code = 404


class AuthorizationException(CraftException):
    status_code = 403


class ValidationException(CraftException):
    status_code = 422

    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__("Validation failed")


class ExceptionHandler:
    """Converts exceptions into HTTP responses, honouring `app.debug`."""

    #: Exception types that should never be reported to the log.
    dont_report = (NotFoundHttpException,)

    def __init__(self, app: Any = None):
        self.app = app
        #: Sinks registered through `reporter()`, called for server faults.
        self._reporters: List[Callable[[BaseException, Dict[str, Any]], None]] = []

    def should_report(self, exception: BaseException) -> bool:
        """Only server faults are worth a stack trace.

        A 404, a failed CSRF check or a validation error is the client getting
        it wrong - logging a full traceback for each one buries the real faults.
        """
        if isinstance(exception, self.dont_report):
            return False
        return self.status_for(exception) >= 500

    # -- configuration ---------------------------------------------------------

    def _debug(self) -> bool:
        if self.app is None:
            return False
        try:
            # `APP_DEBUG`, not `app.debug`: the config repository keys entries
            # by the module attribute name (and its lowercase form), so
            # `app.debug` never resolves and debug mode silently stayed off.
            return bool(self.app.make("config").get("app.APP_DEBUG", False))
        except Exception:
            return False

    def _logger(self) -> Optional[Any]:
        if self.app is None:
            return None
        try:
            return self.app.make("log")
        except Exception:
            return None

    # -- handling --------------------------------------------------------------

    def reporter(self, callback: Callable[[BaseException, Dict[str, Any]], None]) -> Any:
        """Register a sink for reportable exceptions - Sentry, or any other.

        The log is where an exception is written down; a reporter is where it
        is noticed. Registered rather than hard-wired so the framework carries
        no vendor, and called with the request context so the report names the
        request rather than arriving as an anonymous stack trace.

            handler.reporter(lambda exc, ctx: sentry_sdk.capture_exception(exc))
        """
        self._reporters.append(callback)
        return self

    def report(self, exception: BaseException) -> None:
        from engine.support import context

        request_context = context.current()
        logger = self._logger()

        if logger is not None:
            if self.should_report(exception):
                logger.error(
                    "%s: %s", type(exception).__name__, exception, exc_info=exception
                )
            else:
                logger.info(
                    "%s (%s): %s",
                    type(exception).__name__,
                    self.status_for(exception),
                    exception,
                )

        if not self.should_report(exception):
            return

        # Counted here rather than in the middleware: this is the one funnel
        # every reportable fault passes through, however it was rendered.
        try:
            from engine.support.metrics import registry

            registry.increment(
                "craft_exceptions_total", exception=type(exception).__name__
            )
        except Exception:
            pass

        for reporter in self._reporters:
            try:
                reporter(exception, dict(request_context))
            except Exception:
                # A failing reporter must not replace the exception being
                # reported: the original is the one worth surfacing, and an
                # error tracker being down is not a reason to lose it.
                if logger is not None:
                    logger.warning("error_reporter_failed", exc_info=True)

    def status_for(self, exception: BaseException) -> int:
        return int(getattr(exception, "status_code", 500))

    def to_payload(self, exception: BaseException) -> dict:
        status = self.status_for(exception)
        debug = self._debug()
        # A 5xx message is the exception's own text - a database error, a path,
        # an internal class name. Only debug mode shows it; a visitor gets the
        # generic page title, and the log keeps the detail.
        message = str(exception) or type(exception).__name__
        if status >= 500 and not debug:
            message = self.TITLES.get(500, "Server error")
        payload: dict = {"message": message, "status": status}
        code = getattr(exception, "code", None)
        if isinstance(code, str):
            payload["code"] = code
        if isinstance(exception, ValidationException):
            payload["errors"] = exception.errors
        # A trace belongs to a *failure*. A 403 or a 404 is the framework
        # working: the visitor asked for something they may not have, and
        # answering that with a stack dump is noise at best and a map of the
        # internals at worst. Traces are for 5xx, and only with debug on.
        if debug and status >= 500:
            payload["exception"] = type(exception).__name__
            payload["trace"] = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        return payload

    def render(self, exception: BaseException, wants_json: bool = True) -> Any:
        """Build a Starlette response for the given exception."""
        self.report(exception)
        status = self.status_for(exception)
        payload = self.to_payload(exception)

        if wants_json:
            from starlette.responses import JSONResponse

            return JSONResponse(payload, status_code=status)

        from starlette.responses import HTMLResponse

        # An application view wins, so an error page can be branded like the
        # rest of the site: `resources/views/errors/403.forge.py`, falling back
        # to `errors/error.forge.py`. Neither is required - the built-in page
        # below is a complete answer on its own.
        rendered = self._render_error_view(status, payload)
        if rendered is not None:
            return HTMLResponse(rendered, status_code=status)

        return HTMLResponse(
            self._default_error_page(status, payload), status_code=status
        )

    #: What each status actually means to the person reading it. A 403 is not a
    #: crash and should not read like one.
    TITLES = {
        400: "Bad request",
        401: "You need to sign in",
        403: "You do not have access to this page",
        404: "Page not found",
        419: "Your session expired",
        422: "Some of that did not check out",
        429: "Too many requests",
        500: "Something went wrong on our side",
    }

    HINTS = {
        401: "Sign in and try again.",
        403: "Your account is signed in, but it is not allowed to open this "
             "page. If you think it should be, ask an administrator to grant "
             "your account the access it needs.",
        404: "The address may be mistyped, or the page may have moved.",
        419: "Refresh the page and submit the form again.",
        429: "Wait a moment before trying again.",
    }

    def _render_error_view(self, status: int, payload: dict):
        """Try the application's own error template, if it has one."""
        if self.app is None:
            return None
        for template in (f"errors.{status}", "errors.error"):
            try:
                view = self.app.make("view")
                return view.render(template, {
                    "status": status,
                    "message": payload.get("message", ""),
                    "title": self.TITLES.get(status, "Error"),
                    "hint": self.HINTS.get(status, ""),
                    "trace": payload.get("trace"),
                    "show_sidebar": False,
                })
            except Exception:
                # No such template (or it failed): fall through to the next
                # candidate and finally to the built-in page. An error page
                # that itself errors must never replace the original problem.
                continue
        return None

    def _default_error_page(self, status: int, payload: dict) -> str:
        """A self-contained, readable error page - no template needed."""
        from html import escape

        title = self.TITLES.get(status, "Error")
        hint = self.HINTS.get(status, "")
        message = escape(str(payload.get("message", "")))

        detail = ""
        trace = payload.get("trace")
        if trace:
            detail = (
                '<pre style="text-align:left;overflow:auto;background:#0f172a;'
                'color:#e2e8f0;padding:1rem;border-radius:.75rem;font-size:12px;'
                'line-height:1.5">' + escape("".join(trace)) + "</pre>"
            )

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{status} - {escape(title)}</title></head>
<body style="margin:0;min-height:100vh;display:flex;align-items:center;
justify-content:center;background:#f8fafc;color:#0f172a;
font-family:system-ui,-apple-system,'Segoe UI',sans-serif">
  <main style="max-width:34rem;padding:2rem;text-align:center">
    <p style="font-family:ui-monospace,monospace;font-size:.75rem;
       letter-spacing:.1em;text-transform:uppercase;color:#f97316;
       font-weight:700;margin:0 0 .5rem">Error {status}</p>
    <h1 style="font-size:1.75rem;font-weight:800;margin:0 0 .75rem">{escape(title)}</h1>
    <p style="color:#475569;line-height:1.6;margin:0 0 1.5rem">{escape(hint) or message}</p>
    <a href="/" style="display:inline-block;background:#ea580c;color:#fff;
       font-weight:700;padding:.7rem 1.5rem;border-radius:.75rem;
       text-decoration:none">Back to safety</a>
    {detail}
  </main>
</body></html>"""


__all__ = [
    "CraftException",
    "MisconfigurationError",
    "NotFoundHttpException",
    "AuthorizationException",
    "ValidationException",
    "ExceptionHandler",
]
