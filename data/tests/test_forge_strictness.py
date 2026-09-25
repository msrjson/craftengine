"""Forge fails loudly on what it cannot render, instead of shipping it as text."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os

import pytest
from jinja2 import DictLoader, Environment, TemplateSyntaxError, UndefinedError

from craft.view.forge import DebugUndefined, DirectiveLoader, compile_directives, unknown_directives

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")


def _render(source: str, undefined=DebugUndefined, **data) -> str:
    env = Environment(loader=DirectiveLoader(DictLoader({"page": source})), undefined=undefined)
    return env.get_template("page").render(**data)


class TestUnknownDirectives:
    def test_an_unknown_directive_names_itself_and_its_line(self):
        with pytest.raises(TemplateSyntaxError) as raised:
            _render("<ul>\n@for x in items\n<li>{{ x }}</li>\n@endfor\n</ul>")
        assert "@for" in str(raised.value) and raised.value.lineno == 2

    def test_include_with_data_explains_the_limit(self):
        with pytest.raises(TemplateSyntaxError, match="takes only a view name"):
            _render("@include('partials.card', {'title': 'x'})")

    @pytest.mark.parametrize("source", [
        "<style>@media (max-width: 600px) { a { color: red } }</style>",
        "<style>\n@import url(x.css);\n@font-face { font-family: x }\n</style>",
        "<p>Write to team@example.com or follow @craft on the forum.</p>",
    ])
    def test_css_rules_and_prose_are_not_directives(self, source):
        assert unknown_directives(compile_directives(source)) == []

    @pytest.mark.parametrize("source", [
        "@foreach(items as item){{ item }}@endforeach",
        "@foreach(item in items){{ item }}@endforeach",
    ])
    def test_foreach_accepts_both_orders(self, source):
        assert _render(source, items=[1, 2]) == "12"


class TestUndefinedVariables:
    def test_printing_an_undefined_name_raises_in_debug(self):
        with pytest.raises(UndefinedError, match="usr"):
            _render("{{ usr.name }}", user={"name": "Ada"})

    def test_a_truth_test_on_an_optional_value_is_false(self):
        assert _render("{% if flash %}shown{% endif %}done") == "done"

    def test_the_default_filter_still_works(self):
        assert _render("{{ title | default('Untitled') }}") == "Untitled"

    def test_without_debug_an_undefined_name_renders_empty(self):
        from jinja2 import Undefined

        assert _render("[{{ usr }}]", undefined=Undefined) == "[]"


def _engine_templates():
    for folder, _, names in os.walk(ENGINE):
        for name in names:
            if ".forge.py" in name or name.endswith(".html"):
                yield os.path.join(folder, name)


def _scaffolder_views():
    """View stubs embedded as strings in the generator modules."""
    from craft.cli import auth_scaffolder

    for attribute in dir(auth_scaffolder):
        if attribute.endswith("_view_stub"):
            yield attribute, getattr(auth_scaffolder, attribute)()


@pytest.mark.parametrize("path", sorted(_engine_templates()), ids=lambda p: os.path.relpath(p, ENGINE))
def test_every_template_the_engine_ships_compiles_cleanly(path):
    with open(path, encoding="utf-8") as handle:
        assert unknown_directives(compile_directives(handle.read())) == []


@pytest.mark.parametrize("name,source", sorted(_scaffolder_views()))
def test_every_view_make_auth_writes_compiles_cleanly(name, source):
    assert unknown_directives(compile_directives(source)) == []
