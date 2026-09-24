"""Create the translation store and the settings table.

These two are engine infrastructure, not application tables: the translator
reads `translations` directly, and `craft.support.settings` reads `settings`.
A project that drops them loses runtime localization and stored settings.

RBAC tables (`roles`, `permissions`, `role_user`, `permission_role`) are
deliberately absent. `craft make:admin` creates them alongside the models that
use them, so a project that never asks for role-based access control does not
carry four unused tables and their indexes.
"""

from craft.migrations import Migration, Schema


def up():
    Schema.create_table("translations", lambda t: (
        t.id(),
        t.string("key"),
        t.string("locale"),
        t.text("value"),
        t.timestamps(),
    ))

    Schema.create_table("settings", lambda t: (
        t.id(),
        t.string("key").unique(),
        t.text("value"),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("settings")
    Schema.drop_table("translations")
