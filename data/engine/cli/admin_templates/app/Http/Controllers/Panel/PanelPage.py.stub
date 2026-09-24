"""Shared shell for every page rendered inside the control panel.

Category: Application (Panel Controllers).
Relations:
  - Mixed into `PanelController` and into the admin controllers that used to
    render inside `layouts.app` (`RoleController`, `GroupController`,
    `CrudBuilderController`).
  - Fills the context `resources/views/layouts/panel.forge.py` needs: the
    filtered menu (`nav_sections`) and the signed-in account.

Extracted so no page can forget the menu. A panel page rendered without
`nav_sections` loses its navigation entirely, and the failure looks like a
styling bug rather than a missing variable — which is exactly how you end up
with two shells drifting apart.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.facades import Auth, Nav


class PanelPage:
    """Adds `panel()` to a controller. Combine with `Controller`."""

    def panel(self, request, template: str, data: dict):
        """Render `template` inside the panel shell."""
        user = Auth.user()
        context = {
            "current_user": user,
            "request": request,
            "nav_sections": Nav.for_user(user, self.current_path(request)),
            # The panel layout owns its own sidebar; the marketing layout's
            # rail must never be switched on underneath it.
            "show_sidebar": False,
        }
        context.update(data)
        return self.view(template, context)

    @staticmethod
    def current_path(request) -> str:
        """Current path, used to highlight the active menu item."""
        try:
            return request.url.path
        except Exception:
            return ""

    # -- helpers every panel page tends to need --------------------------------

    @staticmethod
    def container():
        from craft.container.application import Container

        return Container.getInstance()

    def app_access(self):
        return self.container().make("access")

    def is_admin(self, user=None) -> bool:
        """`is_admin`, or the `admin` role — either is sufficient.

        The same rule as the `access-admin-dashboard` Gate ability, so an
        installation managing access purely through roles and one that flags
        the column behave identically.
        """
        user = user if user is not None else Auth.user()
        if user is None:
            return False
        if user.get_attribute("is_admin"):
            return True
        return self.app_access().has_role(user, "admin")
