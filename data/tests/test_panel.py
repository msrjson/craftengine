"""The control panel: one shell, filtered per account.

The panel replaced an icon-only rail whose labels appeared on hover, over the
page content, with a menu hardcoded in the template. Hardcoding it made the
navigation a second, silent authorization system — which is how an ordinary
account came to be shown a Dashboard button that led straight to a 403.

Here the menu is data (`engine/support/navigation.py`), each item carries the
same guard as the route it points at, and these tests assert the two halves
agree: what a visitor can *see* and what they can *open*.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest
from craft.facades import DB, Route
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app

#: Pages any signed-in account may open — their own workspace, nothing else.
WORKSPACE_PAGES = ["/panel", "/panel/profile"]

#: Pages that manage other people, describe the installation, or expose how
#: access is configured. `/panel/access` is here because permission slugs,
#: grant paths and raw ABAC conditions are security configuration, not the
#: visitor's personal data.
ADMIN_PAGES = [
    "/panel/users",
    "/panel/access",
    "/panel/modules",
    "/panel/plugins",
    "/panel/system",
]


@pytest.fixture(scope="module", autouse=True)
def helper_routes(migrated_database):
    def token(request):
        return {"token": request.session().token()}

    def do_login(request):
        return {
            "ok": app.make("auth").attempt(
                {
                    "email": request.input("email"),
                    "password": request.input("password"),
                }
            )
        }

    Route.get("/t/panel/token", token).name("t.panel.token")
    Route.post("/t/panel/login", do_login).name("t.panel.login")
    yield


@pytest.fixture
def client():
    return TestClient(asgi_app)


@pytest.fixture
def accounts(migrated_database):
    from app.Models.Role import Role
    from app.Models.User import User

    for email in ("plain-panel@craft.local", "admin-panel@craft.local"):
        DB.statement("DELETE FROM users WHERE email = ?", [email])

    plain = User.create({"name": "Plain", "email": "plain-panel@craft.local", "password": "s3cret"})
    administrator = User.force_create(
        {
            "name": "Boss",
            "email": "admin-panel@craft.local",
            "password": "s3cret",
            "is_admin": True,
        }
    )

    role = Role.query().where("slug", "admin").first() or Role.create({"name": "Admin", "slug": "admin"})
    DB.statement(
        "INSERT INTO role_user (user_id, role_id) VALUES (:user, :role)",
        {"user": administrator.get_attribute("id"), "role": role.get_attribute("id")},
    )
    return {"plain": plain, "admin": administrator}


def login(client, email: str) -> None:
    token = client.get("/t/panel/token").json()["token"]
    client.post("/t/panel/login", data={"email": email, "password": "s3cret", "_token": token})


class TestTheWorkspaceIsForEveryone:
    """The panel is not an admin area. That was the whole complaint."""

    @pytest.mark.parametrize("path", WORKSPACE_PAGES)
    def test_an_ordinary_account_can_open_its_own_workspace(self, client, accounts, path):
        login(client, "plain-panel@craft.local")
        assert client.get(path, follow_redirects=False).status_code == 200

    @pytest.mark.parametrize("path", WORKSPACE_PAGES + ADMIN_PAGES)
    def test_a_guest_is_sent_to_login(self, client, accounts, path):
        assert client.get(path, follow_redirects=False).status_code in (302, 401, 403)

    @pytest.mark.parametrize("path", ADMIN_PAGES)
    def test_an_ordinary_account_cannot_open_the_admin_pages(self, client, accounts, path):
        login(client, "plain-panel@craft.local")
        response = client.get(path, headers={"Accept": "application/json"}, follow_redirects=False)
        assert response.status_code == 403

    @pytest.mark.parametrize("path", WORKSPACE_PAGES + ADMIN_PAGES)
    def test_an_administrator_can_open_everything(self, client, accounts, path):
        login(client, "admin-panel@craft.local")
        assert client.get(path, follow_redirects=False).status_code == 200


class TestTheSidebarShowsLabelsAndOnlyReachablePages:
    def test_the_menu_is_labelled_not_icon_only(self, client, accounts):
        """The reported problem: a rail of icons with no names."""
        login(client, "plain-panel@craft.local")
        body = client.get("/panel").text

        # Only items with no permission condition — whether this account holds
        # `create-post` depends on seeded data, and that is a different test.
        for label in ("Dashboard", "My Profile", "Workspace"):
            assert label in body, f"the sidebar does not name {label!r}"

    def test_an_ordinary_account_is_not_shown_the_admin_sections(self, client, accounts):
        login(client, "plain-panel@craft.local")
        body = client.get("/panel").text

        assert "People &amp; Access" not in body and "People & Access" not in body
        for path in ADMIN_PAGES:
            assert f'href="{path}"' not in body

    def test_an_administrator_is_shown_them(self, client, accounts):
        login(client, "admin-panel@craft.local")
        body = client.get("/panel").text

        assert "People" in body
        for path in ADMIN_PAGES:
            assert f'href="{path}"' in body

    def test_every_link_the_menu_offers_can_actually_be_opened(self, client, accounts):
        """The invariant that matters: menu and router agree.

        A link the visitor cannot open is an invitation to a 403 — exactly the
        bug this whole design exists to make impossible.
        """
        from app.Models.User import User

        nav = app.make("nav")
        for email in ("plain-panel@craft.local", "admin-panel@craft.local"):
            user = User.query().where("email", email).first()
            login(client, email)

            for section in nav.for_user(user, "/panel"):
                for item in section["items"]:
                    url = item["url"]
                    if not url.startswith("/"):
                        continue
                    # Redirects are followed: `/admin/*` links land in the
                    # panel. What must hold is that the visitor reaches a
                    # working page, never a 403.
                    status = client.get(url).status_code
                    assert status == 200, f"{email} is offered {url}, which answers {status}"


class TestOrdinaryAccountsSeeNoSecurityConfiguration:
    """Reported from a running installation, again.

    The panel's first revision gave every visitor a "My access" page listing
    permission slugs, the path each grant arrives by (`role`, `group-role`,
    `group`) and the raw ABAC conditions — plus role/group counts on the
    dashboard. All of that describes how the installation is secured. Knowing
    which roles exist and which of them you hold is a map for probing the
    system; it belongs to whoever administers access.
    """

    #: Strings that only appear when the authorization model is being described.
    LEAKS = ["group-role", "Granted via", "@user.id", "unconditional", "content-team"]

    def test_the_dashboard_does_not_describe_the_authorization_model(self, client, accounts):
        login(client, "plain-panel@craft.local")
        body = client.get("/panel").text

        for leak in self.LEAKS:
            assert leak not in body, f"the dashboard shows {leak!r} to an ordinary account"
        # Nor the counts that summarise it.
        assert "Permissions" not in body
        assert "Roles" not in body

    def test_the_profile_does_not_show_security_metadata(self, client, accounts):
        login(client, "plain-panel@craft.local")
        body = client.get("/panel/profile").text

        assert "Administrator" not in body
        assert "Account type" not in body
        assert "/panel/access" not in body

    def test_an_administrator_still_gets_the_audit(self, client, accounts):
        login(client, "admin-panel@craft.local")

        assert client.get("/panel/access").status_code == 200
        assert "Administrator" in client.get("/panel/profile").text

    def test_the_menu_never_offers_the_audit_to_an_ordinary_account(self, client, accounts):
        login(client, "plain-panel@craft.local")
        body = client.get("/panel").text
        assert "Access audit" not in body


class TestTheActiveItem:
    """Exactly one item is highlighted — the best match for the current path.

    Found by looking at the running panel, not by a test: `/panel` lit up
    alongside `/panel/access`, so the sidebar claimed the visitor was in two
    places at once. Per-item prefix matching cannot express "closest wins".
    """

    def test_a_child_page_does_not_also_light_up_its_parent(self, accounts):
        from app.Models.User import User

        nav = app.make("nav")
        user = User.query().where("email", "plain-panel@craft.local").first()

        sections = nav.for_user(user, "/panel/profile")
        active = [item["label"] for s in sections for item in s["items"] if item["active"]]
        assert active == ["My Profile"]

    def test_the_index_is_active_on_its_own_path(self, accounts):
        from app.Models.User import User

        nav = app.make("nav")
        user = User.query().where("email", "plain-panel@craft.local").first()

        sections = nav.for_user(user, "/panel")
        active = [item["label"] for s in sections for item in s["items"] if item["active"]]
        assert active == ["Dashboard"]

    def test_a_deeper_url_still_highlights_its_section(self, accounts):
        """`/panel/profile/edit` belongs to My Profile."""
        from app.Models.User import User

        nav = app.make("nav")
        user = User.query().where("email", "plain-panel@craft.local").first()

        sections = nav.for_user(user, "/panel/profile/edit")
        active = [item["label"] for s in sections for item in s["items"] if item["active"]]
        assert active == ["My Profile"]


class TestScoping:
    def test_an_ordinary_account_sees_only_its_own_profile(self, client, accounts):
        login(client, "plain-panel@craft.local")
        body = client.get("/panel/profile").text
        assert "plain-panel@craft.local" in body
        assert "admin-panel@craft.local" not in body

    def test_installation_wide_numbers_are_administrators_only(self, client, accounts):
        """Even the *size* of the system is not for an account that cannot see
        its contents."""
        login(client, "plain-panel@craft.local")
        assert "This installation" not in client.get("/panel").text

        login(client, "admin-panel@craft.local")
        assert "This installation" in client.get("/panel").text

    def test_my_access_explains_where_each_permission_comes_from(self, client, accounts):
        """The page must name the path a permission arrives by, and show the
        conditions attached to it — not merely list slugs."""
        from app.Models.Permission import Permission

        DB.statement("DELETE FROM permissions WHERE slug = 'panel-probe'")
        permission = Permission.create({"name": "Panel Probe", "slug": "panel-probe"})
        DB.statement(
            "INSERT INTO permission_user (permission_id, user_id, conditions) VALUES (:p, :u, :c)",
            {
                "p": permission.get_attribute("id"),
                "u": accounts["admin"].get_attribute("id"),
                "c": '{"user_id": "@user.id"}',
            },
        )

        try:
            login(client, "admin-panel@craft.local")
            body = client.get("/panel/access").text

            assert "Granted via" in body
            assert "panel-probe" in body
            assert "direct" in body
            # The condition itself, verbatim: "may publish" and "may publish
            # their own" are different permissions.
            assert "@user.id" in body
        finally:
            DB.statement("DELETE FROM permission_user WHERE permission_id = ?", [permission.get_attribute("id")])
            DB.statement("DELETE FROM permissions WHERE slug = 'panel-probe'")


class TestModuleToggle:
    def test_an_administrator_can_disable_and_reenable_a_module(self, client, accounts):
        from app.Models.Module import Module

        DB.statement("DELETE FROM modules WHERE slug = 'panel-test'")
        Module.create({"name": "Panel Test", "slug": "panel-test", "enabled": True})
        manager = app.make("module")
        manager.forget_cached_state("panel-test")

        try:
            login(client, "admin-panel@craft.local")
            token = client.get("/t/panel/token").json()["token"]

            client.post(
                "/panel/modules/toggle",
                data={"slug": "panel-test", "enable": "0", "_token": token},
                follow_redirects=False,
            )
            assert manager.is_enabled("panel-test") is False

            client.post(
                "/panel/modules/toggle",
                data={"slug": "panel-test", "enable": "1", "_token": token},
                follow_redirects=False,
            )
            assert manager.is_enabled("panel-test") is True
        finally:
            DB.statement("DELETE FROM modules WHERE slug = 'panel-test'")
            manager.forget_cached_state("panel-test")

    def test_an_ordinary_account_cannot_toggle_a_module(self, client, accounts):
        login(client, "plain-panel@craft.local")
        token = client.get("/t/panel/token").json()["token"]

        response = client.post(
            "/panel/modules/toggle",
            data={"slug": "inventory", "enable": "0", "_token": token},
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )
        assert response.status_code == 403
