"""
Audit Log — records model writes and authentication events to `system_logs`.
Category: Plugin (bundled example).
Relations:
  - Registers hooks against the framework lifecycle events emitted by
    `engine/events/lifecycle.py` and bridged to hooks by
    `engine/plugins/manager.py`.
  - Persists through the `DB` facade straight into `system_logs`. It used
    to go through the demo application's `SystemLog` model, so the plugin
    shipped with the framework silently wrote nothing in any project that
    had not reproduced that model.
References:
  - Guide: `documentation/plugins.md`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import json

PLUGIN = {
    "slug": "audit-log",
    "name": "Audit Log",
    "version": "1.0.0",
    "description": "Writes an audit trail of model changes and logins to system_logs.",
}

#: The table this plugin itself writes to. Auditing it would make every write
#: trigger `model.created`, which writes another row, which triggers
#: `model.created` again — unbounded recursion. Any plugin that persists from
#: inside a model hook needs the same guard.
IGNORED_TABLES = {"system_logs"}


def _record(level, message, context):
    """Write one audit row, never raising into the framework.

    A failure here means the audit trail lost an entry; it must not mean the
    business write that triggered it fails. `trigger_hook` already isolates
    exceptions, but being explicit keeps the intent local and readable.
    """
    from datetime import datetime, timezone

    from craft.facades import DB

    now = datetime.now(timezone.utc).isoformat()
    try:
        DB.table("system_logs").insert({
            "level": level,
            "message": message,
            "context": json.dumps(context, default=str),
            "created_at": now,
            "updated_at": now,
        })
    except Exception:
        import logging

        logging.getLogger("craft").warning(
            "audit-log could not persist an entry", exc_info=True
        )


def _describe(model):
    """A stable, non-sensitive identity for the audited record."""
    return model.get_attribute(model.primary_key)


def _on_model_write(verb):
    def handler(event):
        table = getattr(event, "table", None)
        if table in IGNORED_TABLES:
            return
        _record(
            "info",
            f"{table}.{verb}",
            {"table": table, "id": _describe(event.model), "action": verb},
        )

    return handler


def _on_login(event):
    user = event.user
    _record("info", "auth.login", {
        "user_id": _describe(user),
        "email": user.get_attribute("email"),
    })


def _on_login_failed(event):
    # `event.email` is the identifier only — the framework never puts the
    # submitted password on the event, so there is nothing sensitive to strip.
    _record("warning", "auth.failed", {"email": event.email})


def _on_logout(event):
    _record("info", "auth.logout", {"user_id": _describe(event.user)})


def register(app):
    """Wire the plugin's hooks. Called by `PluginManager.load_enabled`."""
    plugins = app.make("plugin")

    plugins.add_hook("model.created", _on_model_write("created"))
    plugins.add_hook("model.updated", _on_model_write("updated"))
    plugins.add_hook("model.deleted", _on_model_write("deleted"))
    plugins.add_hook("auth.login", _on_login)
    plugins.add_hook("auth.failed", _on_login_failed)
    plugins.add_hook("auth.logout", _on_logout)
