"""User seeder."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import DB
from craft.seeding import Seeder
from app.Models.User import User


class UserSeeder(Seeder):
    """Seeds the framework's 3 official demo accounts, and the tenant one of them belongs to.

    Uses `force_create` deliberately: `type` and `is_admin` are excluded from
    `User.fillable` so request input can never escalate privileges, which
    means `create()` would silently drop them and seed three identical
    non-admin accounts. Seeding is a trusted path, so it bypasses the guard.

    The demo tenant exists because `tenant@craft.local` is `type = "tenant"`
    and a tenant user with no `tenant_id` is not a coherent account: turn
    multi-tenancy on and every scoped query it makes raises
    `TenantNotBoundError`, because nothing resolves a tenant for it. Seeding a
    user whose own configuration cannot work is worse than seeding nothing.
    """

    #: Fixed so the demo is reproducible — re-seeding lands on the same tenant,
    #: and a fixture can refer to it without reading it back first.
    DEMO_TENANT_ID = "00000000-0000-7000-8000-000000000001"
    DEMO_TENANT_SLUG = "acme"

    def run(self):
        self.seed_demo_tenant()

        self._ensure_user({
            "name": "Standard User",
            "email": "user@craft.local",
            "password": "craft",
            "type": "user",
            "is_admin": False,
        })
        self._ensure_user({
            "name": "Tenant User",
            "email": "tenant@craft.local",
            "password": "craft",
            "type": "tenant",
            "is_admin": False,
            # What `ScopeTenant.resolve()` reads when the host names no tenant.
            "tenant_id": self.DEMO_TENANT_ID,
        })
        self._ensure_user({
            "name": "Admin User",
            "email": "admin@craft.local",
            "password": "craft",
            "type": "admin",
            "is_admin": True,
        })

    @staticmethod
    def _ensure_user(values):
        """Preserve an existing account, including its password and access."""
        if User.query().where("email", values["email"]).first() is None:
            User.force_create(values)

    def seed_demo_tenant(self):
        """Insert the demo tenant, idempotently.

        Written as a guarded INSERT rather than a model call because the
        `tenants` table belongs to the framework and has no application model —
        and because seeding must survive being run twice.
        """
        from datetime import datetime, timezone

        existing = DB.select_one(
            "SELECT id FROM tenants WHERE id = ?", [self.DEMO_TENANT_ID]
        )
        if existing is not None:
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        DB.statement(
            "INSERT INTO tenants (id, name, slug, is_active, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [self.DEMO_TENANT_ID, "Acme Corporation", self.DEMO_TENANT_SLUG,
             True, now, now],
        )
