"""Generation of the engine update screen of the admin panel (ADR 0005).

`make:engine-panel` adds `/admin/engine` to a project that has the admin panel:
the screen that shows the pinned release, the cached update notice, local
patches and drift, reviews a move and applies it; the alert partial the panel
pages include; the screen's translations; and the routes, behind `auth` and
`role:admin`. `make:admin` runs it too, so a new panel has the screen from
the start, and an older panel gets it by running this command on its own.

Templates live under `engine_panel_templates/`, suffixed `.stub`, and are
copied verbatim. Generation is all-or-nothing and the routes are appended
once: the screen's first route is the token.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Final

from engine.cli import layout_scaffolder

#: Root of the template tree, alongside this module.
TEMPLATE_ROOT: Final[Path] = Path(__file__).resolve().parent / "engine_panel_templates"

#: Suffix marking a template file. Stripped when the file is written out.
STUB_SUFFIX: Final[str] = ".stub"

#: The panel shell the screen renders through; `make:admin` writes it.
PANEL_SHELL: Final[Path] = Path("app", "Http", "Controllers", "Panel", "PanelPage.py")

#: Heading written above the appended route block.
ROUTES_MARKER: Final[str] = "# Engine Update Routes (make:engine-panel)"

#: Presence of this call in `routes/web.py` means the screen is registered.
ROUTES_TOKEN: Final[str] = 'Route.get("/admin/engine", [EngineUpdateController, "index"])'

#: Import the appended routes need.
ROUTE_IMPORT: Final[str] = "from app.Http.Controllers.Admin.EngineUpdateController import EngineUpdateController"

#: The screen's routes. Moving the engine is an administrative act: every
#: route carries `role:admin` on top of `auth`, and the two that change state
#: are POST, so the CSRF middleware guards them.
ROUTE_BLOCK: Final[str] = '''
Route.get("/admin/engine", [EngineUpdateController, "index"]).middleware("auth", "role:admin").name("admin.engine.index")
Route.post("/admin/engine/check", [EngineUpdateController, "check"]).middleware("auth", "role:admin").name(
    "admin.engine.check"
)
Route.get("/admin/engine/review", [EngineUpdateController, "review"]).middleware("auth", "role:admin").name(
    "admin.engine.review"
)
Route.post("/admin/engine/apply", [EngineUpdateController, "apply"]).middleware("auth", "role:admin").name(
    "admin.engine.apply"
)
'''


class EnginePanelRequiresAdmin(Exception):
    """The project has no admin panel shell to render the screen through.

    Args:
        path: The panel shell that was expected.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(str(path))
        self.path = path


def template_files() -> list[Path]:
    """Return every template, relative to the template root, in a stable order."""
    return sorted(path.relative_to(TEMPLATE_ROOT) for path in TEMPLATE_ROOT.rglob(f"*{STUB_SUFFIX}"))


def _routes_path(base: Path) -> Path:
    """Return the project's web route file."""
    return base / "routes" / "web.py"


def is_registered(base_path: str) -> bool:
    """Report whether the screen's routes are already in `routes/web.py`."""
    routes = _routes_path(Path(base_path))
    return routes.is_file() and ROUTES_TOKEN in routes.read_text(encoding="utf-8")


def register_routes(base_path: str) -> str:
    """Append the `/admin/engine` routes once; an existing line is never rewritten.

    Args:
        base_path: Root of the target project.

    Returns:
        The path to `routes/web.py`.
    """
    routes = _routes_path(Path(base_path))
    content = routes.read_text(encoding="utf-8") if routes.is_file() else _routes_header()
    if ROUTES_TOKEN not in content:
        imports = "" if ROUTE_IMPORT in content else ROUTE_IMPORT + "\n"
        content = content.rstrip("\n") + f"\n\n{ROUTES_MARKER}\n" + imports + ROUTE_BLOCK
        routes.parent.mkdir(parents=True, exist_ok=True)
        routes.write_text(content, encoding="utf-8")
    return str(routes)


def _routes_header() -> str:
    """Return the header of a route file written from scratch, with `Route` in scope."""
    from engine.cli.admin_scaffolder import ROUTES_HEADER

    return ROUTES_HEADER


def _copy_templates(base: Path, *, force: bool) -> dict[str, str]:
    """Copy every template into the project, refusing any conflict before writing.

    Raises:
        FileExistsError: Naming the first file that exists, when `force` is False.
    """
    plan = [(TEMPLATE_ROOT / relative, base / str(relative)[: -len(STUB_SUFFIX)]) for relative in template_files()]
    conflicts = [target for _source, target in plan if target.exists()]
    if conflicts and not force:
        raise FileExistsError(str(conflicts[0]))
    written: dict[str, str] = {}
    for source, target in plan:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written[str(target.relative_to(base))] = str(target)
    return written


def build_engine_panel(base_path: str, *, force: bool = False) -> dict[str, Any]:
    """Generate the engine update screen into a project that has the admin panel.

    Args:
        base_path: Root of the target project.
        force: Overwrite files the screen also provides.

    Returns:
        `files` (project-relative path to absolute path) and `already_configured`.

    Raises:
        EnginePanelRequiresAdmin: When the panel shell is missing (run `make:admin`).
        FileExistsError: When a generated file exists and `force` is False.
        FileNotFoundError: When a template of the installation is missing.
    """
    base = Path(base_path)
    if not (base / PANEL_SHELL).is_file():
        raise EnginePanelRequiresAdmin(base / PANEL_SHELL)
    if is_registered(base_path) and not force:
        return {"files": {"routes/web.py": str(_routes_path(base))}, "already_configured": True}
    layout_scaffolder.require_templates(*(str(TEMPLATE_ROOT / relative) for relative in template_files()))
    written = _copy_templates(base, force=force)
    written["routes/web.py"] = register_routes(base_path)
    return {"files": written, "already_configured": False}


__all__ = ["EnginePanelRequiresAdmin", "build_engine_panel", "is_registered", "register_routes", "template_files"]
