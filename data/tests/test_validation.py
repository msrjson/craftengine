"""Validator rules."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import uuid

import pytest

from craft.exceptions.handler import ValidationException
from craft.validation.validator import Validator


def check(data, rules) -> Validator:
    return Validator(data, rules)


class TestRuleSyntax:
    def test_list_and_pipe_syntax_agree(self):
        as_list = check({"a": ""}, {"a": ["required", "string"]})
        as_pipe = check({"a": ""}, {"a": "required|string"})
        assert as_list.errors.keys() == as_pipe.errors.keys()

    def test_unknown_rules_raise(self):
        # A typo'd rule silently doing nothing would leave the field
        # looking validated while it is not.
        with pytest.raises(ValueError):
            check({"a": "x"}, {"a": ["no_such_rule"]})

    def test_absent_optional_field_is_not_type_checked(self):
        # Nothing was submitted — reporting "must be a string" would be noise.
        assert check({}, {"a": ["string"]}).passes()

    def test_nullable_allows_an_empty_value(self):
        assert check({"a": None}, {"a": ["nullable", "integer"]}).passes()


class TestPresence:
    @pytest.mark.parametrize("value", [None, "", [], {}])
    def test_required_rejects_empty_values(self, value):
        assert check({"a": value}, {"a": ["required"]}).fails()

    def test_required_accepts_zero(self):
        assert check({"a": 0}, {"a": ["required"]}).passes()

    def test_required_rejects_a_missing_key(self):
        assert check({}, {"a": ["required"]}).fails()

    def test_required_if(self):
        rules = {"reason": ["required_if:status,rejected"]}
        assert check({"status": "rejected"}, rules).fails()
        assert check({"status": "approved"}, rules).passes()

    def test_required_with(self):
        rules = {"last_name": ["required_with:first_name"]}
        assert check({"first_name": "Ada"}, rules).fails()
        assert check({}, rules).passes()


class TestTypes:
    def test_integer_accepts_ints_and_numeric_strings(self):
        assert check({"a": 5}, {"a": ["integer"]}).passes()
        assert check({"a": "-5"}, {"a": ["integer"]}).passes()

    def test_integer_rejects_booleans(self):
        # bool subclasses int in Python — True must not pass as an integer.
        assert check({"a": True}, {"a": ["integer"]}).fails()

    def test_integer_rejects_text(self):
        assert check({"a": "abc"}, {"a": ["integer"]}).fails()

    def test_numeric_accepts_floats(self):
        assert check({"a": 1.5}, {"a": ["numeric"]}).passes()
        assert check({"a": "1.5"}, {"a": ["numeric"]}).passes()

    def test_string_rejects_numbers(self):
        assert check({"a": 5}, {"a": ["string"]}).fails()

    def test_boolean(self):
        assert check({"a": "1"}, {"a": ["boolean"]}).passes()
        assert check({"a": "maybe"}, {"a": ["boolean"]}).fails()

    def test_array(self):
        assert check({"a": [1, 2]}, {"a": ["array"]}).passes()
        assert check({"a": "no"}, {"a": ["array"]}).fails()

    def test_date(self):
        assert check({"a": "2026-08-06"}, {"a": ["date"]}).passes()
        assert check({"a": "not-a-date"}, {"a": ["date"]}).fails()


class TestFormats:
    @pytest.mark.parametrize("value", ["a@b.co", "first.last@sub.domain.org"])
    def test_valid_emails(self, value):
        assert check({"e": value}, {"e": ["email"]}).passes()

    @pytest.mark.parametrize("value", ["plain", "a@b", "@b.co", "a b@c.co"])
    def test_invalid_emails(self, value):
        assert check({"e": value}, {"e": ["email"]}).fails()

    def test_url(self):
        assert check({"u": "https://example.com/x"}, {"u": ["url"]}).passes()
        assert check({"u": "example.com"}, {"u": ["url"]}).fails()

    def test_uuid(self):
        assert check(
            {"u": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"}, {"u": ["uuid"]}
        ).passes()
        assert check({"u": "nope"}, {"u": ["uuid"]}).fails()

    def test_alpha_variants(self):
        assert check({"a": "abc"}, {"a": ["alpha"]}).passes()
        assert check({"a": "ab1"}, {"a": ["alpha"]}).fails()
        assert check({"a": "ab1"}, {"a": ["alpha_num"]}).passes()
        assert check({"a": "a-b_1"}, {"a": ["alpha_dash"]}).passes()

    def test_regex(self):
        assert check({"a": "AB12"}, {"a": [r"regex:^[A-Z]{2}\d{2}$"]}).passes()
        assert check({"a": "ab12"}, {"a": [r"regex:^[A-Z]{2}\d{2}$"]}).fails()


class TestSize:
    def test_min_and_max_on_strings_count_characters(self):
        assert check({"a": "abc"}, {"a": ["min:3"]}).passes()
        assert check({"a": "ab"}, {"a": ["min:3"]}).fails()
        assert check({"a": "abcd"}, {"a": ["max:3"]}).fails()

    def test_min_and_max_on_numbers_compare_value(self):
        assert check({"a": 10}, {"a": ["min:5"]}).passes()
        assert check({"a": 3}, {"a": ["min:5"]}).fails()

    def test_between(self):
        assert check({"a": 18}, {"a": ["between:18,120"]}).passes()
        assert check({"a": 17}, {"a": ["between:18,120"]}).fails()

    def test_size(self):
        assert check({"a": "abcd"}, {"a": ["size:4"]}).passes()
        assert check({"a": "abc"}, {"a": ["size:4"]}).fails()


class TestSetsAndComparisons:
    def test_in_and_not_in(self):
        assert check({"a": "draft"}, {"a": ["in:draft,published"]}).passes()
        assert check({"a": "x"}, {"a": ["in:draft,published"]}).fails()
        assert check({"a": "x"}, {"a": ["not_in:draft"]}).passes()

    def test_same_and_different(self):
        assert check({"a": 1, "b": 1}, {"a": ["same:b"]}).passes()
        assert check({"a": 1, "b": 2}, {"a": ["same:b"]}).fails()
        assert check({"a": 1, "b": 2}, {"a": ["different:b"]}).passes()

    def test_confirmed(self):
        assert check(
            {"password": "secret", "password_confirmation": "secret"},
            {"password": ["confirmed"]},
        ).passes()
        assert check(
            {"password": "secret", "password_confirmation": "typo"},
            {"password": ["confirmed"]},
        ).fails()

    def test_accepted(self):
        assert check({"terms": "on"}, {"terms": ["accepted"]}).passes()
        assert check({"terms": "no"}, {"terms": ["accepted"]}).fails()


class TestDatabaseRules:
    @pytest.fixture
    def taken_email(self) -> str:
        """An address unique to this test, so no other row can collide with it."""
        return f"taken-{uuid.uuid4().hex[:8]}@craft.local"

    @pytest.fixture(autouse=True)
    def seeded(self, migrated_database, taken_email):
        from tests.support.models import User

        return User.create({"name": "Taken", "email": taken_email, "password": "x"})

    def test_unique_rejects_an_existing_value(self, taken_email):
        assert check(
            {"email": taken_email}, {"email": ["unique:users,email"]}
        ).fails()

    def test_unique_accepts_a_free_value(self):
        free = f"free-{uuid.uuid4().hex[:8]}@craft.local"
        assert check(
            {"email": free}, {"email": ["unique:users,email"]}
        ).passes()

    def test_unique_can_ignore_the_current_record(self, seeded, taken_email):
        rules = {"email": [f"unique:users,email,{seeded.get_attribute('id')},id"]}
        assert check({"email": taken_email}, rules).passes()

    def test_exists(self, taken_email):
        assert check(
            {"email": taken_email}, {"email": ["exists:users,email"]}
        ).passes()
        ghost = f"ghost-{uuid.uuid4().hex[:8]}@craft.local"
        assert check(
            {"email": ghost}, {"email": ["exists:users,email"]}
        ).fails()


class TestResults:
    def test_errors_are_grouped_by_field(self):
        validator = check({"a": ""}, {"a": ["required"], "b": ["required"]})
        assert set(validator.errors) == {"a", "b"}

    def test_first_error(self):
        validator = check({}, {"a": ["required"]})
        assert "required" in validator.first_error("a")
        assert validator.first_error() is not None

    def test_error_messages_is_flat(self):
        validator = check({}, {"a": ["required"], "b": ["required"]})
        assert len(validator.error_messages()) == 2

    def test_validated_returns_only_ruled_fields(self):
        validator = check({"a": "x", "extra": "y"}, {"a": ["required"]})
        assert validator.validated() == {"a": "x"}

    def test_validated_raises_when_invalid(self):
        with pytest.raises(ValidationException):
            check({}, {"a": ["required"]}).validated()

    def test_custom_message_overrides_the_default(self):
        validator = Validator({}, {"a": ["required"]}, {"a": "Give me an A."})
        assert validator.errors["a"] == ["Give me an A."]
