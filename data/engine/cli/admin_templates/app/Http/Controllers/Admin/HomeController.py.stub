"""Home Controller for Admin and Dashboard views."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.http.controller import Controller
from craft.http.response import redirect


class HomeController(Controller):
    def index(self, request):
        """The public landing page."""
        return self.view("home", {"show_sidebar": False})

    def admin(self, request):
        """`/admin` — kept only as a redirect into the control panel.

        This action used to render its own dashboard inside `layouts.app`,
        whose sidebar is a hover-expanding icon rail that covers the page
        underneath. Everything it showed — users, administrators, tenants —
        now lives in `/panel`, on a shell with a labelled sidebar and a menu
        filtered by what the visitor may actually reach.

        Two dashboards is how the two drift apart: one gets a new section, the
        other keeps an old guard, and eventually one of them is wrong. The
        redirect keeps every existing `/admin` bookmark and link working while
        there is exactly one panel to maintain.

        The route still carries `auth` + `role:admin`, so this redirect is not
        a way around the guard — an ordinary account is refused before reaching
        it, exactly as before.
        """
        return redirect(url="/panel", status=302)
