"""Group model — access granted to a team rather than to one person at a time.

A group collects users and carries roles and/or permissions of its own.
Onboarding someone into "the support team" then becomes a single membership
row, instead of remembering every role that team happens to need; and revoking
it is one delete rather than an audit of five pivot tables.

Permissions reaching a user *through* a group are resolved by
`craft.auth.access.AccessResolver`, together with the direct and role-based
paths — see `documentation/authorization.md`. Nothing here re-implements that
check; these relations exist for reading and managing membership.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class Group(Model):
    __table__ = "groups"
    fillable = ["name", "slug", "description"]

    def users(self):
        """Members of this group, through the `group_user` pivot."""
        from app.Models.User import User
        from craft.orm.relationships import BelongsToMany

        return BelongsToMany(
            self,
            User,
            pivot_table="group_user",
            foreign_pivot_key="group_id",
            related_pivot_key="user_id",
            name="users",
        )

    def roles(self):
        """Roles this group grants to every member, through `group_role`."""
        from app.Models.Role import Role
        from craft.orm.relationships import BelongsToMany

        return BelongsToMany(
            self,
            Role,
            pivot_table="group_role",
            foreign_pivot_key="group_id",
            related_pivot_key="role_id",
            name="roles",
        )

    def permissions(self):
        """Permissions granted straight to the group, through `permission_group`.

        For the cases where inventing a role would be ceremony: one team needs
        one extra permission and nothing else.
        """
        from app.Models.Permission import Permission
        from craft.orm.relationships import BelongsToMany

        return BelongsToMany(
            self,
            Permission,
            pivot_table="permission_group",
            foreign_pivot_key="group_id",
            related_pivot_key="permission_id",
            name="permissions",
        )
