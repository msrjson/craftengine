"""Web routes for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Route

from app.Http.Controllers.Admin.CrudBuilderController import CrudBuilderController
from app.Http.Controllers.Admin.GroupController import GroupController
from app.Http.Controllers.Admin.HomeController import HomeController
from app.Http.Controllers.Admin.RoleController import PermissionController, RoleController
from app.Http.Controllers.Auth.AuthController import AuthController
from app.Http.Controllers.Docs.DocsController import DocsController
from app.Http.Controllers.Panel.PanelController import PanelController

# Home & Dashboard Routes
Route.get("/", [HomeController, "index"]).name("home")
Route.get("/home", [HomeController, "index"]).name("home.index")
Route.get("/dashboard", [HomeController, "index"]).name("dashboard")

# Authentication - login/register are throttled per IP+route to close the
# brute-force gap: the CAPTCHA on /login stops naive scripted attempts, but
# does not bound automated ones without a request-rate limit.
Route.get("/login", [AuthController, "show_login"]).name("login")
Route.post("/login", [AuthController, "login"]).middleware("throttle").name("login.attempt")
Route.get("/register", [AuthController, "show_register"]).name("register")
Route.post("/register", [AuthController, "register"]).middleware("throttle").name("register.store")
Route.post("/logout", [AuthController, "logout"]).name("logout")

# The dashboard lists every user, every administrator and every tenant in the
# installation. It carried `auth` alone, so any account that could log in read
# the whole directory - authentication is not authorization. `role:admin` puts
# it on the same footing as the rest of the admin surface, and
# `tests/test_admin_authorization.py` now fails the build if any /admin route
# is ever declared without an authorizing alias again.
Route.get("/admin", [HomeController, "admin"]).middleware("auth", "role:admin").name("admin.dashboard")

# The CRUD builder writes real `.py` files into app/ and database/migrations/
# and rewrites routes/api.py and routes/web.py. Behind `auth` alone that is
# remote code execution for any registered user, so it carries `role:admin`
# like the rest of the admin surface.
Route.get("/admin/crud-builder", [CrudBuilderController, "index"]).middleware("auth", "role:admin").name(
    "admin.crud_builder.index"
)
Route.post("/admin/crud-builder", [CrudBuilderController, "store"]).middleware("auth", "role:admin").name(
    "admin.crud_builder.store"
)

# RBAC admin UI - the first real usage of the `role:<slug>` route middleware.
Route.get("/admin/roles", [RoleController, "index"]).middleware("auth", "role:admin").name("admin.roles.index")
Route.post("/admin/roles/grant", [RoleController, "grant"]).middleware("auth", "role:admin").name("admin.roles.grant")
Route.get("/admin/permissions", [PermissionController, "index"]).middleware("auth", "role:admin").name(
    "admin.permissions.index"
)

# Group admin UI - team-level access, plus the conditional (ABAC) grants.
# Every one of these hands out access, so they are themselves admin-only.
Route.get("/admin/groups", [GroupController, "index"]).middleware("auth", "role:admin").name("admin.groups.index")
Route.post("/admin/groups", [GroupController, "store"]).middleware("auth", "role:admin").name("admin.groups.store")
Route.post("/admin/groups/members", [GroupController, "add_member"]).middleware("auth", "role:admin").name(
    "admin.groups.members"
)
Route.post("/admin/groups/roles", [GroupController, "grant_role"]).middleware("auth", "role:admin").name(
    "admin.groups.roles"
)
Route.post("/admin/groups/permissions", [GroupController, "grant_permission"]).middleware("auth", "role:admin").name(
    "admin.groups.permissions"
)

# The control panel - a workspace for EVERY signed-in account, not an admin
# area. `/panel` and the pages under it that only concern the visitor's own
# data need `auth` alone; the pages that manage other people carry
# `role:admin` as well. The sidebar is built from the `nav` registry and
# filtered by the very same guards, so an account never sees a link into a 403.
Route.get("/panel", [PanelController, "index"]).middleware("auth").name("panel.index")
Route.get("/panel/profile", [PanelController, "profile"]).middleware("auth").name("panel.profile")
Route.post("/panel/profile", [PanelController, "update_profile"]).middleware("auth").name("panel.profile.update")
Route.post("/panel/profile/password", [PanelController, "update_password"]).middleware("auth").name(
    "panel.profile.password"
)

# The access audit exposes permission slugs, the path each grant arrives by and
# the raw ABAC conditions - the installation's security configuration, not the
# visitor's personal data. It shipped open to any signed-in account for one
# revision; it is admin-only now.
Route.get("/panel/access", [PanelController, "access"]).middleware("auth", "role:admin").name("panel.access")
Route.get("/panel/users", [PanelController, "users"]).middleware("auth", "role:admin").name("panel.users")
Route.post("/panel/users", [PanelController, "store_user"]).middleware("auth", "role:admin").name("panel.users.store")
Route.post("/panel/users/roles/assign", [PanelController, "assign_role"]).middleware("auth", "role:admin").name(
    "panel.users.roles.assign"
)
Route.post("/panel/users/roles/revoke", [PanelController, "revoke_role"]).middleware("auth", "role:admin").name(
    "panel.users.roles.revoke"
)
Route.post("/panel/users/groups/assign", [PanelController, "assign_group"]).middleware("auth", "role:admin").name(
    "panel.users.groups.assign"
)
Route.post("/panel/users/groups/revoke", [PanelController, "revoke_group"]).middleware("auth", "role:admin").name(
    "panel.users.groups.revoke"
)
Route.get("/panel/modules", [PanelController, "modules"]).middleware("auth", "role:admin").name("panel.modules")
Route.post("/panel/modules/toggle", [PanelController, "toggle_module"]).middleware("auth", "role:admin").name(
    "panel.modules.toggle"
)
Route.get("/panel/plugins", [PanelController, "plugins"]).middleware("auth", "role:admin").name("panel.plugins")
Route.get("/panel/tenants", [PanelController, "tenants"]).middleware("auth", "role:admin").name("panel.tenants")

# Framework control. These answer "what is this installation actually doing?"
# from the running application - the live router, the live connection, the live
# managers - so an administrator never has to shell into the container to find
# out. `/panel/routes` in particular is the installation's attack surface in
# one table.
Route.get("/panel/routes", [PanelController, "routes"]).middleware("auth", "role:admin").name("panel.routes")
Route.get("/panel/database", [PanelController, "database"]).middleware("auth", "role:admin").name("panel.database")
Route.get("/panel/cache", [PanelController, "cache"]).middleware("auth", "role:admin").name("panel.cache")
Route.post("/panel/cache/flush", [PanelController, "flush_cache"]).middleware("auth", "role:admin").name(
    "panel.cache.flush"
)
Route.get("/panel/queue", [PanelController, "queue"]).middleware("auth", "role:admin").name("panel.queue")
Route.get("/panel/schedule", [PanelController, "schedule"]).middleware("auth", "role:admin").name("panel.schedule")
Route.get("/panel/logs", [PanelController, "logs"]).middleware("auth", "role:admin").name("panel.logs")
Route.get("/panel/system", [PanelController, "system"]).middleware("auth", "role:admin").name("panel.system")

# Documentation Routes
Route.get("/docs", [DocsController, "index"]).name("docs.index")
Route.get("/docs/{page}", [DocsController, "show"]).name("docs.show")
