"""FormRequest: authorization plus validation of request input."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.exceptions.handler import AuthorizationException, ValidationException
from craft.validation.form_request import FormRequest


class StoreThing(FormRequest):
    def rules(self):
        return {
            "title": ["required", "string", "max:10"],
            "count": ["nullable", "integer"],
        }


class ForbiddenRequest(StoreThing):
    def authorize(self):
        return False


class NormalisingRequest(StoreThing):
    def prepare_for_validation(self, data):
        data = dict(data)
        if "title" in data:
            data["title"] = str(data["title"]).strip()
        return data


class MessagedRequest(StoreThing):
    def messages(self):
        return {"title": "Give it a title."}


class TestValidation:
    def test_valid_input_passes(self):
        assert StoreThing({"title": "ok"}).passes() is True

    def test_validated_returns_only_ruled_fields(self):
        form = StoreThing({"title": "ok", "sneaky": "value"})
        assert form.validated() == {"title": "ok"}

    def test_rules_are_actually_enforced(self):
        # The old implementation returned the body untouched, so every rule
        # declared here was ignored.
        with pytest.raises(ValidationException):
            StoreThing({"title": "far too long to pass"}).validated()

    def test_missing_required_field_fails(self):
        form = StoreThing({})
        assert form.fails() is True
        assert "title" in form.errors

    def test_nullable_field_may_be_omitted(self):
        assert StoreThing({"title": "ok"}).passes() is True

    def test_bad_optional_value_still_fails(self):
        assert StoreThing({"title": "ok", "count": "abc"}).fails() is True

    def test_prepare_for_validation_runs_first(self):
        form = NormalisingRequest({"title": "   ok   "})
        assert form.validated() == {"title": "ok"}

    def test_custom_messages_are_used(self):
        assert MessagedRequest({}).errors["title"] == ["Give it a title."]


class TestAuthorization:
    def test_unauthorized_raises(self):
        with pytest.raises(AuthorizationException):
            ForbiddenRequest({"title": "ok"}).validated()

    def test_unauthorized_fails_even_with_valid_input(self):
        assert ForbiddenRequest({"title": "ok"}).passes() is False


class TestInputSources:
    def test_accepts_a_plain_dict(self):
        assert StoreThing({"title": "ok"}).data() == {"title": "ok"}

    def test_reads_from_a_request_object(self):
        class FakeRequest:
            def all(self):
                return {"title": "from-req"}  # within the max:10 rule

        assert StoreThing(FakeRequest()).validated() == {"title": "from-req"}

    def test_no_request_means_no_data(self):
        assert StoreThing().data() == {}

    def test_an_unparseable_body_degrades_to_empty_and_is_logged(self, caplog):
        class MalformedJson:
            def all(self):
                raise ValueError("Expecting value: line 1 column 1")

        with caplog.at_level("WARNING", logger="craft.validation"):
            assert StoreThing(MalformedJson()).data() == {}
        assert "form_request_body_unreadable" in caplog.text

    def test_any_other_failure_reading_the_request_propagates(self):
        # Swallowing it validated `{}` and reported every field as required,
        # hiding the real fault.
        class BrokenRequest:
            def all(self):
                raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            StoreThing(BrokenRequest()).data()
