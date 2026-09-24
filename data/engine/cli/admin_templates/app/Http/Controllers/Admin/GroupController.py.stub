"""GroupController — admin UI for group-level access.

Category: Application (Admin Controllers).
Relations:
  - Reads/writes `app/Models/Group.py` and its `users()`/`roles()`/
    `permissions()` relations; membership and grants live in the `group_user`,
    `group_role` and `permission_group` pivots created by
    `database/migrations/2026_08_11_000001_create_groups_and_abac_tables.py`.
  - Routes registered in `routes/web.py`, guarded by `auth` + `role:admin` —
    this screen hands out access, so reaching it must itself be authorized.
  - Decisions are never re-implemented here: what a member ends up being
    allowed to do is resolved by `craft.auth.access.AccessResolver`.
References:
  - Guide: `documentation/authorization.md`

A group grants access to a team rather than to one person at a time. It holds
roles and/or permissions, and every member inherits them, so onboarding is a
single membership row instead of a tour of every role that team needs.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from app.Http.Controllers.Panel.PanelPage import PanelPage
from craft.facades import DB
from craft.http.controller import Controller
from craft.http.response import redirect


class GroupController(PanelPage, Controller):
    """Lists groups and lets an administrator wire membership and grants."""

    def index(self, request):
        """Every group with its members, roles and directly granted permissions.

        Conditions attached to a grant are shown verbatim rather than
        summarised: "publish-post, only where user_id matches" is the sort of
        detail that must not be rounded off on the screen people audit.
        """
        from app.Models.Group import Group
        from app.Models.Permission import Permission
        from app.Models.Role import Role
        from app.Models.User import User

        groups = Group.query().get()

        members = {}
        roles_of = {}
        permissions_of = {}
        for group in groups:
            group_id = group.get_attribute("id")
            members[group_id] = group.users().get()
            roles_of[group_id] = group.roles().get()
            permissions_of[group_id] = self._granted_permissions(group_id)

        return self.panel(request, "admin.groups.index", {
            "heading": "Groups",
            "subheading": "Team-level access. Members inherit every role and permission the group carries.",
            "groups": groups,
            "members": members,
            "roles_of": roles_of,
            "permissions_of": permissions_of,
            "roles": Role.query().get(),
            "permissions": Permission.query().get(),
            "users": User.query().order_by("name").get(),
        })

    @staticmethod
    def _granted_permissions(group_id):
        """Permissions granted straight to a group, with their conditions.

        A join rather than the relation, because the relation returns the
        permissions and drops the `conditions` column carried by the pivot —
        which is exactly the part an administrator needs to see.
        """
        rows = DB.statement(
            """
            SELECT p.slug AS slug, pg.conditions AS conditions
              FROM permissions p
              JOIN permission_group pg ON pg.permission_id = p.id
             WHERE pg.group_id = ?
             ORDER BY p.slug
            """,
            [group_id],
            read=True,
        ).fetchall()
        return [{"slug": row["slug"], "conditions": row["conditions"]} for row in rows]

    def store(self, request):
        """Create a group. Slug is what the `group:<slug>` middleware matches."""
        from app.Models.Group import Group

        name = (request.post("name") or "").strip()
        slug = (request.post("slug") or "").strip()
        if name and slug:
            Group.create({
                "name": name,
                "slug": slug,
                "description": (request.post("description") or "").strip() or None,
            })

        return redirect(url="/admin/groups", status=302)

    def add_member(self, request):
        """Add a user to a group."""
        return self._link(
            request,
            table="group_user",
            left=("user_id", request.post("user_id")),
            right=("group_id", request.post("group_id")),
        )

    def grant_role(self, request):
        """Grant a role to every member of a group."""
        return self._link(
            request,
            table="group_role",
            left=("group_id", request.post("group_id")),
            right=("role_id", request.post("role_id")),
        )

    def grant_permission(self, request):
        """Grant one permission to a group, optionally narrowed by conditions."""
        from craft.auth.conditions import ConditionError, dump, parse

        raw = (request.post("conditions") or "").strip()
        try:
            conditions = dump(parse(raw)) if raw else None
        except ConditionError:
            # Refuse rather than store: an unreadable condition denies at check
            # time, so accepting it would create a grant that never works and
            # looks like it should.
            return redirect(url="/admin/groups?error=conditions", status=302)

        return self._link(
            request,
            table="permission_group",
            left=("group_id", request.post("group_id")),
            right=("permission_id", request.post("permission_id")),
            extra={"conditions": conditions},
        )

    @staticmethod
    def _link(request, table, left, right, extra=None):
        """Insert a pivot row once, ignoring a repeat of the same pair."""
        left_column, left_value = left
        right_column, right_value = right
        if not left_value or not right_value:
            return redirect(url="/admin/groups", status=302)

        already = DB.statement(
            f"SELECT 1 FROM {table} WHERE {left_column} = ? AND {right_column} = ?",
            [left_value, right_value],
            read=True,
        ).fetchone()
        if not already:
            columns = {left_column: left_value, right_column: right_value}
            columns.update(extra or {})
            names = ", ".join(columns)
            placeholders = ", ".join(f":{name}" for name in columns)
            DB.statement(f"INSERT INTO {table} ({names}) VALUES ({placeholders})", columns)

        return redirect(url="/admin/groups", status=302)
