"""Declares the control panel's navigation.

Category: Application (Providers).
Relations:
  - Registers items on the framework's `nav` registry
    (`engine/support/navigation.py`), rendered by
    `resources/views/layouts/panel.forge.py`.
  - Every item carries the same guard as the route it points at, so the menu
    and the router cannot disagree. An item nobody may reach is simply not
    rendered — and its section disappears with it.
References:
  - Guide: `documentation/authorization.md`

The panel is for **every** signed-in account, not only administrators. An
ordinary user sees their own workspace (their posts, their profile, the access
they hold); an administrator additionally sees the sections that manage other
people. That is the whole reason the menu is filtered rather than duplicated:
one declaration, and each visitor gets the subset that is true for them.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Nav
from craft.providers import ServiceProvider


class PanelServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        # Icons are inline SVG shared with every template, so the panel paints
        # correctly on first render with no extra request.
        from app.Support.PanelIcons import panel_icon

        self.app.make("view").share("panel_icon", panel_icon)

        # -- Sections, in the order they appear -----------------------------
        Nav.section("workspace", "Workspace", order=10)
        Nav.section("people", "People & Access", order=30)
        Nav.section("system", "System", order=40)

        # -- Workspace: what every signed-in account gets --------------------
        Nav.add("workspace", "Dashboard", "/panel", icon="home", order=10)
        Nav.add("workspace", "My Profile", "/panel/profile", icon="user", order=20)

        # -- People & Access: administrators only ----------------------------
        # `Access audit` shows permission slugs, the path each grant arrives by
        # and the raw ABAC conditions. That is the installation's security
        # configuration, not the visitor's personal data: knowing that
        # `delete-post` reaches you via `group-role` under such-and-such
        # condition is a map for probing the system. Administrators only.
        Nav.add("people", "Users", "/panel/users", icon="users", order=10, role="admin")
        Nav.add("people", "Access audit", "/panel/access", icon="key", order=15, role="admin")
        Nav.add("people", "Groups", "/admin/groups", icon="collection", order=20, role="admin")
        Nav.add("people", "Roles", "/admin/roles", icon="badge", order=30, role="admin")
        Nav.add("people", "Permissions", "/admin/permissions", icon="key", order=40, role="admin")

        # -- System: total control over the running installation --------------
        # Every one of these reads the live application rather than a config
        # file, so an administrator can answer "what is this process actually
        # doing?" without shelling into the container.
        Nav.add("system", "Routes", "/panel/routes", icon="document", order=10, role="admin")
        Nav.add("system", "Database", "/panel/database", icon="collection", order=20, role="admin")
        Nav.add("system", "Cache", "/panel/cache", icon="squares", order=30, role="admin")
        Nav.add("system", "Queue", "/panel/queue", icon="puzzle", order=40, role="admin")
        Nav.add("system", "Scheduler", "/panel/schedule", icon="badge", order=50, role="admin")
        Nav.add("system", "Logs", "/panel/logs", icon="document", order=60, role="admin")
        Nav.add("system", "Modules", "/panel/modules", icon="squares", order=70, role="admin")
        Nav.add("system", "Plugins", "/panel/plugins", icon="puzzle", order=80, role="admin")
        Nav.add("system", "Tenants", "/panel/tenants", icon="collection", order=90, role="admin")
        Nav.add("system", "CRUD builder", "/admin/crud-builder", icon="wrench", order=100, role="admin")
        Nav.add("system", "About this install", "/panel/system", icon="info", order=110, role="admin")
