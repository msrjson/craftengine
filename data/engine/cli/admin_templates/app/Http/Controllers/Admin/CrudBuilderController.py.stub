"""Admin CRUD builder — define an entity visually and generate its CRUD slice."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json
import re

from craft.http.controller import Controller
from app.Http.Requests.CrudBuilderRequest import CrudBuilderRequest

FIELD_TYPES = (
    "string", "text", "integer", "big_integer", "small_integer",
    "float", "boolean", "decimal", "date", "datetime", "json"
)

FIELD_NAME_RE = re.compile(r"^field_name_(\d+)$")


class CrudBuilderController(Controller):
    """Renders the entity/field form and, on submit, calls `crud_builder.build_crud`.

    Field rows are repeatable in the browser (JS adds `field_name_N` /
    `field_type_N` / `field_required_N` inputs with an incrementing index), so
    they are parsed here from indexed keys rather than through a flat
    FormRequest rule set.
    """

    def index(self, request):
        return self.view("admin.crud_builder.index", {
            "show_sidebar": True,
            "field_types": FIELD_TYPES,
            "errors": [],
            "entity": "",
            "fields_json": "[]",
        })

    def store(self, request):
        form = CrudBuilderRequest(request)
        raw_rows_json = json.dumps(self._raw_field_rows(request))

        if form.fails():
            return self.view("admin.crud_builder.index", {
                "show_sidebar": True,
                "field_types": FIELD_TYPES,
                "errors": [msg for msgs in form.errors.values() for msg in msgs],
                "entity": request.input("entity", ""),
                "fields_json": raw_rows_json,
            })

        entity = form.validated()["entity"]
        fields, field_errors = self._parse_fields(request)

        if field_errors:
            return self.view("admin.crud_builder.index", {
                "show_sidebar": True,
                "field_types": FIELD_TYPES,
                "errors": field_errors,
                "entity": entity,
                "fields_json": raw_rows_json,
            })

        from craft.cli import crud_builder
        from craft.cli.app import base_path

        try:
            result = crud_builder.build_crud(entity, fields, base_path())
        except FileExistsError as exc:
            return self.view("admin.crud_builder.index", {
                "show_sidebar": True,
                "field_types": FIELD_TYPES,
                "errors": [f"A generated file already exists: {exc}"],
                "entity": entity,
                "fields_json": raw_rows_json,
            })
        except ValueError as exc:
            return self.view("admin.crud_builder.index", {
                "show_sidebar": True,
                "field_types": FIELD_TYPES,
                "errors": [str(exc)],
                "entity": entity,
                "fields_json": raw_rows_json,
            })

        return self.view("admin.crud_builder.result", {
            "show_sidebar": True,
            "entity": result["entity"],
            "files": result["files"],
        })

    # -- helpers -----------------------------------------------------------

    def _raw_field_rows(self, request):
        """Every submitted field row, unfiltered, for redisplay after a failure.

        Unlike `_parse_fields`, this keeps rows even when they are invalid
        (unknown type, blank name) so the browser can restore exactly what the
        user typed instead of silently dropping rows on a validation error.
        """
        data = request.all()
        indexes = sorted(
            int(match.group(1))
            for key in data
            if (match := FIELD_NAME_RE.match(key))
        )
        return [
            {
                "name": str(data.get(f"field_name_{index}", "")),
                "type": str(data.get(f"field_type_{index}", "string")),
                "required": bool(data.get(f"field_required_{index}")),
            }
            for index in indexes
        ]

    def _parse_fields(self, request):
        data = request.all()
        indexes = sorted(
            int(match.group(1))
            for key in data
            if (match := FIELD_NAME_RE.match(key))
        )

        fields = []
        errors = []
        for index in indexes:
            name = str(data.get(f"field_name_{index}", "")).strip()
            if not name:
                continue
            type_ = data.get(f"field_type_{index}", "string")
            if type_ not in FIELD_TYPES:
                errors.append(f"Unknown field type [{type_}] for field [{name}].")
                continue
            required = bool(data.get(f"field_required_{index}"))
            fields.append({
                "name": name,
                "type": type_,
                "nullable": not required,
                "rules": ["required"] if required else ["nullable"],
            })

        if not fields:
            errors.append("Define at least one field.")

        return fields, errors
