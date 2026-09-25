"""FormRequest for Craft Framework.

Subclass it to declare authorization and validation rules next to the endpoint
that needs them::

    class StorePostRequest(FormRequest):
        def authorize(self):
            return self.user() is not None

        def rules(self):
            return {"title": ["required", "string", "max:255"]}

    def store(self, form: StorePostRequest):
        data = form.validated()

A route action parameter annotated with a FormRequest subclass receives an
instance that has already been authorized and validated (see
`engine/http/kernel.py::bind_route_arguments`); constructing one by hand from
the request works the same way.

Category: Core Framework (Validation).
Relations:
  - Wraps `engine/validation/validator.py`; `validated()` authorizes first
    (raising `AuthorizationException`), then validates (raising
    `ValidationException`), both rendered by `engine/exceptions/handler.py`.
References:
  - Guide: `documentation/validation.md#formrequest`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, List, Optional

from engine.validation.validator import Validator


class FormRequest:
    """Authorizes and validates an incoming request's input."""

    def __init__(self, request: Any = None):
        self.request = request
        self._validator: Optional[Validator] = None

    antispam: bool = False
    antispam_action: str = ""

    # -- to override -----------------------------------------------------------

    def authorize(self) -> bool:
        return True

    def rules(self) -> Dict[str, List[Any]]:
        return {}

    def messages(self) -> Dict[str, str]:
        return {}

    def prepare_for_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Hook to normalise input before the rules run."""
        return data

    # -- input -----------------------------------------------------------------

    def data(self) -> Dict[str, Any]:
        """Every input on the request: query string plus parsed body."""
        request = self.request
        if request is None:
            return {}
        if isinstance(request, dict):
            return dict(request)
        if hasattr(request, "all"):
            try:
                return dict(request.all() or {})
            except Exception:
                return {}
        return {}

    def user(self) -> Any:
        if self.request is not None and hasattr(self.request, "user"):
            return self.request.user()
        return None

    # -- running ---------------------------------------------------------------

    def validator(self) -> Validator:
        if self._validator is None:
            data = self.prepare_for_validation(self.data())
            self._validator = Validator(data, self.rules(), self.messages())
        return self._validator

    @property
    def errors(self) -> Any:
        return self.validator().errors

    def error_bag(self) -> Any:
        return self.validator().error_bag()

    def passes_antispam(self) -> bool:
        from engine.security.antispam import AntiSpamService

        data = self.data()
        if self.antispam or self.antispam_action or "_craft_hp_name" in data or "_craft_hp_time" in data:
            antispam = AntiSpamService()
            is_clean, reason = antispam.verify(self.request or data, action=self.antispam_action)
            if not is_clean:
                self.validator().errors.setdefault("_antispam", []).append(f"Submission rejected ({reason})")
                return False
        return True

    def passes(self) -> bool:
        return self.authorize() and self.passes_antispam() and self.validator().passes()

    def fails(self) -> bool:
        return not self.passes()

    def validated(self) -> Dict[str, Any]:
        """Authorize, validate, and return only the fields that were ruled on.

        Raises `AuthorizationException` or `ValidationException`. This used to
        return the raw body without checking anything — every rule declared on a
        FormRequest was silently ignored.
        """
        cached = self.__dict__.get("_validated")
        if cached is not None:
            return dict(cached)

        if not self.authorize():
            from engine.exceptions.handler import AuthorizationException

            raise AuthorizationException("This action is unauthorized.")

        if not self.passes_antispam():
            from engine.exceptions.handler import ValidationException

            raise ValidationException(self.validator().errors.to_dict())

        self._validated = self.validator().validated()
        return dict(self._validated)


__all__ = ["FormRequest"]
