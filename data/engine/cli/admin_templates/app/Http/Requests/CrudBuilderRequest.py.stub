"""FormRequest for the admin CRUD builder entity name."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Auth
from craft.validation import FormRequest


class CrudBuilderRequest(FormRequest):
    """Validates only the entity name.

    Field rows are dynamic (repeatable, JS-managed indexes), so they are
    parsed and checked directly in `CrudBuilderController` rather than
    through a flat rule set here.
    """

    def authorize(self) -> bool:
        return Auth.user() is not None

    def rules(self) -> dict:
        return {
            "entity": ["required", "string", "regex:^[A-Za-z][A-Za-z0-9_]*$", "max:64"],
        }
