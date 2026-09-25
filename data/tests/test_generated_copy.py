"""Generated screens carry translation keys, and the generators seed every key.

The first code an agent reads in a new project is what `make:auth` and
`make:admin` wrote. It used to hold hardcoded English, so the example taught
the pattern the project's own language rules reject. These tests hold the
generated views and controllers to the rule: no visible copy outside a
`__()` call, and every key used has a row in `en`, `pt-BR` and `es`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import ast
import os
import re

import pytest

from craft.cli import auth_scaffolder

ENGINE_CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine", "cli")
ADMIN_ROOT = os.path.join(ENGINE_CLI, "admin_templates")
LOCALES = {"en", "pt-BR", "es"}

#: Attribute values a person reads.
_VISIBLE_ATTRIBUTE = re.compile(r'\b(?:title|placeholder|aria-label|alt)="([^"]*)"')
#: Technical examples that are identifiers, not copy.
_TECHNICAL_VALUES = {"field_name", "support-team"}
_KEY_CALL = re.compile(r"""__\(\s*['"]([a-z0-9_]+(?:\.[a-z0-9_]+)+)['"]""")


def _generated_views():
    for name in ("login_view_stub", "register_view_stub", "dashboard_view_stub"):
        yield name, getattr(auth_scaffolder, name)()
    views = os.path.join(ADMIN_ROOT, "resources", "views")
    for folder, _, names in os.walk(views):
        for file_name in sorted(names):
            path = os.path.join(folder, file_name)
            with open(path, encoding="utf-8") as handle:
                yield os.path.relpath(path, ADMIN_ROOT), handle.read()


def _visible_text(source: str) -> str:
    """Return what a browser would show that did not come from an expression."""
    for pattern in (
        r"\{#.*?#\}", r"<script\b.*?</script>", r"<style\b.*?</style>", r"<code\b.*?</code>",
        r"\{\{.*?\}\}", r"\{%.*?%\}", r"@\w+\s*\((?:[^()]|\([^()]*\))*\)", r"@\w+",
        r"<!--.*?-->", r"<[^>]+>", r"&#?\w+;",
    ):
        source = re.sub(pattern, " ", source, flags=re.DOTALL)
    return " ".join(source.split())


def _seeded_rows(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign) and node.targets[0].id == "ROWS")
    seeded: dict = {}
    for key, locale, value in ast.literal_eval(assignment.value):
        assert value.strip(), ("empty_value", key, locale)
        seeded.setdefault(key, set()).add(locale)
    return seeded


def _seeded_keys() -> dict:
    auth = os.path.join(ENGINE_CLI, "auth_templates", "database", "migrations",
                        "2026_09_25_000010_seed_auth_translations.py.stub")
    admin = os.path.join(ADMIN_ROOT, "database", "migrations", "2026_09_25_000011_seed_admin_translations.py.stub")
    return {**_seeded_rows(auth), **_seeded_rows(admin)}


def _used_keys() -> set:
    sources = [source for _, source in _generated_views()]
    sources.append(auth_scaffolder.auth_controller_stub())
    controllers = os.path.join(ADMIN_ROOT, "app", "Http", "Controllers")
    for folder, _, names in os.walk(controllers):
        for file_name in names:
            with open(os.path.join(folder, file_name), encoding="utf-8") as handle:
                sources.append(handle.read())
    return {key for source in sources for key in _KEY_CALL.findall(source)}


@pytest.mark.parametrize("name,source", list(_generated_views()), ids=lambda value: value if isinstance(value, str) and "\n" not in value else "")
def test_a_generated_view_shows_no_hardcoded_copy(name, source):
    assert _visible_text(source) == "", name
    for value in _VISIBLE_ATTRIBUTE.findall(source):
        assert value.startswith("{{") or value in _TECHNICAL_VALUES, (name, value)


def test_generated_controllers_translate_their_messages():
    source = auth_scaffolder.auth_controller_stub()
    assert "These credentials do not match" not in source
    with open(os.path.join(ADMIN_ROOT, "app", "Http", "Controllers", "Admin", "CrudBuilderController.py.stub"),
              encoding="utf-8") as handle:
        crud = handle.read()
    assert not re.search(r'errors\.append\(f?"', crud)
    assert '"errors": [f"' not in crud


def test_every_key_used_is_seeded_in_every_locale():
    seeded = _seeded_keys()
    missing = {key: sorted(LOCALES - seeded.get(key, set())) for key in _used_keys()}
    assert {key: locales for key, locales in missing.items() if locales} == {}


def test_no_seeded_key_goes_unused():
    assert set(_seeded_keys()) - _used_keys() == set()
