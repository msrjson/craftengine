"""Static checks of a project's wiring, run by `craft doctor`.

Each check looks for one mistake that otherwise surfaces late - on the first
request, as an empty page, or as a check that quietly denies everyone - and
reports it with a stable code, where it is, and the exact change to make. The
checks read the project; none of them writes anything.

Category: Core Framework (Support).
Relations:
  - Called by the `doctor` console command in `engine/cli/app.py`.
  - Reuses the kernel's own middleware resolution, Forge's directive scan and
    the identity registry, so a project that passes here passes at runtime.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import difflib
import importlib
import inspect
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, List

ERROR = "error"
WARNING = "warning"

#: Tables the engine writes to on its own, and the subsystem that needs each.
ENGINE_TABLES = {
    "translations": "translation lookups (`__()`)",
    "sessions": "the database session driver",
    "jobs": "the database queue",
    "failed_jobs": "the database queue",
    "scheduler_runs": "ScheduleManager.run_due_with_catchup()",
    "security_events": "honeypot, anti-spam and firewall audit",
    "auth_cooldowns": "sign-in throttling",
    "auth_audit_logs": "sign-in audit",
    "firewall_rules": "the firewall",
}

#: Route middleware that asks the user model for a capability.
_CAPABILITY_ALIASES = {"role": "has_role", "permission": "has_permission", "group": "in_group"}

_TRANSLATION_CALL = re.compile(r"__\(\s*['\"]([a-z0-9_]+(?:\.[a-z0-9_]+)+)['\"]")


#: Developer-facing text per finding code, with named placeholders filled from
#: the finding's params. Engineer diagnostics, like log lines: never shown to an
#: application's end users.
CATALOG = {
    "ROUTE_MIDDLEWARE_INVALID": ("{detail}", "Fix the middleware string on this route in routes/*.py."),
    "ROUTE_ACTION_NOT_FOUND": (
        "{controller} has no method {method}. Closest: {closest}.",
        "Add the method or point the route at an existing one.",
    ),
    "IDENTITY_MODEL_NOT_CONFIGURED": ("{detail}", "Correct the dotted path in config/auth.py, or run craft make:auth."),
    "USER_MODEL_NOT_AUTHORIZABLE": (
        "Routes call {methods}, which the user model does not define.",
        "Mix craft.auth.models.AuthorizableMixin into the user model.",
    ),
    "VIEW_UNKNOWN_DIRECTIVE": (
        "@{directive} is not a Forge directive and would render as text.",
        "Use a supported directive (documentation/views.md) or a Jinja tag.",
    ),
    "DATABASE_UNREACHABLE": (
        "The database could not be reached; table checks were skipped.",
        "Start the database or fix the connection settings.",
    ),
    "ENGINE_TABLE_MISSING": (
        "Table {table} does not exist; {used_by} will not work.",
        "Add a migration creating the table if the project uses {used_by}.",
    ),
    "MODEL_TABLE_MISSING": (
        "Table {table} does not exist.",
        "Run craft migrate, or set __table__ on the model to the real table name.",
    ),
    "TRANSLATION_MISSING": (
        "Key {key} has no row for {locales}.",
        "Add the rows in a migration or seeder: en, pt-BR and es in the same change.",
    ),
}


@dataclass(frozen=True)
class Finding:
    """One problem found in the project: a code, a place, and the values to report."""

    level: str
    code: str
    where: str
    params: tuple = ()

    def message(self) -> str:
        """Return the catalog text for this code with its params filled in."""
        return CATALOG[self.code][0].format(**dict(self.params))

    def fix(self) -> str:
        """Return the catalog remedy for this code with its params filled in."""
        return CATALOG[self.code][1].format(**dict(self.params))

    def to_dict(self) -> dict:
        """Return the finding as a plain dictionary, for `--json`."""
        return {**asdict(self), "params": dict(self.params), "message": self.message(), "fix": self.fix()}


def _finding(level: str, code: str, where: str, **params: Any) -> Finding:
    return Finding(level, code, where, tuple(sorted((key, str(value)) for key, value in params.items())))


def run_all(app: Any, kernel: Any, base_path: str) -> List[Finding]:
    """Run every check and return the findings, errors first.

    Args:
        app: The booted application container.
        kernel: The HTTP kernel from `bootstrap/app.py`.
        base_path: The project root.

    Returns:
        Every finding, errors before warnings.
    """
    checks: List[Callable[[], Iterable[Finding]]] = [
        lambda: check_routes(app, kernel),
        lambda: check_identity_models(app),
        lambda: check_authorizable_user(app),
        lambda: check_views(base_path),
        lambda: check_engine_tables(app),
        lambda: check_model_tables(app, base_path),
        lambda: check_translations(app, base_path),
    ]
    findings = [finding for check in checks for finding in check()]
    return sorted(findings, key=lambda finding: finding.level != ERROR)


# -- routes ------------------------------------------------------------------------

def check_routes(app: Any, kernel: Any) -> Iterable[Finding]:
    """Resolve every route's middleware and confirm every action method exists."""
    for route in app.make("router").application_routes():
        where = " ".join(("|".join(route.methods), route.uri))
        try:
            kernel.resolve_route_middleware(route.middleware_list)
        except KeyError as exc:
            yield _finding(ERROR, "ROUTE_MIDDLEWARE_INVALID", where, detail=_plain(exc))
        yield from _check_action(route.action, where)


def _check_action(action: Any, where: str) -> Iterable[Finding]:
    if not isinstance(action, (list, tuple)) or len(action) != 2 or not isinstance(action[0], type):
        return
    controller, name = action
    if callable(getattr(controller, name, None)):
        return
    public = [attr for attr in dir(controller) if not attr.startswith("_")]
    close = difflib.get_close_matches(name, public, n=1)
    yield _finding(ERROR, "ROUTE_ACTION_NOT_FOUND", where,
                   controller=controller.__name__, method=name, closest=close[0] if close else "none")


# -- identity ----------------------------------------------------------------------

def check_identity_models(app: Any) -> Iterable[Finding]:
    """Every identity model path that is configured must import."""
    from engine.auth import registry

    config = app.make("config")
    for kind in ("user", "role", "permission", "group"):
        if not registry.configured_path(kind, config):
            continue
        try:
            registry.model_for(kind, config)
        except registry.IdentityModelNotConfigured as exc:
            yield _finding(ERROR, exc.code, registry.config_key(kind), detail=str(exc))


def check_authorizable_user(app: Any) -> Iterable[Finding]:
    """A `role:`/`permission:`/`group:` route needs a user model that can answer it."""
    from engine.auth import registry

    needed = sorted({
        method
        for route in app.make("router").application_routes()
        for entry in route.middleware_list if isinstance(entry, str)
        for alias, method in _CAPABILITY_ALIASES.items() if entry.startswith(alias + ":")
    })
    if not needed:
        return
    try:
        user_model = registry.model_for("user", app.make("config"))
    except registry.IdentityModelNotConfigured as exc:
        yield _finding(ERROR, exc.code, "auth.models.user", detail=str(exc))
        return
    missing = [method for method in needed if not callable(getattr(user_model, method, None))]
    if missing:
        yield _finding(ERROR, "USER_MODEL_NOT_AUTHORIZABLE", _dotted(user_model), methods=", ".join(missing))


# -- views -------------------------------------------------------------------------

def check_views(base_path: str) -> Iterable[Finding]:
    """Every template must compile without an unknown Forge directive."""
    from engine.view.forge import compile_directives, unknown_directives

    for path in _files(os.path.join(base_path, "resources", "views"), (".forge.py", ".html")):
        with open(path, encoding="utf-8") as handle:
            compiled = compile_directives(handle.read())
        for name, offset in unknown_directives(compiled):
            line = compiled.count("\n", 0, offset) + 1
            yield _finding(ERROR, "VIEW_UNKNOWN_DIRECTIVE", _location(path, base_path, line), directive=name)


# -- database ----------------------------------------------------------------------

def check_engine_tables(app: Any) -> Iterable[Finding]:
    """Report engine tables that do not exist; the subsystem using each degrades."""
    has_table = _table_probe(app)
    if has_table is None:
        yield _finding(WARNING, "DATABASE_UNREACHABLE", "config/database.py")
        return
    for table, used_by in ENGINE_TABLES.items():
        if not has_table(table):
            yield _finding(WARNING, "ENGINE_TABLE_MISSING", table, table=table, used_by=used_by)


def check_model_tables(app: Any, base_path: str) -> Iterable[Finding]:
    """Every model under app/Models must have its table."""
    has_table = _table_probe(app)
    if has_table is None:
        return
    for model in _project_models(base_path):
        table = model.get_table_name()
        if not has_table(table):
            yield _finding(ERROR, "MODEL_TABLE_MISSING", _dotted(model), table=table)


def check_translations(app: Any, base_path: str) -> Iterable[Finding]:
    """Every key a view translates needs a row in each offered locale."""
    has_table = _table_probe(app)
    if has_table is None or not has_table("translations"):
        return
    locales = list(app.make("config").get("app.APP_LOCALES") or ["en"])
    db = app.make("db")
    for key, where in sorted(_translation_keys(base_path).items()):
        rows = db.table("translations").where("key", key).where_in("locale", locales).get()
        missing = sorted(set(locales) - {row["locale"] for row in rows})
        if missing:
            yield _finding(WARNING, "TRANSLATION_MISSING", where, key=key, locales=", ".join(missing))


# -- helpers -----------------------------------------------------------------------

def _dotted(cls: type) -> str:
    return ".".join((cls.__module__, cls.__name__))


def _location(path: str, base_path: str, line: int) -> str:
    return ":".join((os.path.relpath(path, base_path), str(line)))


def _plain(exc: BaseException) -> str:
    return str(exc.args[0]) if isinstance(exc, KeyError) and exc.args else str(exc)


def _files(root: str, suffixes: tuple) -> Iterable[str]:
    for folder, _, names in os.walk(root):
        for name in sorted(names):
            if name.endswith(suffixes):
                yield os.path.join(folder, name)


def _table_probe(app: Any) -> Any:
    """Return a `has_table(name)` callable, or None when the database is unreachable."""
    try:
        schema = app.make("schema")
        schema.has_table("translations")
    except (KeyError, OSError, RuntimeError) as exc:
        del exc
        return None
    except Exception as exc:  # noqa: BLE001 - driver errors have no common base class
        if "connect" in str(exc).lower() or "could not" in str(exc).lower():
            return None
        raise
    return schema.has_table


def _project_models(base_path: str) -> Iterable[type]:
    from engine.orm.model import Model

    for path in _files(os.path.join(base_path, "app", "Models"), (".py",)):
        if os.path.basename(path).startswith("_"):
            continue
        module_name = os.path.relpath(path, base_path)[:-3].replace(os.sep, ".")
        module = importlib.import_module(module_name)
        for _, value in inspect.getmembers(module, inspect.isclass):
            if issubclass(value, Model) and value is not Model and value.__module__ == module_name:
                yield value


def _translation_keys(base_path: str) -> dict:
    found: dict = {}
    for path in _files(os.path.join(base_path, "resources", "views"), (".forge.py", ".html")):
        with open(path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, start=1):
                for key in _TRANSLATION_CALL.findall(line):
                    found.setdefault(key, _location(path, base_path, number))
    return found


def summary(total: int, errors: int) -> str:
    """Return the closing line of a doctor run."""
    return SUMMARY.format(total=total, errors=errors)


#: Closing line of a doctor run.
SUMMARY = "{total} finding(s), {errors} error(s)."


__all__ = ["CATALOG", "ENGINE_TABLES", "ERROR", "Finding", "SUMMARY", "WARNING", "run_all", "summary"]
