"""A wrong facade call explains itself."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest


def test_a_missing_method_suggests_the_closest_with_its_signature(migrated_database):
    from craft.facades import AntiSpam

    with pytest.raises(AttributeError) as raised:
        AntiSpam.verfy
    message = str(raised.value)
    assert "AntiSpam facade" in message and "Did you mean verify(" in message
    assert "Public methods:" in message


def test_hasattr_still_answers_false(migrated_database):
    from craft.facades import AntiSpam

    assert not hasattr(AntiSpam, "no_such_method")


def test_importing_a_non_facade_names_where_it_lives():
    with pytest.raises(ImportError, match=r"craft\.validation\.Validator"):
        from craft.facades import Validator  # noqa: F401


def test_a_misspelled_facade_suggests_the_real_one():
    with pytest.raises(ImportError, match="Did you mean 'Cache'"):
        from craft.facades import Cahce  # noqa: F401
