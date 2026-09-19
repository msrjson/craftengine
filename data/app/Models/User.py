"""User Model for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any, Dict

from craft.auth.password import Hash
from craft.orm.model import Model


class User(Model):
    __table__ = "users"

    # `is_admin` and `type` gate authorization (PostPolicy, TenantMiddleware)
    # and must never be settable via mass assignment from request input —
    # only through a trusted, explicit path (e.g. Model.force_create /
    # direct set_attribute in an admin-only action).
    fillable = ["name", "email", "password"]
    hidden = ["password", "remember_token"]

    @classmethod
    def force_create(cls, attributes: Dict[str, Any]) -> "User":
        """Hash the password on the way in — never store plaintext.

        Hooked on `force_create` rather than `create` so that *every* insert
        path hashes: `create()` funnels through here after mass-assignment
        filtering, and trusted callers that bypass the guard (seeders, admin
        actions setting `type`/`is_admin`) get the same guarantee.
        """
        attributes = dict(attributes)
        password = attributes.get("password")
        if password and not Hash.is_hashed(password):
            attributes["password"] = Hash.make(password)
        return super().force_create(attributes)

    def check_password(self, password: str) -> bool:
        return Hash.check(password, self.get_attribute("password"))

    # -- Authorization -----------------------------------------------------

    # The relations below are for reading and managing membership. The actual
    # decisions — `has_role`, `has_permission`, `can` — are delegated to the
    # framework's `AccessResolver` (`craft.auth.access`), because a permission
    # can reach a user by four different paths:
    #
    #     user → permission                (direct grant)
    #     user → role → permission
    #     user → group → role → permission
    #     user → group → permission
    #
    # Every caller that re-implements "check the role table" gets at least one
    # of those wrong. One resolver, one answer.
    #
    # These used to sit on the framework's base `Model`, so every model in the
    # application answered `roles()` with the roles of the *user* holding the
    # same id. They belong to the model they actually describe.

    def _access(self):
        """The container's AccessResolver, or None outside a booted app.

        Models are used in unit tests with no application booted, so this has
        to degrade — and it degrades to *denial*, never to a grant.
        """
        from craft.container.application import Container

        try:
            return Container.getInstance().make("access")
        except Exception:
            return None

    def groups(self):
        """Groups this user belongs to, through the `group_user` pivot."""
        from craft.orm.relationships import BelongsToMany

        from app.Models.Group import Group

        return BelongsToMany(
            self,
            Group,
            pivot_table="group_user",
            foreign_pivot_key="user_id",
            related_pivot_key="group_id",
            name="groups",
        )

    def in_group(self, slug: str) -> bool:
        """Whether the user is a member of the group."""
        access = self._access()
        if access is None:
            return False
        return access.in_group(self, slug)

    def can(self, slug: str, resource=None) -> bool:
        """Whether the user may do `slug`, optionally to a specific resource.

        This is the method to reach for when there *is* a resource: a grant
        narrowed by attribute conditions ("only your own articles", "only under
        10k") is evaluated against it here. `has_permission()` deliberately
        answers only for unconditional grants, because without a resource a
        conditional grant has not answered the question.
        """
        access = self._access()
        if access is None:
            return False
        return access.allows(self, slug, resource)

    def permission_slugs(self) -> list:
        """Every permission slug reachable by this user — for display and audit."""
        access = self._access()
        return access.permissions(self) if access is not None else []

    def roles(self):
        """Roles assigned to this user, through the `role_user` pivot."""
        from craft.orm.relationships import BelongsToMany

        from app.Models.Role import Role

        return BelongsToMany(
            self,
            Role,
            pivot_table="role_user",
            foreign_pivot_key="user_id",
            related_pivot_key="role_id",
            name="roles",
        )

    def has_role(self, slug: str) -> bool:
        """Whether the user holds the role — directly, or through a group.

        This used to query `role_user` alone, so a role granted to the user's
        group was invisible: membership looked correct in the admin UI and the
        route middleware still refused.
        """
        access = self._access()
        if access is None:
            return False
        return access.has_role(self, slug)

    def has_permission(self, slug: str) -> bool:
        """Whether the user holds the permission **unconditionally**.

        Covers all four grant paths (direct, role, group→role, group). Grants
        carrying attribute conditions are deliberately excluded: this method is
        asked without a resource, and a grant that says *only your own* has not
        answered "may they edit articles?". Use `can(slug, resource)` when
        there is a resource to check against.
        """
        access = self._access()
        if access is None:
            return False
        return access.has_permission(self, slug)
