"""EngineUpdateController - the engine update screen of the admin panel.

Category: Application (Admin Controllers).
Relations:
  - Resolves `engine_updates` from the container (`engine/lifecycle/updates.py`),
    the same service `dev.py engine check|update|upgrade` uses.
  - Routes in `routes/web.py` behind `auth` + `role:admin` (`make:engine-panel`).
  - The verification command comes from `craft-engine.lock`, set with
    `dev.py engine verify-command`; no field of this screen runs a command.
References:
  - Guide: `documentation/engine-lifecycle.md`, ADR 0005
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from typing import Any

from app.Http.Controllers.Panel.PanelPage import PanelPage
from craft.facades import Auth
from craft.http.controller import Controller
from craft.http.response import redirect
from craft.lifecycle import EngineLifecycleError


class EngineUpdateController(PanelPage, Controller):
    """Shows the update notice, reviews a move and applies it."""

    def index(self, request: Any) -> Any:
        """Render the pin, the cached notice, patches and drift; never calls the network."""
        return self._screen(request, refusal="")

    def check(self, request: Any) -> Any:
        """Ask the canonical repository for newer releases, then show the screen again."""
        self._updates().check()
        return redirect(route="admin.engine.index")

    def review(self, request: Any) -> Any:
        """Show what a move would do - patches and changelog - without changing anything."""
        target = str(request.input("target", "update"))
        try:
            report = self._updates().review(target)
        except EngineLifecycleError as refused:
            return self._screen(request, refusal=str(refused))
        return self.panel(request, "admin.engine.review", {"report": report, "target": target})

    def apply(self, request: Any) -> Any:
        """Perform the move reviewed on the previous screen, verified by the lock's command."""
        target = str(request.post("target", "update"))
        user = Auth.user()
        actor = str(user.get_attribute("email")) if user is not None else ""
        try:
            report = self._updates().apply(target, actor)
        except EngineLifecycleError as refused:
            return self._screen(request, refusal=str(refused))
        return self.panel(request, "admin.engine.review", {"report": report, "target": target})

    def _screen(self, request: Any, refusal: str) -> Any:
        """Render the overview, with the refusal code of a failed action when there is one."""
        updates = self._updates()
        notice = updates.notice()
        # Passed here too, so the screen works under a panel shell generated
        # before the shell itself carried the notice.
        return self.panel(request, "admin.engine.index", {
            "overview": updates.overview(),
            "notice": notice,
            "engine_update": notice,
            "refusal": refusal,
        })

    def _updates(self) -> Any:
        """Return the engine update service from the container."""
        return self.container().make("engine_updates")
