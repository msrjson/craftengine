"""Role Model for Craft Framework RBAC."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.orm.model import Model


class Role(Model):
    __table__ = "roles"
    fillable = ["name", "slug"]

    def permissions(self):
        """Permissions granted to this role, through the `permission_role`
        pivot.

        Previously defined on the framework's base `Model`, where every model
        inherited it and answered with the permissions of the *role* sharing
        its id.
        """
        from craft.orm.relationships import BelongsToMany
        from app.Models.Permission import Permission

        return BelongsToMany(
            self,
            Permission,
            pivot_table="permission_role",
            foreign_pivot_key="role_id",
            related_pivot_key="permission_id",
            name="permissions",
        )
