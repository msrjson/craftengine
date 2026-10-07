"""A validation failure carries its stable `code` and `message_key`."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from craft.exceptions.handler import ExceptionHandler, ValidationException
from craft.validation.messages import KEY_PREFIX
from craft.validation.validator import Validator


def test_a_rule_failure_records_its_code_and_message_key():
    validator = Validator({"email": "not-an-email"}, {"email": "required|email"})
    assert validator.fails()

    entry = validator.errors.errors()["email"][0]
    assert entry["code"] == "email"
    assert entry["message_key"] == KEY_PREFIX + "email"
    assert entry["params"]["field"] == "email"
    # The rendered text is unchanged for templates and older callers.
    assert entry["message"] == validator.errors.first("email")
    assert isinstance(validator.errors.first("email"), str)


def test_every_failed_rule_is_recorded_separately():
    validator = Validator({}, {"name": "required|min:3"})
    codes = [entry["code"] for entry in validator.errors.errors()["name"]]
    assert codes == ["required"]


def test_a_message_key_is_reported_even_when_a_custom_message_wins_the_text():
    validator = Validator(
        {"email": "nope"},
        {"email": "email"},
        messages={"email": "Please check the address"},
    )
    entry = validator.errors.errors()["email"][0]
    assert entry["message"] == "Please check the address"
    assert entry["code"] == "email"


def test_the_http_payload_exposes_the_structured_details():
    validator = Validator({"email": "nope"}, {"email": "email"})
    with pytest.raises(ValidationException) as caught:
        validator.validated()

    payload = ExceptionHandler().to_payload(caught.value)
    # The string map every existing client reads is still there.
    assert payload["errors"]["email"]
    assert payload["error_details"]["email"][0]["code"] == "email"
