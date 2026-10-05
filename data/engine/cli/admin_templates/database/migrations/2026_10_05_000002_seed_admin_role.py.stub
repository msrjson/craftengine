"""Migration: the `admin` role the generated panel and its routes require.

`craft make:admin` protects every panel route with `role:admin` and tells the
developer to run `user assign-role <email> admin`; without this row that step
fails with "No such role" on every new project. The role is created only when
no role with that slug exists, so a project's own edits survive a re-run.

Forward-only: there is no `down()`; records are never deleted.

Category: Generated (RBAC).
"""

from datetime import datetime, timezone

from craft.facades import DB

#: The slug the panel's routes check (`role:admin`).
ADMIN_SLUG = "admin"


def up():
    if DB.table("roles").where("slug", ADMIN_SLUG).first() is not None:
        return
    now = datetime.now(timezone.utc).isoformat()
    DB.table("roles").insert({"name": ADMIN_SLUG, "slug": ADMIN_SLUG, "created_at": now, "updated_at": now})
