"""Container failures name the cause instead of hiding it."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.container.application import Container


def test_an_unknown_key_suggests_bound_ones():
    container = Container()
    container.singleton("cache.store", lambda c: object())
    with pytest.raises(KeyError, match="Closest bound keys: cache.store"):
        container.make("cache.stor")


def test_the_fallback_container_says_no_application_booted():
    with pytest.raises(KeyError, match="No application has booted"):
        Container().make("db")


def test_a_missing_module_is_still_just_unbound():
    with pytest.raises(KeyError, match="not bound"):
        Container().make("no_such_package.Thing")


def test_an_error_inside_an_existing_module_propagates(tmp_path, monkeypatch):
    (tmp_path / "broken_service_module.py").write_text("import no_such_dependency_xyz\nclass Service: pass\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(ModuleNotFoundError, match="no_such_dependency_xyz"):
        Container().make("broken_service_module.Service")


def test_an_unresolvable_parameter_chains_the_reason():
    class Unbuildable:
        def __init__(self, secret):
            pass

    class Wrapper:
        def __init__(self, dep: Unbuildable):
            self.dep = dep

    with pytest.raises(ValueError, match=r"Cannot resolve parameter \[dep: Unbuildable\]") as raised:
        Container().make(Wrapper)
    assert isinstance(raised.value.__cause__, ValueError)
