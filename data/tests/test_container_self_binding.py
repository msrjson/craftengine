"""A service bound by its own dotted path resolves instead of recursing."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from engine.container.application import Container
from engine.events.dispatcher import EventDispatcher

DOTTED = "engine.events.dispatcher.EventDispatcher"


def test_a_dotted_path_bound_to_itself_builds_its_class():
    container = Container()
    container.bind(DOTTED)
    assert isinstance(container.make(DOTTED), EventDispatcher)


def test_a_dotted_path_bound_as_its_own_concrete_builds_its_class():
    container = Container()
    container.singleton(DOTTED, DOTTED)
    first = container.make(DOTTED)
    assert isinstance(first, EventDispatcher)
    assert container.make(DOTTED) is first
