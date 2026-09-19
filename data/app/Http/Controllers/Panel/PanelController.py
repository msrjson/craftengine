"""The control panel — a workspace for every signed-in account.

Category: Application (Panel Controllers).
Relations:
  - Routes in `routes/web.py` under `/panel`, all behind `auth`; the sections
    that manage other people additionally require `role:admin`.
  - Renders `resources/views/panel/*` inside `layouts/panel.forge.py`.
  - The sidebar comes from the `nav` registry
    (`engine/support/navigation.py`), declared in
    `app/Providers/PanelServiceProvider.py` and filtered per visitor.
References:
  - Guide: `documentation/authorization.md`

Design note. The panel is deliberately **not** an admin-only area. An ordinary
account gets a real workspace — their posts, their profile, and an honest
account of the access they hold — and an administrator sees the same shell with
more sections in it. Building two parallel panels is how the two drift apart;
one shell whose menu is filtered means an ordinary user cannot even see, let
alone click, what they may not have.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB, Auth, Hash
from craft.http.controller import Controller
from craft.http.response import redirect

from app.Http.Controllers.Panel.PanelPage import PanelPage


class PanelController(PanelPage, Controller):
    """Every page of the panel. Each action ends in `self.panel(...)`."""

    # -- workspace -------------------------------------------------------------

    def index(self, request):
        """Dashboard — the visitor's own workspace.

        What an ordinary account sees here is strictly its own: what it wrote,
        and when it joined. It does **not** see roles, groups, permission counts
        or anything else describing how access is configured. That is the
        installation's security configuration, not the visitor's personal data:
        knowing which roles exist and which of them you hold is a map for
        probing the system, and it belongs to whoever administers it.

        Administrators additionally get the installation-wide figures — the
        size of the system is itself information an account that cannot see its
        contents should not be handed.
        """
        user = Auth.user()

        stats = [
            {"label": "Account status", "value": "Active", "hint": "Authenticated user"},
            {"label": "Member since", "value": self._joined(user), "hint": "Your account"},
        ]

        admin_stats = []
        if self.is_admin(user):
            from app.Models.Group import Group
            from app.Models.User import User

            admin_stats = [
                {"label": "Users", "value": User.query().count(), "hint": "Accounts in this installation"},
                {"label": "Groups", "value": Group.query().count(), "hint": "Teams with shared access"},
                {"label": "Modules", "value": len(self._modules()), "hint": "Feature areas"},
            ]

        return self.panel(
            request,
            "panel.index",
            {
                "heading": f"Welcome back, {user.get_attribute('name')}",
                "subheading": "Your workspace in this installation.",
                "stats": stats,
                "admin_stats": admin_stats,
            },
        )

    @staticmethod
    def _joined(user) -> str:
        """Just the date part of `created_at` — a timestamp is not a fact
        anybody reads off a dashboard."""
        value = user.get_attribute("created_at")
        return str(value).split("T")[0].split(" ")[0] if value else "—"

    def profile(self, request):
        """The account's own details — and nothing about how access is wired.

        The security-shaped rows (whether the account is an administrator, its
        internal `type`) are shown to administrators only. To an ordinary user
        this page is their name, their email and when they joined: their data,
        not the installation's configuration.
        """
        user = Auth.user()
        return self.panel(
            request,
            "panel.profile",
            {
                "heading": "My profile",
                "subheading": "Your account in this installation.",
                "user": user,
                "is_admin": self.is_admin(user),
            },
        )

    def update_profile(self, request):
        """Update authenticated user profile information."""
        from app.Services.Identity.DomainValidator import DomainValidator

        user = Auth.user()
        if not user:
            return redirect(url="/login", status=302)

        name = (request.post("name") or "").strip()
        email = (request.post("email") or "").strip().lower()

        if not name or len(name) < 2:
            return redirect(url="/panel/profile?error=invalid_name", status=302)

        if not DomainValidator.is_allowed_email(email, allow_system_domains=True):
            return redirect(url="/panel/profile?error=invalid_email", status=302)

        existing = DB.statement(
            "SELECT id FROM users WHERE email = ? AND id != ?",
            [email, user.get_attribute("id")],
            read=True,
        ).fetchone()
        if existing:
            return redirect(url="/panel/profile?error=email_taken", status=302)

        user.set_attribute("name", name)
        user.set_attribute("email", email)
        user.save()

        return redirect(url="/panel/profile?success=profile_updated", status=302)

    def update_password(self, request):
        """Rotate authenticated user password."""
        user = Auth.user()
        if not user:
            return redirect(url="/login", status=302)

        current_password = request.post("current_password") or ""
        new_password = request.post("new_password") or ""
        new_password_confirmation = request.post("new_password_confirmation") or ""

        if not user.check_password(current_password):
            return redirect(url="/panel/profile?error=invalid_current_password", status=302)

        if len(new_password) < 8:
            return redirect(url="/panel/profile?error=password_too_short", status=302)

        if new_password != new_password_confirmation:
            return redirect(url="/panel/profile?error=password_mismatch", status=302)

        user.set_attribute("password", Hash.make(new_password))
        user.save()

        return redirect(url="/panel/profile?success=password_updated", status=302)

    def access(self, request):
        """Access audit — **administrators only** (`role:admin` on the route).

        Shows every permission in play, the path each grant arrives by
        (direct, role, group→role, group) and the conditions attached to it,
        straight from the resolver that makes the decision.

        This started life as a "My access" page for every visitor and was moved
        behind the admin guard: permission slugs, grant paths and raw ABAC
        conditions describe how the installation is secured. Telling an
        ordinary account that `delete-post` reaches it via `group-role` under
        such-and-such condition hands over a map for probing the system, and it
        answers a question only whoever administers access needs to ask.
        """
        user = Auth.user()
        access = self.app_access()

        grants = []
        for slug in access.permissions(user):
            for grant in access.explain(user, slug):
                grants.append(
                    {
                        "slug": slug,
                        "source": grant["source"],
                        "conditions": grant["conditions"],
                    }
                )

        return self.panel(
            request,
            "panel.access",
            {
                "heading": "Access audit",
                "subheading": "How this account's permissions are configured.",
                "roles": access.roles(user),
                "groups": access.groups(user),
                "grants": grants,
            },
        )

    # -- administration --------------------------------------------------------

    def users(self, request):
        """The account directory and RBAC assignment. Admin-only."""
        from app.Models.Group import Group
        from app.Models.Role import Role
        from app.Models.User import User

        access = self.app_access()
        users = User.query().order_by_desc("created_at").limit(100).get()

        rows = [
            {
                "user": user,
                "roles": [r["slug"] if isinstance(r, dict) else r for r in access.roles(user)],
                "groups": [g["slug"] if isinstance(g, dict) else g for g in access.groups(user)],
            }
            for user in users
        ]

        roles = Role.query().order_by("name").get()
        groups = Group.query().order_by("name").get()

        return self.panel(
            request,
            "panel.users",
            {
                "heading": "Users",
                "subheading": f"{len(rows)} accounts.",
                "rows": rows,
                "roles": roles,
                "groups": groups,
            },
        )

    def store_user(self, request):
        """Provision a new user account with initial role and group."""
        from app.Models.User import User

        name = (request.post("name") or "").strip()
        email = (request.post("email") or "").strip().lower()
        password = request.post("password") or ""
        is_admin = request.post("is_admin") in ("1", "true", "True", True)
        role_id = request.post("role_id")
        group_id = request.post("group_id")

        if not name or not email or not password:
            return redirect(url="/panel/users?error=missing_fields", status=302)

        existing = DB.statement("SELECT id FROM users WHERE email = ?", [email], read=True).fetchone()
        if existing:
            return redirect(url="/panel/users?error=email_taken", status=302)

        user = User.force_create(
            {
                "name": name,
                "email": email,
                "password": password,
                "is_admin": is_admin,
            }
        )

        if role_id:
            DB.statement(
                "INSERT INTO role_user (user_id, role_id) VALUES (?, ?)",
                [user.get_attribute("id"), int(role_id)],
            )
        if group_id:
            DB.statement(
                "INSERT INTO group_user (user_id, group_id) VALUES (?, ?)",
                [user.get_attribute("id"), int(group_id)],
            )

        return redirect(url="/panel/users?success=user_created", status=302)

    def assign_role(self, request):
        """Assign a role to a user."""
        user_id = request.post("user_id")
        role_id = request.post("role_id")
        if user_id and role_id:
            already = DB.statement(
                "SELECT 1 FROM role_user WHERE user_id = ? AND role_id = ?",
                [user_id, role_id],
                read=True,
            ).fetchone()
            if not already:
                DB.statement("INSERT INTO role_user (user_id, role_id) VALUES (?, ?)", [user_id, role_id])
        return redirect(url="/panel/users?success=role_assigned", status=302)

    def revoke_role(self, request):
        """Revoke a role from a user."""
        user_id = request.post("user_id")
        role_id = request.post("role_id")
        if user_id and role_id:
            DB.statement("DELETE FROM role_user WHERE user_id = ? AND role_id = ?", [user_id, role_id])
        return redirect(url="/panel/users?success=role_revoked", status=302)

    def assign_group(self, request):
        """Assign a group to a user."""
        user_id = request.post("user_id")
        group_id = request.post("group_id")
        if user_id and group_id:
            already = DB.statement(
                "SELECT 1 FROM group_user WHERE user_id = ? AND group_id = ?",
                [user_id, group_id],
                read=True,
            ).fetchone()
            if not already:
                DB.statement("INSERT INTO group_user (user_id, group_id) VALUES (?, ?)", [user_id, group_id])
        return redirect(url="/panel/users?success=group_assigned", status=302)

    def revoke_group(self, request):
        """Revoke a group from a user."""
        user_id = request.post("user_id")
        group_id = request.post("group_id")
        if user_id and group_id:
            DB.statement("DELETE FROM group_user WHERE user_id = ? AND group_id = ?", [user_id, group_id])
        return redirect(url="/panel/users?success=group_revoked", status=302)

    def modules(self, request):
        """Feature modules, with their live enabled state."""
        return self.panel(
            request,
            "panel.modules",
            {
                "heading": "Modules",
                "subheading": "Feature areas. A disabled module makes its routes 404 without a deploy.",
                "modules": self._modules(),
            },
        )

    def toggle_module(self, request):
        """Enable or disable a module, then return to the list."""
        slug = request.post("slug")
        enable = request.post("enable") == "1"
        if slug:
            manager = self.container().make("module")
            manager.enable(slug) if enable else manager.disable(slug)
        return redirect(url="/panel/modules", status=302)

    def plugins(self, request):
        """Installed plugins, discovered from `plugins/<slug>/plugin.py`."""
        manager = self.container().make("plugin")
        try:
            installed = manager.installed()
        except Exception:
            installed = []
        return self.panel(
            request,
            "panel.plugins",
            {
                "heading": "Plugins",
                "subheading": "Discovered from plugins/<slug>/plugin.py.",
                "plugins": installed,
            },
        )

    def system(self, request):
        """What this installation actually is: versions, driver, counts."""
        import platform
        import sys

        db = self.container().make("db")
        config = self.container().make("config")

        # Counted per dialect, the same way `dev.py db tables` does it — there
        # is no cross-driver table listing helper to lean on.
        listings = {
            "sqlite": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
            "postgresql": "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()",
        }
        sql = listings.get(
            db.driver,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()",
        )
        try:
            table_count = len(db.statement(sql, read=True).fetchall())
        except Exception:
            # An unavailable count is reported as unavailable, never as zero:
            # "0 tables" and "could not ask" look identical and mean opposites.
            table_count = None

        facts = [
            ("Craft version", f"{config.get('app.version')} {config.get('app.release')}"),
            ("Environment", config.get("app.APP_ENV", "local")),
            ("Debug", "on" if config.get("app.APP_DEBUG", False) else "off"),
            ("Python", sys.version.split()[0]),
            ("Platform", platform.platform()),
            ("Database driver", db.driver),
            ("Tables", table_count if table_count is not None else "unavailable"),
            ("Locale", config.get("app.APP_LOCALE", "en")),
        ]

        return self.panel(
            request,
            "panel.system",
            {
                "heading": "About this install",
                "subheading": "Read from the running application, not from a config file.",
                "facts": facts,
            },
        )

    # -- framework control -----------------------------------------------------
    # These pages exist so an administrator can answer "what is this
    # installation actually doing?" without shelling into the container. Every
    # figure is read from the running application — the live router, the live
    # connection, the live managers — never from a config file that may not be
    # the one in effect.

    def routes(self, request):
        """Every registered route, with the middleware that guards it.

        The single most useful screen for auditing an installation: the route
        table *is* the attack surface, and reading it here beats grepping
        `routes/` and hoping nothing registers routes at runtime (the CRUD
        builder does).
        """
        router = self.container().make("router")

        rows = []
        for route in router.routes:
            declared = [m if isinstance(m, str) else getattr(m, "__name__", str(m)) for m in route.middleware_list]
            rows.append(
                {
                    "methods": ", ".join(route.methods),
                    "uri": route.uri,
                    "name": route._name or "—",
                    "middleware": declared,
                    "module": route._module or "",
                    # An unguarded write route is worth seeing at a glance.
                    "guarded": any(
                        isinstance(m, str) and m.startswith(("auth", "role:", "permission:", "group:", "api"))
                        for m in route.middleware_list
                    ),
                }
            )
        rows.sort(key=lambda r: r["uri"])

        return self.panel(
            request,
            "panel.routes",
            {
                "heading": "Routes",
                "subheading": f"{len(rows)} routes registered in this process.",
                "rows": rows,
            },
        )

    def database(self, request):
        """Driver, connection pool and every table with its row count."""
        db = self.container().make("db")

        listings = {
            "sqlite": "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name",
            "postgresql": "SELECT tablename AS name FROM pg_tables WHERE schemaname = current_schema() ORDER BY tablename",
        }
        sql = listings.get(
            db.driver,
            "SELECT table_name AS name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() ORDER BY table_name",
        )

        tables = []
        try:
            for row in db.statement(sql, read=True).fetchall():
                name = row["name"]
                try:
                    count = db.statement(f'SELECT COUNT(*) AS n FROM "{name}"', read=True).fetchone()["n"]
                except Exception:
                    # A table the current role cannot read is reported as such,
                    # not as zero rows.
                    count = None
                tables.append({"name": name, "rows": count})
        except Exception:
            tables = []

        try:
            pool = db.write_connection.pool_stats
        except Exception:
            pool = {"open": 0, "idle": 0}

        return self.panel(
            request,
            "panel.database",
            {
                "heading": "Database",
                "subheading": f"{db.driver} — {len(tables)} tables.",
                "driver": db.driver,
                "pool": pool,
                "pool_size": getattr(db.write_connection, "pool_size", "?"),
                "tables": tables,
            },
        )

    def cache(self, request):
        """Which cache store is in effect, and a way to empty it."""
        config = self.container().make("config")
        # `store` is a property on the manager, not a method — the resolved
        # store object, whichever driver actually came up.
        store = self.container().make("cache").store

        return self.panel(
            request,
            "panel.cache",
            {
                "heading": "Cache",
                "subheading": "The store actually in use, resolved at runtime.",
                "configured": config.get("cache.default", "array"),
                "store": type(store).__name__,
                "flushed": request.input("flushed") == "1",
            },
        )

    def flush_cache(self, request):
        """Empty the cache. POST + CSRF: a GET that mutates can be prefetched."""
        try:
            self.container().make("cache").flush()
        except Exception:
            return redirect(url="/panel/cache", status=302)
        return redirect(url="/panel/cache?flushed=1", status=302)

    def queue(self, request):
        """Pending and failed jobs, straight from the `jobs` table."""
        db = self.container().make("db")
        config = self.container().make("config")

        def count(sql, bindings=None):
            try:
                return db.statement(sql, bindings, read=True).fetchone()["n"]
            except Exception:
                # No jobs table yet (nothing queued in this installation).
                return None

        pending = count("SELECT COUNT(*) AS n FROM jobs")
        attempted = count("SELECT COUNT(*) AS n FROM jobs WHERE attempts > 0")

        recent = []
        try:
            rows = db.statement(
                "SELECT id, queue, attempts, available_at FROM jobs ORDER BY id DESC LIMIT 20",
                read=True,
            ).fetchall()
            recent = [
                {
                    "id": row["id"],
                    "queue": row["queue"],
                    "attempts": row["attempts"],
                    "available_at": row["available_at"],
                }
                for row in rows
            ]
        except Exception:
            recent = []

        return self.panel(
            request,
            "panel.queue",
            {
                "heading": "Queue",
                "subheading": "Jobs waiting to be processed by `dev.py queue work`.",
                "connection": config.get("queue.default", "sync"),
                "pending": pending,
                "attempted": attempted,
                "recent": recent,
            },
        )

    def logs(self, request):
        """The most recent entries the application wrote to the database."""
        db = self.container().make("db")

        entries = []
        try:
            rows = db.statement("SELECT * FROM system_logs ORDER BY id DESC LIMIT 100", read=True).fetchall()
            entries = [dict(row) for row in rows]
        except Exception:
            entries = []

        return self.panel(
            request,
            "panel.logs",
            {
                "heading": "Logs",
                "subheading": "The last 100 entries recorded in `system_logs`.",
                "entries": entries,
                "columns": list(entries[0].keys()) if entries else [],
            },
        )

    def schedule(self, request):
        """Registered scheduled tasks and when each one runs."""
        try:
            tasks = self.container().make("schedule").tasks()
        except Exception:
            tasks = []

        rows = [{"name": task.name(), "expression": task.expression()} for task in tasks]

        return self.panel(
            request,
            "panel.schedule",
            {
                "heading": "Scheduler",
                "subheading": "Run them with `dev.py schedule work`, or `schedule run` from cron.",
                "rows": rows,
            },
        )

    def tenants(self, request):
        """Tenants and the schema each one is isolated into."""
        from app.Services.Tenant.TenantService import TenantService

        try:
            tenants = TenantService().get_active_tenants()
        except Exception:
            tenants = []

        db = self.container().make("db")
        return self.panel(
            request,
            "panel.tenants",
            {
                "heading": "Tenants",
                "subheading": "Schema-per-tenant isolation requires PostgreSQL.",
                "tenants": tenants,
                "driver": db.driver,
                "isolated": db.driver == "postgresql",
            },
        )

    # -- helpers ---------------------------------------------------------------
    # `container()`, `app_access()` and `is_admin()` come from PanelPage.

    def _modules(self):
        """Every module with the state the router will actually honour."""
        try:
            manager = self.container().make("module")
            modules = manager.all()
        except Exception:
            return []

        result = []
        for module in modules:
            slug = module.get("slug")
            result.append(
                {
                    "slug": slug,
                    "name": module.get("name") or slug,
                    "enabled": bool(module.get("enabled")),
                }
            )
        return result
