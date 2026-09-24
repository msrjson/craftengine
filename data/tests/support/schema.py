"""Schema the test-suite needs for its own identity models.

The engine's migrations create `users`; the RBAC tables are a project concern
and a project may generate them later. The suite therefore creates whatever is
missing itself, idempotently: where a migration already built the table, this
is a no-op, and where it did not, the tests still have somewhere to write.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Callable, Dict

from craft.facades import DB, Schema


def _users(table: Any) -> Any:
    return (
        table.id(),
        table.uuid("uuid").nullable(),
        table.string("name"),
        table.string("email").unique(),
        table.string("password"),
        table.boolean("is_admin").default(False),
        table.string("type").default("user"),
        table.datetime("email_verified_at").nullable(),
        table.string("remember_token", 100).nullable(),
        table.string("api_token", 80).nullable(),
        table.uuid("tenant_id").nullable(),
        table.timestamps(),
    )


def _roles(table: Any) -> Any:
    return (
        table.id(),
        table.uuid("uuid").nullable(),
        table.string("name").unique(),
        table.string("slug").unique(),
        table.text("description").nullable(),
        table.timestamps(),
    )


def _permissions(table: Any) -> Any:
    return (
        table.id(),
        table.uuid("uuid").nullable(),
        table.string("name").unique(),
        table.string("slug").unique(),
        table.timestamps(),
    )


def _groups(table: Any) -> Any:
    return (
        table.id(),
        table.string("name").unique(),
        table.string("slug").unique(),
        table.text("description").nullable(),
        table.timestamps(),
    )


def _pivot(left: str, right: str) -> Callable[[Any], Any]:
    """Build a grant pivot carrying the optional ABAC `conditions` column."""

    def blueprint(table: Any) -> Any:
        return (
            table.id(type="integer"),
            table.big_integer(left),
            table.big_integer(right),
            table.text("conditions").nullable(),
            table.timestamps(),
        )

    return blueprint


#: Every table the suite's identity models read or write, in creation order.
IDENTITY_TABLES: Dict[str, Callable[[Any], Any]] = {
    "users": _users,
    "roles": _roles,
    "permissions": _permissions,
    "groups": _groups,
    "role_user": _pivot("user_id", "role_id"),
    "permission_role": _pivot("permission_id", "role_id"),
    "group_user": _pivot("user_id", "group_id"),
    "group_role": _pivot("group_id", "role_id"),
    "permission_group": _pivot("permission_id", "group_id"),
    "permission_user": _pivot("permission_id", "user_id"),
}


def ensure_identity_schema() -> None:
    """Create any identity table the migrations did not already build."""
    for name, blueprint in IDENTITY_TABLES.items():
        if not Schema.has_table(name):
            Schema.create_table(name, blueprint)
    DB.forget_schema_cache()
