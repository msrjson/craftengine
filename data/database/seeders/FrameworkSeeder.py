"""Add missing framework authorization demo records without replacing live data."""

from typing import Any

from craft.auth.conditions import dump
from craft.facades import DB
from craft.seeding import Seeder

from app.Models.Group import Group
from app.Models.Module import Module
from app.Models.Permission import Permission
from app.Models.Role import Role
from app.Models.User import User
from database.seeders.TranslationSeeder import TranslationSeeder


def _ensure_model(model: Any, values: dict[str, Any]) -> Any:
    """Create a named starter record only when it is absent."""
    return model.query().where("slug", values["slug"]).first() or model.create(values)


def _ensure_pivot(table: str, values: dict[str, Any]) -> None:
    """Add a starter relation without changing an existing grant."""
    query = DB.table(table)
    for column, value in values.items():
        if column == "conditions":
            continue
        query = query.where(column, value)
    if query.first() is None:
        DB.table(table).insert(values)


def _id(record: Any) -> Any:
    return record.get_attribute("id")


class FrameworkSeeder(Seeder):
    """Seed missing framework reference data while preserving user edits."""

    def run(self) -> None:
        self.call(TranslationSeeder)
        # An existing authorization installation may have intentionally revoked
        # starter grants. Re-running a seeder must never restore those grants.
        if Group.query().where("slug", "content-team").first() is not None:
            return
        _ensure_model(Module, {"name": "Inventory Management", "slug": "inventory", "enabled": True})
        _ensure_model(Module, {"name": "Billing Services", "slug": "billing", "enabled": True})

        roles = {
            "admin": _ensure_model(Role, {"name": "Administrator", "slug": "admin"}),
            "user": _ensure_model(Role, {"name": "User", "slug": "user"}),
            "tenant-manager": _ensure_model(Role, {"name": "Tenant Manager", "slug": "tenant-manager"}),
        }
        permissions = {
            "create-post": _ensure_model(Permission, {"name": "Create Posts", "slug": "create-post"}),
            "delete-post": _ensure_model(Permission, {"name": "Delete Posts", "slug": "delete-post"}),
            "manage-users": _ensure_model(Permission, {"name": "Manage Users", "slug": "manage-users"}),
            "publish-post": _ensure_model(Permission, {"name": "Publish Posts", "slug": "publish-post"}),
        }
        grants = {
            "admin": ("create-post", "delete-post", "manage-users", "publish-post"),
            "user": ("create-post", "delete-post"),
            "tenant-manager": ("create-post", "delete-post", "manage-users"),
        }
        for role_slug, permission_slugs in grants.items():
            for permission_slug in permission_slugs:
                _ensure_pivot("permission_role", {
                    "role_id": _id(roles[role_slug]), "permission_id": _id(permissions[permission_slug]),
                })

        accounts = {
            "admin@craft.local": "admin",
            "user@craft.local": "user",
            "tenant@craft.local": "tenant-manager",
        }
        for email, role_slug in accounts.items():
            user = User.query().where("email", email).first()
            if user is not None:
                _ensure_pivot("role_user", {"user_id": _id(user), "role_id": _id(roles[role_slug])})

        group = _ensure_model(Group, {
            "name": "Content Team", "slug": "content-team",
            "description": "Writers and editors. Members inherit the `user` role.",
        })
        _ensure_pivot("group_role", {"group_id": _id(group), "role_id": _id(roles["user"])})
        demo_user = User.query().where("email", "user@craft.local").first()
        if demo_user is not None:
            _ensure_pivot("group_user", {"user_id": _id(demo_user), "group_id": _id(group)})
        _ensure_pivot("permission_group", {
            "group_id": _id(group), "permission_id": _id(permissions["publish-post"]),
            "conditions": dump({"user_id": "@user.id"}),
        })
