"""
AuthScaffolder - Authentication scaffolding generator for Craft Engine.

Category: Core Framework (CLI).
Relations:
  - Invoked from `dev.py make:auth` (`engine/cli/app.py`).
  - Scaffolds `AuthController`, `LoginRequest`, `RegisterRequest`, Forge views,
    and registers auth routes in `routes/web.py`.
References:
  - Guide: `documentation/cli.md#make-auth`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import os
import re
from typing import Any, Dict

from engine.cli import identity_config, layout_scaffolder

#: Templates for the concrete classes authentication needs. The engine
#: ships the contract (`craft.auth.models.AuthenticatableMixin`) and the
#: resolver (`craft.auth.registry`); the concrete `User` belongs to the
#: project, so it is generated rather than imported from the framework.
AUTH_TEMPLATE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_templates")

#: Dotted path of the generated user model, recorded in `config/auth.py`.
USER_MODEL_PATH = "app.Models.User.User"


def _copy_auth_templates(base_path: str, force: bool = False) -> Dict[str, str]:
    """Write the user model and its migration into the project.

    Args:
        base_path: Root of the target project.
        force: Overwrite files that already exist.

    Returns:
        A mapping of result key to the absolute path written. A file the
        project already has is left alone and omitted.
    """
    import shutil

    written: Dict[str, str] = {}
    for key, relative in (
        ("model_user", os.path.join("app", "Models", "User.py")),
        (
            "migration_users",
            os.path.join("database", "migrations", "2025_01_01_000001_create_users_table.py"),
        ),
        (
            "migration_translations",
            os.path.join("database", "migrations", "2026_09_25_000010_seed_auth_translations.py"),
        ),
    ):
        destination = os.path.join(base_path, relative)
        if os.path.exists(destination) and not force:
            continue
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copyfile(os.path.join(AUTH_TEMPLATE_ROOT, relative + ".stub"), destination)
        written[key] = destination

    marker = os.path.join(base_path, "app", "Models", "__init__.py")
    if not os.path.exists(marker):
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("")
    return written


def _write(path: str, content: str, force: bool = False) -> str:
    """Write content to path, creating directories if needed, unless exists and not force."""
    if os.path.exists(path) and not force:
        raise FileExistsError(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


def login_request_stub() -> str:
    return '''"""Login request validator."""

from craft.validation.form_request import FormRequest


class LoginRequest(FormRequest):
    # The honeypot and time trap rendered by @honeypot in the view are checked
    # by FormRequest.passes(); NR-06 requires them on any public form.
    antispam = True

    def authorize(self) -> bool:
        return True

    def rules(self) -> dict:
        return {
            "email": ["required", "email"],
            "password": ["required", "min:6"],
        }
'''


def register_request_stub() -> str:
    return '''"""Registration request validator."""

from craft.validation.form_request import FormRequest


class RegisterRequest(FormRequest):
    antispam = True

    def authorize(self) -> bool:
        return True

    def rules(self) -> dict:
        return {
            "name": ["required", "string", "min:2", "max:100"],
            "email": ["required", "email"],
            "password": ["required", "min:8"],
        }
'''


def auth_controller_stub(success_route: str = "dashboard") -> str:
    """Build a controller that redirects to a route present in its target app."""
    return '''"""Auth controller - login, register, logout, and dashboard."""

from craft.facades import Auth
from craft.http.controller import Controller
from craft.http.response import redirect
from craft.support import __

from app.Http.Requests.Auth.LoginRequest import LoginRequest
from app.Http.Requests.Auth.RegisterRequest import RegisterRequest
from app.Models.User import User


class AuthController(Controller):
    """Sign-in, registration and sign-out.

    Validation and the anti-spam check live in the FormRequests beside this
    file; `passes()` runs both. A failure goes back to the form with the errors
    and the input the visitor typed - never the password.
    """

    def show_login(self, request):
        return self.view("auth.login")

    def show_signin(self, request):
        return redirect(route="login")

    def login(self, request):
        form = LoginRequest(request)
        if not form.passes():
            return self._back(request, form.errors)

        credentials = {"email": request.get_input("email"), "password": request.get_input("password")}
        if Auth.attempt(credentials):
            return redirect(route="__SUCCESS_ROUTE__")
        return self._back(request, {"email": [__("auth.login.failed")]})

    def show_register(self, request):
        return self.view("auth.register")

    def register(self, request):
        form = RegisterRequest(request)
        if not form.passes():
            return self._back(request, form.errors)

        user = User.create({
            "name": (request.get_input("name") or "").strip(),
            "email": (request.get_input("email") or "").strip(),
            "password": request.get_input("password") or "",
        })
        Auth.login(user)
        return redirect(route="__SUCCESS_ROUTE__")

    def logout(self, request):
        Auth.logout()
        return redirect(route="login")

    def dashboard(self, request):
        return self.view("auth.dashboard", {"user": Auth.user()})

    @staticmethod
    def _back(request, errors):
        """Return to the form with errors and every field except the password."""
        kept = {key: value for key, value in request.all().items() if "password" not in key}
        return redirect.back(request).with_errors(errors).with_input(kept)
'''.replace("__SUCCESS_ROUTE__", success_route)


def login_view_stub() -> str:
    return '''@extends("layouts.app")

@section("title", __('auth.login.title'))

@section("content")
<main>
    <h1>{{ __('auth.login.title') }}</h1>

    @if(errors.any())
        <ul role="alert">
            @foreach(errors.all() as err)
                <li>{{ err }}</li>
            @endforeach
        </ul>
    @endif

    <form action="/login" method="POST">
        @csrf
        @honeypot

        <p>
            <label for="email">{{ __('auth.field.email') }}</label>
            <input type="email" name="email" id="email" value="{{ old('email', '') }}" required autofocus autocomplete="username">
            @error('email')
                <small role="alert">{{ message }}</small>
            @enderror
        </p>
        <p>
            <label for="password">{{ __('auth.field.password') }}</label>
            <input type="password" name="password" id="password" required autocomplete="current-password">
            @error('password')
                <small role="alert">{{ message }}</small>
            @enderror
        </p>
        <p><button type="submit">{{ __('auth.login.action.submit') }}</button></p>
    </form>

    <p><a href="/register">{{ __('auth.login.link.register') }}</a></p>
</main>
@endsection
'''


def register_view_stub() -> str:
    return '''@extends("layouts.app")

@section("title", __('auth.register.title'))

@section("content")
<main>
    <h1>{{ __('auth.register.title') }}</h1>

    @if(errors.any())
        <ul role="alert">
            @foreach(errors.all() as err)
                <li>{{ err }}</li>
            @endforeach
        </ul>
    @endif

    <form action="/register" method="POST">
        @csrf
        @honeypot

        <p>
            <label for="name">{{ __('auth.field.name') }}</label>
            <input type="text" name="name" id="name" value="{{ old('name', '') }}" required autofocus autocomplete="name">
            @error('name')
                <small role="alert">{{ message }}</small>
            @enderror
        </p>
        <p>
            <label for="email">{{ __('auth.field.email') }}</label>
            <input type="email" name="email" id="email" value="{{ old('email', '') }}" required autocomplete="email">
            @error('email')
                <small role="alert">{{ message }}</small>
            @enderror
        </p>
        <p>
            <label for="password">{{ __('auth.field.password') }}</label>
            <input type="password" name="password" id="password" required minlength="8" autocomplete="new-password">
            @error('password')
                <small role="alert">{{ message }}</small>
            @enderror
        </p>
        <p><button type="submit">{{ __('auth.register.action.submit') }}</button></p>
    </form>

    <p><a href="/login">{{ __('auth.register.link.login') }}</a></p>
</main>
@endsection
'''


def dashboard_view_stub() -> str:
    return '''@extends("layouts.app")

@section("title", __('auth.dashboard.title'))

@section("content")
<main>
    <h1>{{ __('auth.dashboard.title') }}</h1>
    @if(user)
        <p>{{ __('auth.dashboard.signed_in_as', email=user.get_attribute('email')) }}</p>
    @endif
    <form action="/logout" method="POST">
        @csrf
        <button type="submit">{{ __('auth.dashboard.action.sign_out') }}</button>
    </form>
</main>
@endsection
'''


#: Written when `routes/web.py` does not exist yet, so the appended route
#: block has the `Route` facade in scope.
_ROUTES_HEADER = '''"""Web routes."""

from craft.facades import Route
'''


def register_auth_routes(base_path: str) -> str:
    """Ensure authentication routes are registered in routes/web.py.

    Creates the routes file when it is absent. This used to return an empty
    string instead, which meant the first scaffold into a project without
    `routes/web.py` registered nothing, and a second scaffold could not detect
    that authentication was already configured. This repository always has the
    file, so the gap stayed hidden; a project generated by `craft new` walks
    exactly this path.

    Args:
        base_path: Root of the target project.

    Returns:
        The path to `routes/web.py`.
    """
    web_routes_path = os.path.join(base_path, "routes", "web.py")
    if os.path.exists(web_routes_path):
        with open(web_routes_path, "r", encoding="utf-8") as handle:
            content = handle.read()
    else:
        os.makedirs(os.path.dirname(web_routes_path), exist_ok=True)
        content = _ROUTES_HEADER

    # If login route is already declared, do nothing
    if re.search(r'Route\.(?:get|post)\(["\']/login["\']', content):
        return web_routes_path

    route_snippet = """
# Authentication Routes (Scaffolded by make:auth)
Route.get("/login", [AuthController, "show_login"]).name("login")
Route.get("/signin", [AuthController, "show_signin"])
Route.post("/login", [AuthController, "login"]).middleware("throttle").name("login.attempt")
Route.get("/register", [AuthController, "show_register"]).name("register")
Route.post("/register", [AuthController, "register"]).middleware("throttle").name("register.store")
Route.post("/logout", [AuthController, "logout"]).name("logout")
Route.get("/dashboard", [AuthController, "dashboard"]).middleware("auth").name("dashboard")
"""
    import_line = "from app.Http.Controllers.Auth.AuthController import AuthController\n"
    if "from app.Http.Controllers.Auth.AuthController import AuthController" not in content:
        # Prepend import after first docstring or imports
        content = import_line + content

    content = content.rstrip() + "\n" + route_snippet

    with open(web_routes_path, "w", encoding="utf-8") as handle:
        handle.write(content)

    return web_routes_path


def build_auth(
    base_path: str,
    *,
    views_only: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Scaffold authentication files (Controller, Requests, Forge views, routes)."""
    result: Dict[str, Any] = {"files": {}}
    routes_path = os.path.join(base_path, "routes", "web.py")
    controller_path = os.path.join(base_path, "app", "Http", "Controllers", "Auth", "AuthController.py")
    routes_content = ""
    if os.path.exists(routes_path):
        with open(routes_path, "r", encoding="utf-8") as handle:
            routes_content = handle.read()
    if not views_only and re.search(
        r'Route\.(?:get|post)\(["\']/login["\']', routes_content
    ):
        files = {"routes": routes_path}
        if os.path.exists(controller_path):
            files["controller"] = controller_path
        return {"files": files, "already_configured": True}

    # The generated views open with `@extends("layouts.app")`, so the shell has
    # to exist or every one of them raises at render time. Written only when
    # the project has none.
    layout_path = layout_scaffolder.ensure_layout(base_path, force=force)
    if layout_path is not None:
        result["files"]["view_layout"] = layout_path

    # The generated controller imports `app.Models.User`. The engine does not
    # ship that class - it resolves whatever the project declares - so the
    # generator writes it, along with the table it reads.
    result["files"].update(_copy_auth_templates(base_path, force=force))
    config_path = identity_config.record_models(
        base_path, {"user": USER_MODEL_PATH}, user_provider=True
    )
    if config_path is not None:
        result["files"]["config_auth"] = config_path

    # Views
    views_dir = os.path.join(base_path, "resources", "views", "auth")
    login_view_path = os.path.join(views_dir, "login.forge.py")
    register_view_path = os.path.join(views_dir, "register.forge.py")
    dashboard_view_path = os.path.join(views_dir, "dashboard.forge.py")

    _write(login_view_path, login_view_stub(), force=force)
    result["files"]["view_login"] = login_view_path

    _write(register_view_path, register_view_stub(), force=force)
    result["files"]["view_register"] = register_view_path

    _write(dashboard_view_path, dashboard_view_stub(), force=force)
    result["files"]["view_dashboard"] = dashboard_view_path

    if views_only:
        return result

    # Form Requests
    requests_dir = os.path.join(base_path, "app", "Http", "Requests", "Auth")
    login_req_path = os.path.join(requests_dir, "LoginRequest.py")
    register_req_path = os.path.join(requests_dir, "RegisterRequest.py")

    _write(login_req_path, login_request_stub(), force=force)
    result["files"]["request_login"] = login_req_path

    _write(register_req_path, register_request_stub(), force=force)
    result["files"]["request_register"] = register_req_path

    # Controller
    controller_dir = os.path.join(base_path, "app", "Http", "Controllers", "Auth")
    controller_path = os.path.join(controller_dir, "AuthController.py")
    success_route = "home" if re.search(r'\.name\(["\']home["\']\)', routes_content) else "dashboard"
    _write(controller_path, auth_controller_stub(success_route), force=force)
    result["files"]["controller"] = controller_path

    # Routes
    routes_file = register_auth_routes(base_path)
    if routes_file:
        result["files"]["routes"] = routes_file

    return result
