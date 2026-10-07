#!/usr/bin/env python3
# version: 1.2.0 | build: 2026-09-18 | update: 2026-09-18
"""Workspace-scoped DigitalOcean App Platform client.

A DigitalOcean API token is account-wide: it can modify or delete every app in
the account. This wrapper is the only way agents in this workspace talk to the
App Platform API, and it narrows the token to one app:

- the app is bound in .claude/do-app.json (name + id), next to this script;
- it lives in the owner's DigitalOcean project (PROJECT_ID), and nowhere else;
- every call that targets an app checks the bound id, the bound name and the project;
- `create` refuses when a binding exists or the name is already taken;
- there is no delete, and no way to pass an arbitrary app id.

The token is read from DIGITALOCEAN_TOKEN or the gitignored token directory
and is never printed.

Usage: do-app.py {propose|create|status|update|deploy}

Failures exit non-zero with one JSON line, {"error": CODE, ...params}:
TOKEN_MISSING, API_ERROR, DEPENDENCY_MISSING, APP_NOT_BOUND,
APP_NAME_MISMATCH, APP_OUTSIDE_PROJECT, APP_ALREADY_BOUND, APP_NAME_TAKEN,
APP_RENAME_REFUSED.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINDING = ROOT / ".claude" / "do-app.json"
SPEC = ROOT / "deploy" / "do-app.yaml"
TOKEN_FILES = (ROOT / ".do" / "dotoken.txt", ROOT / ".do" / "do-token.txt")
API = "https://api.digitalocean.com/v2"
# The DigitalOcean project that holds the owner's public apps (owner's choice, 2026-09-18).
PROJECT_ID = "c87eafe0-7bb4-45ee-996c-71874b62758d"


def fail(code: str, **params: object) -> None:
    # A machine code plus parameters, never a rendered sentence: the caller is an
    # operator or an agent, and the codes are documented in the usage docstring.
    sys.exit(json.dumps({"error": code, **params}))


def token() -> str:
    value = os.environ.get("DIGITALOCEAN_TOKEN", "").strip()
    for path in TOKEN_FILES:
        if not value and path.is_file():
            value = path.read_text().strip()
    if not value:
        fail("TOKEN_MISSING", sources=["DIGITALOCEAN_TOKEN", *map(str, TOKEN_FILES)])
    return value


def call(method: str, path: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        fail("API_ERROR", method=method, path=path, status=error.code,
             body=error.read().decode(errors="replace")[:500])


def spec() -> dict:
    # App Platform accepts the spec as JSON; the YAML file stays the readable source.
    try:
        import yaml
    except ImportError:
        fail("DEPENDENCY_MISSING", package="pyyaml")
    return yaml.safe_load(SPEC.read_text())


def binding() -> dict:
    if not BINDING.is_file():
        fail("APP_NOT_BOUND", binding=str(BINDING.relative_to(ROOT)), next_command="create")
    return json.loads(BINDING.read_text())


def project() -> dict:
    return call("GET", f"/projects/{PROJECT_ID}")["project"]


def in_project(app_id: str) -> bool:
    resources = call("GET", f"/projects/{PROJECT_ID}/resources?per_page=200").get("resources", [])
    return f"do:app:{app_id}" in {resource["urn"] for resource in resources}


def bound_app() -> dict:
    bound = binding()
    app = call("GET", f"/apps/{bound['app_id']}")["app"]
    if app["spec"]["name"] != bound["app_name"]:
        fail("APP_NAME_MISMATCH", app_id=bound["app_id"], actual=app["spec"]["name"], bound=bound["app_name"])
    if not in_project(app["id"]):
        fail("APP_OUTSIDE_PROJECT", app_id=app["id"], project_id=PROJECT_ID)
    return app


def summary(app: dict) -> None:
    phase = (app.get("active_deployment") or app.get("in_progress_deployment") or {}).get("phase", "none")
    domains = {domain["spec"]["domain"]: domain.get("phase") for domain in app.get("domains", [])}
    print(json.dumps({
        "id": app["id"], "name": app["spec"]["name"], "url": app.get("live_url"),
        "default_ingress": app.get("default_ingress"), "domains": domains, "deployment": phase,
    }, indent=2))


def main(command: str) -> None:
    if command == "propose":
        result = call("POST", "/apps/propose", {"spec": spec()})
        print(json.dumps({"valid": True, "project": project()["name"], "app_cost": result.get("app_cost")}, indent=2))
    elif command == "create":
        if BINDING.is_file():
            fail("APP_ALREADY_BOUND", app_id=binding()["app_id"], next_command="update")
        wanted = spec()
        apps = call("GET", "/apps?per_page=200").get("apps", [])
        if any(app["spec"]["name"] == wanted["name"] for app in apps):
            fail("APP_NAME_TAKEN", app_name=wanted["name"])
        project()  # fails loudly if the project is gone or the token cannot see it
        app = call("POST", "/apps", {"spec": wanted, "project_id": PROJECT_ID})["app"]
        BINDING.write_text(json.dumps({"app_name": wanted["name"], "app_id": app["id"]}, indent=2) + "\n")
        summary(app)
    elif command == "status":
        summary(bound_app())
    elif command == "update":
        app = bound_app()
        wanted = spec()
        if wanted["name"] != app["spec"]["name"]:
            fail("APP_RENAME_REFUSED", bound=app["spec"]["name"], requested=wanted["name"])
        summary(call("PUT", f"/apps/{app['id']}", {"spec": wanted})["app"])
    elif command == "deploy":
        app = bound_app()
        deployment = call("POST", f"/apps/{app['id']}/deployments", {"force_build": True})["deployment"]
        print(json.dumps({"deployment": deployment["id"], "phase": deployment.get("phase")}, indent=2))
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
