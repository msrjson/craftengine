"""
CrudBuilder — generates a full vertical slice (migration, model, controller,
FormRequest, Resource, JSON API route, and a server-rendered admin UI —
list/create/edit views, an admin controller, admin routes) for a described
entity, wired to real ORM calls.

Category: Core Framework (CLI).
Relations:
  - Reuses the stub builders in `engine/cli/generators.py` (extended to
    accept a `fields` list) instead of duplicating codegen.
  - Called from `dev.py make:crud` (`engine/cli/app.py`) and from the admin
    CRUD builder UI (`app/Http/Controllers/Admin/CrudBuilderController.py`).
  - Appends the JSON API route to `routes/api.py`, idempotently, after the
    `# CRUD Builder Routes` marker comment, and the admin HTML routes to
    `routes/web.py`, idempotently, after the `# CRUD Builder Admin Routes`
    marker comment.
References:
  - Guide: `documentation/crud-builder.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from engine.cli import generators, layout_scaffolder

#: DDL column type -> `Blueprint` method name on `engine/migrations/schema.py`.
FIELD_TYPES = {
    "string": "string",
    "text": "text",
    "integer": "integer",
    "big_integer": "big_integer",
    "small_integer": "small_integer",
    "float": "float",
    "boolean": "boolean",
    "decimal": "decimal",
    "date": "date",
    "datetime": "datetime",
    "json": "json",
}

ROUTES_MARKER = "# CRUD Builder Routes"
WEB_ROUTES_MARKER = "# CRUD Builder Admin Routes"


def normalize_field(field: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in defaults for a single field description."""
    name = field["name"]
    type_ = field.get("type", "string")
    if type_ not in FIELD_TYPES:
        raise ValueError(f"Unknown field type [{type_}] for field [{name}].")
    nullable = field.get("nullable", True)
    rules = field.get("rules")
    if not rules:
        rules = ["nullable"] if nullable else ["required"]
    return {"name": name, "type": type_, "rules": list(rules), "nullable": nullable}


def parse_fields(spec: str) -> List[Dict[str, Any]]:
    """Parse the `--fields "name:type:rule1|rule2,..."` CLI syntax.

    Each comma-separated entry is `name:type[:rule1|rule2|...]`. A field
    whose rules include `required` is treated as non-nullable; otherwise it
    defaults to nullable.
    """
    fields: List[Dict[str, Any]] = []
    for chunk in filter(None, (part.strip() for part in spec.split(","))):
        parts = chunk.split(":")
        name = parts[0].strip()
        type_ = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "string"
        rules = [r.strip() for r in parts[2].split("|")] if len(parts) > 2 and parts[2].strip() else []
        nullable = "required" not in rules
        fields.append(normalize_field({"name": name, "type": type_, "rules": rules, "nullable": nullable}))
    return fields


def _write(path: str, content: str, force: bool) -> str:
    if os.path.exists(path) and not force:
        raise FileExistsError(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    init_path = os.path.join(os.path.dirname(path), "__init__.py")
    if not os.path.exists(init_path):
        open(init_path, "a", encoding="utf-8").close()
    return path


def _write_view(path: str, content: str, force: bool) -> str:
    """Same overwrite discipline as `_write`, minus the `__init__.py`
    sibling — `resources/views/**` is never imported as a Python package,
    and the existing `posts/*.forge.py` views directory has no `__init__.py`
    either."""
    if os.path.exists(path) and not force:
        raise FileExistsError(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def _migration_content(name: str, table: str, fields: List[Dict[str, Any]]) -> str:
    column_lines = []
    for field in fields:
        method = FIELD_TYPES[field["type"]]
        line = f'        t.{method}("{field["name"]}")'
        if field.get("nullable", True):
            line += ".nullable()"
        column_lines.append(line + ",")
    columns_body = "\n".join(column_lines)
    return f'''"""Migration: {name}."""

from craft.migrations import Migration, Schema


def up():
    Schema.create_table("{table}", lambda t: (
        t.id(),
        t.uuid_key(),
{columns_body}
        t.timestamps(),
    ))


def down():
    Schema.drop_table("{table}")
'''



def _append_route(base_path: str, entity_class: str, slug: str) -> Optional[str]:
    """Register the generated controller as a JSON API resource.

    Registers in `routes/api.py` (not `routes/web.py`) via `Route.api_resource`,
    matching the existing `PostController` convention — the generated
    controller only returns JSON, and `web.py` routes are behind CSRF
    verification, which a JSON API client has no `_token` to satisfy. Every
    generated entity gets its own self-contained `Route.group(..., prefix=
    "/api/v1", ...)` block, so this never has to parse or mutate the existing
    group's lambda body.

    Idempotent: running `build_crud` twice for the same entity does not add
    a second import or route block. Writes are append-only after the marker
    comment, never touching existing lines.

    Write actions (`store`/`update`/`destroy`) get `write_middleware=["api",
    "auth"]`: `AuthenticateApiToken` ("api") resolves a bearer token into the
    auth manager first, then `RequireAuth` ("auth") is the alias that
    actually rejects the request when nobody ended up authenticated —
    `AuthenticateApiToken` alone never blocks a missing/invalid token, it
    just continues unauthenticated.
    """
    routes_path = os.path.join(base_path, "routes", "api.py")
    # A project generated by `craft new` has no routes/api.py. Returning early
    # here used to skip the registration silently while the command still
    # printed the API URL - which then answered 404. Create the file instead.
    if not os.path.isfile(routes_path):
        os.makedirs(os.path.dirname(routes_path), exist_ok=True)
        with open(routes_path, "w", encoding="utf-8") as handle:
            handle.write('"""API routes."""\n\nfrom craft.facades import Route\n')

    with open(routes_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    import_line = f"from app.Http.Controllers.{entity_class}Controller import {entity_class}Controller"
    marker_token = f'Route.api_resource("{slug}"'

    if marker_token in content:
        return routes_path  # already registered

    additions = []
    if import_line not in content:
        additions.append(import_line)

    group_block = (
        "Route.group(\n"
        "    lambda: (\n"
        f'        Route.api_resource("{slug}", {entity_class}Controller, write_middleware=["api", "auth"]),\n'
        "    ),\n"
        '    prefix="/api/v1",\n'
        f'    name="api.{slug}.",\n'
        ")"
    )
    additions.append(group_block)
    block = "\n".join(additions)

    if ROUTES_MARKER in content:
        content = content.rstrip("\n") + "\n" + block + "\n"
    else:
        content = content.rstrip("\n") + f"\n\n{ROUTES_MARKER}\n" + block + "\n"

    with open(routes_path, "w", encoding="utf-8") as handle:
        handle.write(content)

    return routes_path


def _append_web_route(base_path: str, admin_controller_class: str, slug: str) -> Optional[str]:
    """Register the generated admin controller's HTML CRUD routes.

    Registers in `routes/web.py` under `/admin/<slug>`, behind the `auth`
    middleware — same alias and area as `/admin/crud-builder`
    (`routes/web.py`). Uses `Route.resource()` (the HTML-form variant with
    `create`/`edit`, unlike `Route.api_resource()` used for the JSON side)
    nested in a `Route.group(..., prefix="/admin", middleware="auth", name=
    "admin.")` block, so every action — including reads — requires a logged
    -in user, matching the rest of the admin area. Named routes come out as
    `admin.<slug>.index` etc.

    Idempotent, mirroring `_append_route`: running `build_crud` twice for the
    same entity does not add a second import or route block.
    """
    routes_path = os.path.join(base_path, "routes", "web.py")
    if not os.path.isfile(routes_path):
        return None

    with open(routes_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    import_line = (
        f"from app.Http.Controllers.Admin.{admin_controller_class} import {admin_controller_class}"
    )
    marker_token = f'Route.resource("{slug}", {admin_controller_class})'

    if marker_token in content:
        return routes_path  # already registered

    additions = []
    if import_line not in content:
        additions.append(import_line)

    group_block = (
        "Route.group(\n"
        "    lambda: (\n"
        f"        Route.resource(\"{slug}\", {admin_controller_class}),\n"
        "    ),\n"
        '    prefix="/admin",\n'
        '    middleware="auth",\n'
        '    name="admin.",\n'
        ")"
    )
    additions.append(group_block)
    block = "\n".join(additions)

    if WEB_ROUTES_MARKER in content:
        content = content.rstrip("\n") + "\n" + block + "\n"
    else:
        content = content.rstrip("\n") + f"\n\n{WEB_ROUTES_MARKER}\n" + block + "\n"

    with open(routes_path, "w", encoding="utf-8") as handle:
        handle.write(content)

    return routes_path


def build_crud(
    entity: str,
    fields: List[Dict[str, Any]],
    base_path: str,
    *,
    resource_route: bool = True,
    force: bool = False,
    pretend: bool = False,
) -> Dict[str, Any]:
    """Generate a full CRUD slice for `entity` and return every path touched."""
    fields = [normalize_field(f) for f in fields]

    class_name = generators.studly(entity)
    table = generators.table_for(class_name)
    slug = table

    model_name = class_name
    request_name = f"Store{class_name}Request"
    resource_name = f"{class_name}Resource"
    controller_name = f"{class_name}Controller"
    admin_controller_name = f"{class_name}AdminController"

    created: Dict[str, Any] = {"entity": class_name, "files": {}, "pretend": pretend}

    # 1. Migration
    from engine.migrations.migrator import migration_filename

    migration_name = f"create_{table}_table"
    migrations_dir = os.path.join(base_path, "database", "migrations")
    migration_path = os.path.join(migrations_dir, migration_filename(generators.snake(migration_name)))
    if os.path.exists(migration_path) and not force and not pretend:
        raise FileExistsError(migration_path)
    if not pretend:
        os.makedirs(migrations_dir, exist_ok=True)
        with open(migration_path, "w", encoding="utf-8") as handle:
            handle.write(_migration_content(migration_name, table, fields))
    created["files"]["migration"] = migration_path

    # 2. Model
    model_path = os.path.join(base_path, "app", "Models", f"{model_name}.py")
    if not pretend:
        _write(model_path, generators.model_stub(model_name, fields=fields), force)
    created["files"]["model"] = model_path

    # 3. FormRequest
    request_path = os.path.join(base_path, "app", "Http", "Requests", f"{request_name}.py")
    if not pretend:
        _write(request_path, generators.request_stub(request_name, fields=fields), force)
    created["files"]["request"] = request_path

    # 4. Resource
    resource_path = os.path.join(base_path, "app", "Http", "Resources", f"{resource_name}.py")
    if not pretend:
        _write(resource_path, generators.resource_stub(resource_name, fields=fields), force)
    created["files"]["resource"] = resource_path

    # 5. Controller — wired to the model/request/resource above.
    controller_path = os.path.join(base_path, "app", "Http", "Controllers", f"{controller_name}.py")
    if not pretend:
        controller_content = generators.crud_controller_stub(
            controller_name, model_name, request_name, resource_name
        )
        _write(controller_path, controller_content, force)
    created["files"]["controller"] = controller_path

    # 6. JSON API route
    if resource_route:
        if not pretend:
            route_path = _append_route(base_path, model_name, slug)
            if route_path:
                created["files"]["routes"] = route_path
        else:
            created["files"]["routes"] = os.path.join(base_path, "routes", "api.py")

    # 7. Admin UI — list/create/edit views
    views_dir = os.path.join(base_path, "resources", "views", "admin", slug)
    index_view_path = os.path.join(views_dir, "index.forge.py")
    create_view_path = os.path.join(views_dir, "create.forge.py")
    edit_view_path = os.path.join(views_dir, "edit.forge.py")
    if not pretend:
        # The views extend `layouts.app`; a project generated by `craft new`
        # has no layout until something writes one.
        layout_path = layout_scaffolder.ensure_layout(base_path)
        if layout_path is not None:
            created["files"]["view_layout"] = layout_path
        _write_view(index_view_path, generators.admin_index_stub(class_name, slug, fields=fields), force)
        _write_view(create_view_path, generators.admin_form_stub(class_name, slug, fields=fields, mode="create"), force)
        _write_view(edit_view_path, generators.admin_form_stub(class_name, slug, fields=fields, mode="edit"), force)
    created["files"]["admin_view_index"] = index_view_path
    created["files"]["admin_view_create"] = create_view_path
    created["files"]["admin_view_edit"] = edit_view_path

    # 8. Admin HTML controller
    admin_controller_path = os.path.join(
        base_path, "app", "Http", "Controllers", "Admin", f"{admin_controller_name}.py"
    )
    if not pretend:
        admin_controller_content = generators.admin_controller_stub(
            admin_controller_name, model_name, request_name, slug
        )
        _write(admin_controller_path, admin_controller_content, force)
    created["files"]["admin_controller"] = admin_controller_path

    # 9. Admin HTML route
    if resource_route:
        if not pretend:
            admin_route_path = _append_web_route(base_path, admin_controller_name, slug)
            if admin_route_path:
                created["files"]["admin_routes"] = admin_route_path
        else:
            created["files"]["admin_routes"] = os.path.join(base_path, "routes", "web.py")

    return created



__all__ = ["build_crud", "parse_fields", "normalize_field"]

