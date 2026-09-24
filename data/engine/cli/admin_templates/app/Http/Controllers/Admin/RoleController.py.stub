"""RoleController — Minimal admin UI for the RBAC system.

Category: Application (Admin Controllers).
Relations:
  - Reads/writes `app/Models/Role.py`, `app/Models/Permission.py` through the
    `roles()`/`permissions()` BelongsToMany relations on `engine/orm/model.py`.
  - Routes registered in `routes/web.py`, guarded by the `role:admin` route
    middleware (`engine/http/middleware.py`).
References:
  - Guide: `documentation/authorization.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from app.Http.Controllers.Panel.PanelPage import PanelPage
from craft.http.controller import Controller
from craft.http.response import redirect
from craft.facades import DB


class RoleController(PanelPage, Controller):
    def index(self, request):
        from app.Models.Role import Role

        roles = Role.query().get()
        role_permissions = {
            role.get_attribute("id"): role.permissions().get() for role in roles
        }

        from app.Models.Permission import Permission

        # Rendered inside the control panel shell rather than the marketing
        # layout: one panel, one sidebar, one set of guards.
        return self.panel(request, "admin.roles.index", {
            "heading": "Roles",
            "subheading": "Roles and the permissions granted to each.",
            "roles": roles,
            "role_permissions": role_permissions,
            "permissions": Permission.query().get(),
        })

    def grant(self, request):
        from app.Models.Role import Role
        from app.Models.Permission import Permission

        role_id = request.post("role_id")
        permission_id = request.post("permission_id")

        role = Role.find(role_id) if role_id else None
        permission = Permission.find(permission_id) if permission_id else None

        if role is not None and permission is not None:
            already = DB.statement(
                "SELECT 1 FROM permission_role WHERE role_id = ? AND permission_id = ?",
                [role.get_attribute("id"), permission.get_attribute("id")],
                read=True,
            ).fetchone()
            if not already:
                DB.statement(
                    "INSERT INTO permission_role (role_id, permission_id) VALUES (?, ?)",
                    [role.get_attribute("id"), permission.get_attribute("id")],
                )

        return redirect(url="/admin/roles", status=302)


class PermissionController(PanelPage, Controller):
    def index(self, request):
        from app.Models.Permission import Permission

        return self.panel(request, "admin.permissions.index", {
            "heading": "Permissions",
            "subheading": "Every permission this installation knows about.",
            "permissions": Permission.query().get(),
        })
