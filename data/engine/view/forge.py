"""Forge View Engine for Craft Framework.

Jinja2 with Forge directives. Templates are preprocessed before Jinja
compiles them, so `@csrf`, `@auth` and friends work in `.forge.py` files.

Category: Core Framework (View).
Relations:
  - Bound as `view`, exposed via the `View` facade; rendered by
    `Controller.view()` (`engine/http/controller.py`). Errors propagate as
    `TemplateNotFound`, `TemplateSyntaxError` (an unknown directive) and, with
    `APP_DEBUG` on, `UndefinedError` (a missing variable).
References:
  - Guide: `documentation/views.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from jinja2 import (
    BaseLoader,
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    TemplateSyntaxError,
    Undefined,
)
from markupsafe import Markup

def resolve_view_path(name: str) -> str:
    """Turn a dotted view name into a template path.

    `layouts.app` -> `layouts/app.forge.py`. Without this, `@extends` handed the
    dotted name straight to Jinja, which looked for a file literally called
    "layouts.app" — so every view that extended a layout failed to render.
    """
    if name.endswith((".forge.py", ".html")):
        return name
    return name.replace(".", "/") + ".forge.py"


#: Forge directive -> Jinja equivalent. Order matters: longer directives first,
#: so `@endauth` is not partially matched by `@end`.
DIRECTIVES = [
    (r"@csrf\b", "{{ csrf_field() }}"),
    (r"@honeypot\b", "{{ honeypot_field() }}"),
    (r"@antispam\b", "{{ antispam_fields() }}"),
    (r"@method\(\s*['\"](\w+)['\"]\s*\)", r'<input type="hidden" name="_method" value="\1">'),
    (r"@auth\b", "{% if auth() %}"),
    (r"@endauth\b", "{% endif %}"),
    (r"@guest\b", "{% if not auth() %}"),
    (r"@endguest\b", "{% endif %}"),
    (r"@endcan\b", "{% endif %}"),
    (r"@enderror\b", "{% endif %}"),
    (r"@else\b", "{% else %}"),
    (r"@endif\b", "{% endif %}"),
    (r"@endforeach\b", "{% endfor %}"),
    (r"@endsection\b", "{% endblock %}"),
]

_COMPILED = [(re.compile(pattern), replacement) for pattern, replacement in DIRECTIVES]

# Directives carrying a view name need the path resolved, so they are handled
# with a callback rather than a plain substitution.
_EXTENDS_RE = re.compile(r"@extends\(\s*['\"](.+?)['\"]\s*\)")
_INCLUDE_RE = re.compile(r"@include\(\s*['\"](.+?)['\"]\s*\)")

# -- balanced-paren directives ---------------------------------------------------
#
# Directives taking an arbitrary expression cannot be matched with `\((.+?)\)`:
# a non-greedy regex stops at the first ")", so `@if(user.has_role('admin'))`
# used to leave a stray ")" in the output. A tiny scanner finds the matching
# close paren instead, skipping over quoted strings.

def _matching_paren(source: str, start: int) -> int:
    """Index of the ")" matching the "(" at `start`, or -1 if unbalanced."""
    depth = 0
    quote = None
    i = start
    while i < len(source):
        ch = source[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _replace_paren_directive(source: str, name: str, render) -> str:
    """Replace every `@name( ... )` using balanced-paren argument extraction.

    `render` receives the stripped argument string; returning None leaves the
    original text untouched.
    """
    pattern = re.compile(r"@" + name + r"\s*\(")
    out = []
    pos = 0
    while True:
        match = pattern.search(source, pos)
        if match is None:
            out.append(source[pos:])
            return "".join(out)
        open_idx = match.end() - 1
        close_idx = _matching_paren(source, open_idx)
        if close_idx == -1:
            out.append(source[pos:match.end()])
            pos = match.end()
            continue
        replacement = render(source[open_idx + 1:close_idx].strip())
        if replacement is None:
            out.append(source[pos:close_idx + 1])
        else:
            out.append(source[pos:match.start()])
            out.append(replacement)
        pos = close_idx + 1


#: `@section("name")` opens a block; `@section("name", value)` is inline.
_NAME_ARGS_RE = re.compile(r"^['\"]([\w.-]+)['\"]\s*(?:,\s*(.+))?$", re.DOTALL)


def _render_section(args: str) -> Optional[str]:
    match = _NAME_ARGS_RE.match(args)
    if match is None:
        return None
    name, value = match.group(1), match.group(2)
    if value is None:
        return "{% block " + name + " %}"
    value = value.strip()
    # A quoted literal is emitted as bare text; anything else is treated as an
    # expression, so `@section("title", post.title)` still works.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        body = value[1:-1]
    else:
        body = "{{ " + value + " }}"
    return "{% block " + name + " %}" + body + "{% endblock %}"


def _render_yield(args: str) -> Optional[str]:
    match = _NAME_ARGS_RE.match(args)
    if match is None:
        return None
    name, value = match.group(1), match.group(2)
    if value is None:
        return "{% block " + name + " %}{% endblock %}"

    # Same literal handling as `@section`: emitted raw, the quotes around a
    # default landed in the HTML — `@yield("title", "Craft")` rendered
    # `"Craft"`, quotes included.
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        body = value[1:-1]
    else:
        body = "{{ " + value + " }}"
    return "{% block " + name + " %}" + body + "{% endblock %}"


def _render_foreach(args: str) -> Optional[str]:
    """Compile `@foreach(items as item)`, or the Jinja order `@foreach(item in items)`."""
    match = re.match(r"(.+?)\s+as\s+(.+)$", args, re.DOTALL)
    if match is not None:
        return "{% for " + match.group(2).strip() + " in " + match.group(1).strip() + " %}"
    match = re.match(r"(.+?)\s+in\s+(.+)$", args, re.DOTALL)
    if match is not None:
        return "{% for " + match.group(1).strip() + " in " + match.group(2).strip() + " %}"
    return None


def _render_error(args: str) -> Optional[str]:
    clean_arg = args.strip().strip("'\"")
    return "{% if errors.has('" + clean_arg + "') %}{% set message = errors.first('" + clean_arg + "') %}"


def compile_directives(source: str) -> str:
    """Rewrite Forge directives into Jinja syntax."""
    source = _EXTENDS_RE.sub(
        lambda m: '{% extends "' + resolve_view_path(m.group(1)) + '" %}', source
    )
    source = _INCLUDE_RE.sub(
        lambda m: '{% include "' + resolve_view_path(m.group(1)) + '" %}', source
    )
    source = _replace_paren_directive(source, "section", _render_section)
    source = _replace_paren_directive(source, "yield", _render_yield)
    source = _replace_paren_directive(source, "elseif", lambda a: "{% elif " + a + " %}")
    source = _replace_paren_directive(source, "if", lambda a: "{% if " + a + " %}")
    source = _replace_paren_directive(source, "foreach", _render_foreach)
    source = _replace_paren_directive(source, "can", lambda a: "{% if can(" + a + ") %}")
    source = _replace_paren_directive(source, "error", _render_error)

    for pattern, replacement in _COMPILED:
        source = pattern.sub(replacement, source)
    return source


#: Every directive Forge compiles, for the message that lists them.
SUPPORTED_DIRECTIVES = (
    "@extends", "@include", "@section/@endsection", "@yield", "@if/@elseif/@else/@endif",
    "@foreach/@endforeach", "@auth/@endauth", "@guest/@endguest", "@can/@endcan",
    "@error/@enderror", "@csrf", "@method", "@honeypot", "@antispam",
)

#: CSS at-rules, which legitimately leave `@name` in a template's output.
_CSS_AT_RULES = frozenset({
    "media", "supports", "import", "container", "layer", "font-face", "keyframes",
    "page", "charset", "namespace", "property", "scope", "starting-style", "document",
    "counter-style", "font-feature-values", "-webkit-keyframes",
})

#: Directive-shaped text left after compiling: `@name(` anywhere, or `@name`
#: opening a line (`@for x in items`, `@endfor`).
_LEFTOVER_RE = re.compile(
    r"(?<![\w@.])@([a-z][\w-]*)\s*\(|^[ \t]*@([a-z][\w-]*)\b", re.MULTILINE
)


def unknown_directives(compiled: str) -> list:
    """Return `(name, offset)` for each directive Forge did not compile.

    Args:
        compiled: A template after `compile_directives`.

    Returns:
        The leftover directive names with their character offsets.
    """
    found = [
        (match.group(1) or match.group(2), match.start())
        for match in _LEFTOVER_RE.finditer(compiled)
    ]
    return [(name, offset) for name, offset in found if name not in _CSS_AT_RULES]


def _check_directives(compiled: str, template: str, filename: Optional[str]) -> None:
    """Refuse a template that still holds a directive Forge does not know.

    An unknown directive used to be sent to the browser as literal text.

    Raises:
        TemplateSyntaxError: Naming the directive, its line and what is supported.
    """
    leftovers = unknown_directives(compiled)
    if not leftovers:
        return
    name, offset = leftovers[0]
    hint = (
        " `@include` takes only a view name; set variables before it instead of passing data."
        if name == "include" else ""
    )
    raise TemplateSyntaxError(
        f"Unknown Forge directive @{name}.{hint} Supported: {', '.join(SUPPORTED_DIRECTIVES)}. "
        f"Plain Jinja tags ({{% ... %}}) also work.",
        compiled.count("\n", 0, offset) + 1,
        template,
        filename,
    )


class DebugUndefined(StrictUndefined):
    """Fail loudly on a missing template variable, except in a truth test.

    Printing, reading an attribute of, or iterating an undefined name raises,
    so `{{ usr.name }}` is an error instead of an empty string. `{% if flash %}`
    stays False, since testing for an optional value is the common and correct
    use. Active only with `APP_DEBUG` on.
    """

    def __bool__(self) -> bool:
        return False


def _debug_enabled(app: Optional[Any]) -> bool:
    """Return whether `APP_DEBUG` is on for `app`; False without an application."""
    if app is None:
        return False
    try:
        return bool(app.make("config").get("app.APP_DEBUG", False))
    except (KeyError, AttributeError):
        return False


class DirectiveLoader(BaseLoader):
    """Wraps a loader, translating directives as each template is read."""

    def __init__(self, inner: BaseLoader):
        self.inner = inner

    def get_source(self, environment, template):
        source, filename, uptodate = self.inner.get_source(environment, template)
        compiled = compile_directives(source)
        _check_directives(compiled, template, filename)
        return compiled, filename, uptodate

    def list_templates(self):
        return self.inner.list_templates()


# -- view helpers available inside every template --------------------------------

def csrf_token() -> str:
    from engine.http.session import get_current_session

    session = get_current_session()
    return session.token() if session is not None else ""


def csrf_field() -> Markup:
    return Markup(f'<input type="hidden" name="_token" value="{csrf_token()}">')


def auth_user() -> Any:
    from engine.container.application import Container

    # Only "no auth service bound" means guest. A misconfigured identity
    # model used to be swallowed here too, rendering every page as a guest.
    try:
        auth = Container.getInstance().make("auth")
    except KeyError:
        return None
    return auth.user()


def can(ability: str, *args) -> bool:
    from engine.container.application import Container

    try:
        gate = Container.getInstance().make("gate")
    except KeyError:
        return False
    return bool(gate.allows(ability, auth_user(), *args))


def route_url(name: str, **params) -> str:
    """Resolve a named route for a template.

    Errors propagate. Returning `"/"` on failure — as this did — turned a
    mistyped route name into a link to the homepage, so the page rendered fine
    and the navigation was quietly wrong.
    """
    from engine.container.application import Container

    return Container.getInstance().make("router").url_for(name, **params)


def asset(path: str, version: Any = None) -> str:
    """URL for a file under `public/`, with a cache-busting query string.

        {{ asset('assets/css/craft-theme.css') }}
        -> /assets/css/craft-theme.css?ver=0.1.0

    The version defaults to the application version, so a release invalidates
    every cached asset at once. In debug the file's modification time is used
    instead, so an edit shows up on the next reload without a version bump.
    """
    path = "/" + str(path).lstrip("/")

    if version is None:
        if config_value("app.APP_DEBUG"):
            import os

            from engine.container.application import Container

            try:
                base = getattr(Container.getInstance(), "base_path", os.getcwd())
                stamp = os.path.getmtime(os.path.join(base, "public", path.lstrip("/")))
                version = int(stamp)
            except (OSError, Exception):
                version = None
        if version is None:
            version = config_value("app.APP_VERSION", "0")

    return f"{path}?ver={version}"


def config_value(key: str, default: Any = None) -> Any:
    from engine.container.application import Container

    try:
        return Container.getInstance().make("config").get(key, default)
    except KeyError:
        return default


def active_locale() -> str:
    """The locale in effect for this request.

    Templates used to read `config('app.locale')`, but the config repository
    registers the key as `APP_LOCALE` / `app_locale` — there is no `locale`, so
    that lookup always returned None and no language ever showed as active.
    """
    from engine.support.translation import get_current_locale

    return str(
        get_current_locale()
        or config_value("app.APP_LOCALE")
        or config_value("app.app_locale")
        or "en"
    )


def session_value(key: str, default: Any = None) -> Any:
    from engine.http.session import get_current_session

    session = get_current_session()
    return session.get(key, default) if session is not None else default

def old_input(key: str, default: Any = "") -> Any:
    """Previously submitted value, flashed back after a failed validation."""
    return (session_value("_old_input") or {}).get(key, default)


def current_errors() -> Any:
    """Validation errors flashed back to the session."""
    from engine.validation.error_bag import ViewErrorBag

    raw = session_value("_errors") or session_value("errors") or {}
    if isinstance(raw, ViewErrorBag):
        return raw
    return ViewErrorBag(raw)


def honeypot_field(field_name: Optional[str] = None, action: str = "") -> Markup:
    """Render anti-spam honeypot and time-trap fields for forms."""
    from engine.security.antispam import AntiSpamService

    return Markup(AntiSpamService().generate_fields(field_name=field_name, action=action))


def antispam_fields(action: str = "") -> Markup:
    """Convenience alias for honeypot_field."""
    return honeypot_field(action=action)


class Forge:
    """Renders templates from `resources/views`."""

    def __init__(self, app: Optional[Any] = None):
        self.app = app
        base_path = app.base_path if app else os.getcwd()
        views_dir = os.path.join(base_path, "resources", "views")
        if not os.path.exists(views_dir):
            views_dir = os.getcwd()

        self.views_dir = views_dir
        self.env = Environment(
            loader=DirectiveLoader(FileSystemLoader(views_dir)),
            autoescape=True,
            undefined=DebugUndefined if _debug_enabled(app) else Undefined,
        )
        self.env.globals.update(
            {
                "csrf_token": csrf_token,
                "csrf_field": csrf_field,
                "honeypot_field": honeypot_field,
                "antispam_fields": antispam_fields,
                "auth": auth_user,
                "can": can,
                "route": route_url,
                "asset": asset,
                "config": config_value,
                "locale": active_locale,
                "session": session_value,
                "old": old_input,
                "errors": current_errors(),
            }
        )

        from engine.support.collection import __ as translate

        self.env.globals["__"] = translate

    def share(self, key: str, value: Any) -> None:
        """Make a value available to every template."""
        self.env.globals[key] = value

    def exists(self, template_name: str) -> bool:
        try:
            self.env.get_template(self._resolve(template_name))
            return True
        except TemplateNotFound:
            return False

    @staticmethod
    def _resolve(template_name: str) -> str:
        return resolve_view_path(template_name)

    def render(self, template_name: str, data: Optional[Dict[str, Any]] = None) -> str:
        """Render a template with request context and flashed validation errors."""
        ctx = dict(data or {})
        if "errors" not in ctx:
            ctx["errors"] = current_errors()
        template = self.env.get_template(self._resolve(template_name))
        return template.render(**ctx)


__all__ = ["Forge", "compile_directives", "csrf_token", "csrf_field", "honeypot_field", "antispam_fields"]
