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

from craft.http.controller import Controller
from craft.http.response import redirect
from craft.facades import Auth, AntiSpam
from craft.validation.validator import Validator
from app.Models.User import User


class AuthController(Controller):
    def show_login(self, request):
        return self.view("auth.login")

    def show_signin(self, request):
        return redirect(route="login")

    def login(self, request):
        # Validate honeypot and anti-spam if configured
        is_valid_human, _ = AntiSpam.verify(request.all(), ip_address=getattr(request, "ip", "127.0.0.1"))
        if not is_valid_human:
            return redirect.back().with_errors({"email": "Automated spam activity detected."}).with_input()

        validator = Validator.make(request.all(), {
            "email": ["required", "email"],
            "password": ["required", "min:6"],
        })

        if validator.fails():
            return redirect.back().with_errors(validator.errors()).with_input()

        credentials = {
            "email": request.get_input("email"),
            "password": request.get_input("password"),
        }

        if Auth.attempt(credentials):
            return redirect(route="__SUCCESS_ROUTE__")

        return redirect.back().with_errors({
            "email": "These credentials do not match our records."
        }).with_input()

    def show_register(self, request):
        return self.view("auth.register")

    def register(self, request):
        is_valid_human, _ = AntiSpam.verify(request.all(), ip_address=getattr(request, "ip", "127.0.0.1"))
        if not is_valid_human:
            return redirect.back().with_errors({"email": "Automated spam activity detected."}).with_input()

        validator = Validator.make(request.all(), {
            "name": ["required", "string", "min:2", "max:100"],
            "email": ["required", "email"],
            "password": ["required", "min:8"],
        })

        if validator.fails():
            return redirect.back().with_errors(validator.errors()).with_input()

        name = (request.get_input("name") or "").strip()
        email = (request.get_input("email") or "").strip()
        password = request.get_input("password") or ""

        # Domain authorization check if identity service exists
        try:
            from app.Services.Identity.DomainValidator import DomainValidator
            if not DomainValidator.is_allowed_email(email, allow_system_domains=True):
                return redirect.back().with_errors({
                    "email": "Email domain is not authorized for registration."
                }).with_input()
        except ImportError:
            pass

        user = User.create({
            "name": name,
            "email": email,
            "password": password,
        })
        Auth.login(user)
        return redirect(route="__SUCCESS_ROUTE__")

    def logout(self, request):
        Auth.logout()
        return redirect(route="login")

    def dashboard(self, request):
        user = Auth.user()
        return self.view("auth.dashboard", {"user": user})
'''.replace("__SUCCESS_ROUTE__", success_route)


def login_view_stub() -> str:
    return '''@extends("layouts.app")

@section("title", "Sign In - Craft Framework")

@section("content")
<div class="max-w-md mx-auto my-12 bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
    <div class="mb-6 text-center">
        <h2 class="text-2xl font-black text-slate-900">Sign In</h2>
        <p class="text-slate-500 text-sm mt-1">Access your account dashboard</p>
    </div>

    @if(errors.any())
        <div class="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm">
            <ul class="list-disc list-inside space-y-1">
                @for err in errors.all()
                    <li>{{ err }}</li>
                @endfor
            </ul>
        </div>
    @endif

    <form action="/login" method="POST" class="space-y-4">
        @csrf
        @honeypot

        <div>
            <label for="email" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Email Address</label>
            <input type="email" name="email" id="email" value="{{ old('email', '') }}" required autofocus
                   class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:outline-none focus:border-orange-500 focus:bg-white transition">
            @error('email')
                <p class="text-rose-500 text-xs mt-1 font-medium">{{ message }}</p>
            @enderror
        </div>

        <div>
            <label for="password" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Password</label>
            <input type="password" name="password" id="password" required
                   class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:outline-none focus:border-orange-500 focus:bg-white transition">
            @error('password')
                <p class="text-rose-500 text-xs mt-1 font-medium">{{ message }}</p>
            @enderror
        </div>

        <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 rounded-xl shadow-md transition duration-200 mt-2">
            Sign In
        </button>
    </form>

    <p class="mt-6 text-center text-xs text-slate-500">
        Don't have an account? <a href="/register" class="text-orange-500 hover:text-orange-600 font-bold">Create one</a>
    </p>
</div>
@endsection
'''


def register_view_stub() -> str:
    return '''@extends("layouts.app")

@section("title", "Register Account - Craft Framework")

@section("content")
<div class="max-w-md mx-auto my-12 bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
    <div class="mb-6 text-center">
        <h2 class="text-2xl font-black text-slate-900">Create Account</h2>
        <p class="text-slate-500 text-sm mt-1">Get started with your new workspace</p>
    </div>

    @if(errors.any())
        <div class="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm">
            <ul class="list-disc list-inside space-y-1">
                @for err in errors.all()
                    <li>{{ err }}</li>
                @endfor
            </ul>
        </div>
    @endif

    <form action="/register" method="POST" class="space-y-4">
        @csrf
        @honeypot

        <div>
            <label for="name" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Full Name</label>
            <input type="text" name="name" id="name" value="{{ old('name', '') }}" required autofocus
                   class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:outline-none focus:border-orange-500 focus:bg-white transition">
            @error('name')
                <p class="text-rose-500 text-xs mt-1 font-medium">{{ message }}</p>
            @enderror
        </div>

        <div>
            <label for="email" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Email Address</label>
            <input type="email" name="email" id="email" value="{{ old('email', '') }}" required
                   class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:outline-none focus:border-orange-500 focus:bg-white transition">
            @error('email')
                <p class="text-rose-500 text-xs mt-1 font-medium">{{ message }}</p>
            @enderror
        </div>

        <div>
            <label for="password" class="block text-xs font-semibold text-slate-600 uppercase mb-1">Password</label>
            <input type="password" name="password" id="password" required
                   class="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 text-sm focus:outline-none focus:border-orange-500 focus:bg-white transition">
            @error('password')
                <p class="text-rose-500 text-xs mt-1 font-medium">{{ message }}</p>
            @enderror
        </div>

        <button type="submit" class="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 rounded-xl shadow-md transition duration-200 mt-2">
            Create Account
        </button>
    </form>

    <p class="mt-6 text-center text-xs text-slate-500">
        Already registered? <a href="/login" class="text-orange-500 hover:text-orange-600 font-bold">Sign in here</a>
    </p>
</div>
@endsection
'''


def dashboard_view_stub() -> str:
    return '''@extends("layouts.app")

@section("title", "Dashboard - Craft Framework")

@section("content")
<div class="max-w-4xl mx-auto my-10 px-4">
    <div class="bg-white rounded-2xl shadow-lg border border-slate-200 p-8 mb-8">
        <div class="flex items-center justify-between pb-6 border-b border-slate-100">
            <div>
                <h1 class="text-2xl font-black text-slate-900">Welcome back{{ ", " + user.name if user and hasattr(user, "name") else "" }}!</h1>
                <p class="text-slate-500 text-sm mt-1">Logged in via Craft Engine Authentication</p>
            </div>
            <form action="/logout" method="POST">
                @csrf
                <button type="submit" class="px-4 py-2 bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-600 rounded-xl text-sm font-semibold transition border border-slate-200 hover:border-rose-200">
                    Sign Out
                </button>
            </form>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
            <div class="p-6 bg-orange-50/50 border border-orange-100 rounded-xl">
                <h3 class="text-xs font-bold uppercase tracking-wider text-orange-600 mb-2">Auth Status</h3>
                <p class="text-sm font-medium text-slate-800">Authenticated Session Active</p>
            </div>
            <div class="p-6 bg-slate-50 border border-slate-200/60 rounded-xl">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">User Email</h3>
                <p class="text-sm font-mono text-slate-700">{{ user.email if user and hasattr(user, "email") else "user@craft.local" }}</p>
            </div>
            <div class="p-6 bg-slate-50 border border-slate-200/60 rounded-xl">
                <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Framework</h3>
                <p class="text-sm font-mono text-slate-700">Craft Engine v3</p>
            </div>
        </div>
    </div>
</div>
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
