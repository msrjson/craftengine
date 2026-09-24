"""Identity models owned by the test-suite.

These are the tests' own subjects. They map onto the same tables the engine's
migrations create, and they are what `config/auth.py` is pointed at while the
suite runs (see the `identity_models` fixture in `tests/conftest.py`), so no
test depends on the demo application under `app/` being present.

The behaviour mirrors what a project is expected to write for itself:
authorization questions are delegated to the container's `AccessResolver`
rather than re-implemented, and passwords are hashed on every insert path.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from craft.auth.password import Hash
from craft.orm.model import Model
from craft.orm.relationships import BelongsToMany


class Permission(Model):
    """A single ability, identified by its slug."""

    __table__ = "permissions"
    fillable = ["name", "slug"]


class Role(Model):
    """A named bundle of permissions."""

    __table__ = "roles"
    fillable = ["name", "slug"]

    def permissions(self) -> BelongsToMany:
        """Permissions granted to this role, through `permission_role`."""
        return BelongsToMany(
            self,
            Permission,
            pivot_table="permission_role",
            foreign_pivot_key="role_id",
            related_pivot_key="permission_id",
            name="permissions",
        )


class Group(Model):
    """A team that carries roles and permissions for all of its members."""

    __table__ = "groups"
    fillable = ["name", "slug", "description"]

    def users(self) -> BelongsToMany:
        """Members of this group, through `group_user`."""
        return BelongsToMany(
            self,
            User,
            pivot_table="group_user",
            foreign_pivot_key="group_id",
            related_pivot_key="user_id",
            name="users",
        )

    def roles(self) -> BelongsToMany:
        """Roles this group grants to every member, through `group_role`."""
        return BelongsToMany(
            self,
            Role,
            pivot_table="group_role",
            foreign_pivot_key="group_id",
            related_pivot_key="role_id",
            name="roles",
        )

    def permissions(self) -> BelongsToMany:
        """Permissions granted straight to the group, through `permission_group`."""
        return BelongsToMany(
            self,
            Permission,
            pivot_table="permission_group",
            foreign_pivot_key="group_id",
            related_pivot_key="permission_id",
            name="permissions",
        )


class User(Model):
    """The account the suite authenticates, authorizes and scopes by tenant."""

    __table__ = "users"

    #: `is_admin`, `type` and `api_token` gate authorization and must never be
    #: mass-assignable from request input — only through `force_create`.
    fillable = ["name", "email", "password"]
    hidden = ["password", "remember_token"]

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> "User":
        """Insert without the mass-assignment guard, hashing the password.

        Args:
            attributes: Column values, trusted by the caller.

        Returns:
            The persisted user.
        """
        attributes = dict(attributes)
        password = attributes.get("password")
        if password and not Hash.is_hashed(password):
            attributes["password"] = Hash.make(password)
        return super().force_create(attributes)

    def check_password(self, password: str) -> bool:
        """Whether the plaintext password matches the stored hash."""
        return Hash.check(password, self.get_attribute("password"))

    def _access(self) -> Optional[Any]:
        """The container's AccessResolver, or None outside a booted app."""
        from craft.container.application import Container

        try:
            return Container.getInstance().make("access")
        except Exception:
            return None

    def groups(self) -> BelongsToMany:
        """Groups this user belongs to, through `group_user`."""
        return BelongsToMany(
            self,
            Group,
            pivot_table="group_user",
            foreign_pivot_key="user_id",
            related_pivot_key="group_id",
            name="groups",
        )

    def roles(self) -> BelongsToMany:
        """Roles assigned to this user, through `role_user`."""
        return BelongsToMany(
            self,
            Role,
            pivot_table="role_user",
            foreign_pivot_key="user_id",
            related_pivot_key="role_id",
            name="roles",
        )

    def in_group(self, slug: str) -> bool:
        """Whether the user is a member of the group."""
        access = self._access()
        return False if access is None else access.in_group(self, slug)

    def can(self, slug: str, resource: Any = None) -> bool:
        """Whether the user may do `slug`, optionally against a resource."""
        access = self._access()
        return False if access is None else access.allows(self, slug, resource)

    def permission_slugs(self) -> List[str]:
        """Every permission slug reachable by this user."""
        access = self._access()
        return access.permissions(self) if access is not None else []

    def has_role(self, slug: str) -> bool:
        """Whether the user holds the role, directly or through a group."""
        access = self._access()
        return False if access is None else access.has_role(self, slug)

    def has_permission(self, slug: str) -> bool:
        """Whether the user holds the permission unconditionally."""
        access = self._access()
        return False if access is None else access.has_permission(self, slug)


class Media(Model):
    """A stored file and its generated conversions."""

    __table__ = "media"

    fillable = [
        "model_type",
        "model_id",
        "collection_name",
        "disk",
        "filename",
        "mime_type",
        "size",
        "width",
        "height",
        "conversions",
    ]

    def get_conversions(self) -> Dict[str, Any]:
        """Return the conversions map, parsing it when stored as JSON text."""
        value = getattr(self, "conversions", None)
        if isinstance(value, dict):
            return value
        if value and isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return {}
        return {}

    def set_conversions(self, conversions: Dict[str, Any]) -> None:
        """Serialize the conversions map for storage."""
        self.conversions = json.dumps(conversions)


class SystemLog(Model):
    """A request-level log line written to the database."""

    __table__ = "system_logs"

    fillable = ["level", "message", "context"]

    #: `level` is NOT NULL in the schema — default it so plain messages work.
    defaults = {"level": "info"}
