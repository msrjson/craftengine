"""Tests for `craft make:admin`, the RBAC admin panel generator."""

import os
import tomllib

import pytest

from engine.cli import admin_scaffolder


def _bare_project(root) -> str:
    """Create the minimum a generated project offers this command.

    Args:
        root: A `tmp_path` directory to build inside.

    Returns:
        The project root, as a string path.
    """
    base = root / "project"
    (base / "routes").mkdir(parents=True)
    (base / "config").mkdir(parents=True)
    (base / "routes" / "web.py").write_text(
        '"""Web routes."""\n\nfrom craft.facades import Route\n', encoding="utf-8"
    )
    (base / "config" / "auth.py").write_text(
        '"""Authentication configuration."""\n\n'
        "models = {\n"
        '    "user": "app.Models.User.User",\n'
        '    "role": "",\n'
        '    "permission": "",\n'
        '    "group": "",\n'
        "}\n",
        encoding="utf-8",
    )
    return str(base)


class TestAdminTemplates:
    """The template tree itself, independent of any generated project."""

    def test_every_template_carries_the_stub_suffix(self):
        """A template without the suffix would be invisible to the generator."""
        for directory, _, filenames in os.walk(admin_scaffolder.ADMIN_TEMPLATE_ROOT):
            for filename in filenames:
                assert filename.endswith(admin_scaffolder.STUB_SUFFIX), os.path.join(directory, filename)

    def test_no_template_is_a_hidden_file(self):
        """Hidden templates are dropped by setuptools' package-data globs."""
        for directory, _, filenames in os.walk(admin_scaffolder.ADMIN_TEMPLATE_ROOT):
            for filename in filenames:
                assert not filename.startswith("."), os.path.join(directory, filename)

    def test_packaging_ships_the_templates(self):
        """Without the declaration the command generates nothing once installed."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(admin_scaffolder.__file__)))
        with open(os.path.join(os.path.dirname(root), "pyproject.toml"), "rb") as handle:
            config = tomllib.load(handle)
        package_data = config["tool"]["setuptools"]["package-data"]
        assert any("admin_templates" in pattern for pattern in package_data.get("engine.cli", []))


class TestGeneratedFiles:
    """What lands in the project."""

    def test_generates_controllers_models_views_and_migration(self, tmp_path):
        """Every part of the panel reaches the project in one run."""
        base = _bare_project(tmp_path)

        written = admin_scaffolder.build_admin(base)["files"]

        for required in (
            "app/Http/Controllers/Admin/HomeController.py",
            "app/Http/Controllers/Admin/RoleController.py",
            "app/Http/Controllers/Admin/GroupController.py",
            "app/Http/Controllers/Admin/CrudBuilderController.py",
            "app/Http/Controllers/Panel/PanelPage.py",
            "app/Http/Requests/CrudBuilderRequest.py",
            "app/Models/Role.py",
            "app/Models/Permission.py",
            "app/Models/Group.py",
            "resources/views/admin/roles/index.forge.py",
            "resources/views/admin/permissions/index.forge.py",
            "resources/views/admin/groups/index.forge.py",
            "resources/views/admin/crud_builder/index.forge.py",
            "resources/views/admin/crud_builder/result.forge.py",
            "database/migrations/2026_09_23_000001_create_rbac_tables.py",
        ):
            assert required in written, required
            assert os.path.isfile(written[required])

    def test_role_controller_exports_both_controllers(self, tmp_path):
        """The routes import `PermissionController` from the same module."""
        base = _bare_project(tmp_path)

        written = admin_scaffolder.build_admin(base)["files"]
        source = open(written["app/Http/Controllers/Admin/RoleController.py"], encoding="utf-8").read()

        assert "class RoleController" in source
        assert "class PermissionController" in source

    def test_migration_creates_every_rbac_table(self, tmp_path):
        """One migration, carrying the tables the panel and the engine read."""
        base = _bare_project(tmp_path)

        written = admin_scaffolder.build_admin(base)["files"]
        source = open(written["database/migrations/2026_09_23_000001_create_rbac_tables.py"], encoding="utf-8").read()

        for table in (
            "roles",
            "permissions",
            "role_user",
            "permission_role",
            "groups",
            "group_user",
            "group_role",
            "permission_group",
            "permission_user",
        ):
            assert f'create_table("{table}"' in source, table

    def test_migration_carries_no_unrelated_table(self, tmp_path):
        """Translations and settings belong to the framework migration, not here."""
        base = _bare_project(tmp_path)

        written = admin_scaffolder.build_admin(base)["files"]
        source = open(written["database/migrations/2026_09_23_000001_create_rbac_tables.py"], encoding="utf-8").read()

        assert 'create_table("translations"' not in source
        assert 'create_table("settings"' not in source
        assert 'create_table("modules"' not in source

    def test_writes_package_markers(self, tmp_path):
        """Generated packages without `__init__.py` cannot be imported."""
        base = _bare_project(tmp_path)

        admin_scaffolder.build_admin(base)

        for package in admin_scaffolder.PACKAGE_DIRECTORIES:
            assert os.path.isfile(os.path.join(base, package, "__init__.py")), package


class TestRouteRegistration:
    """Appending to a file the project owns."""

    def test_registers_the_admin_routes(self, tmp_path):
        """Each screen gets a named route behind `auth` and `role:admin`."""
        base = _bare_project(tmp_path)

        admin_scaffolder.build_admin(base)
        content = open(os.path.join(base, "routes", "web.py"), encoding="utf-8").read()

        for name in (
            "admin.dashboard",
            "admin.roles.index",
            "admin.roles.grant",
            "admin.permissions.index",
            "admin.groups.index",
            "admin.crud_builder.index",
        ):
            assert f'.name("{name}")' in content or f'"{name}"' in content, name
        assert content.count('middleware("auth", "role:admin")') >= 6

    def test_preserves_existing_route_declarations(self, tmp_path):
        """Registration is append-only: nothing already in the file is rewritten."""
        base = _bare_project(tmp_path)
        routes_path = os.path.join(base, "routes", "web.py")
        with open(routes_path, "a", encoding="utf-8") as handle:
            handle.write('\nRoute.get("/", welcome).name("home")\n')

        admin_scaffolder.build_admin(base)
        content = open(routes_path, encoding="utf-8").read()

        assert 'Route.get("/", welcome).name("home")' in content

    def test_does_not_duplicate_routes_on_a_second_run(self, tmp_path):
        """Running the command twice must not register the panel twice."""
        base = _bare_project(tmp_path)
        routes_path = os.path.join(base, "routes", "web.py")

        admin_scaffolder.build_admin(base)
        first = open(routes_path, encoding="utf-8").read()
        result = admin_scaffolder.build_admin(base)
        second = open(routes_path, encoding="utf-8").read()

        assert result["already_configured"] is True
        assert first == second
        assert second.count(admin_scaffolder.ROUTES_TOKEN) == 1
        assert second.count(admin_scaffolder.ROUTE_IMPORTS[0]) == 1

    def test_creates_the_routes_file_when_absent(self, tmp_path):
        """A project without a route file still gets a registered panel."""
        base = str(tmp_path / "empty")
        os.makedirs(base)

        admin_scaffolder.build_admin(base)
        content = open(os.path.join(base, "routes", "web.py"), encoding="utf-8").read()

        assert admin_scaffolder.ROUTES_TOKEN in content
        assert "from craft.facades import Route" in content


class TestIdentityModelConfiguration:
    """`config/auth.py` is where the engine resolves the models from."""

    def test_fills_the_empty_model_entries(self, tmp_path):
        """The engine imports nothing directly; unset entries disable the commands."""
        base = _bare_project(tmp_path)

        admin_scaffolder.build_admin(base)
        content = open(os.path.join(base, "config", "auth.py"), encoding="utf-8").read()

        assert '"role": "app.Models.Role.Role"' in content
        assert '"permission": "app.Models.Permission.Permission"' in content
        assert '"group": "app.Models.Group.Group"' in content

    def test_preserves_a_model_the_project_already_named(self, tmp_path):
        """A project that renamed its own class keeps it."""
        base = _bare_project(tmp_path)
        config_path = os.path.join(base, "config", "auth.py")
        content = open(config_path, encoding="utf-8").read()
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write(content.replace('"role": ""', '"role": "app.Models.Team.Team"'))

        admin_scaffolder.build_admin(base)
        updated = open(config_path, encoding="utf-8").read()

        assert '"role": "app.Models.Team.Team"' in updated
        assert "app.Models.Role.Role" not in updated

    def test_appends_a_models_block_when_the_file_has_none(self, tmp_path):
        """An older configuration file predates the registry and has no mapping."""
        base = _bare_project(tmp_path)
        config_path = os.path.join(base, "config", "auth.py")
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write('"""Authentication configuration."""\n\ndefaults = {"guard": "web"}\n')

        admin_scaffolder.build_admin(base)
        updated = open(config_path, encoding="utf-8").read()

        assert "models = {" in updated
        assert '"group": "app.Models.Group.Group"' in updated

    def test_survives_a_project_without_the_configuration_file(self, tmp_path):
        """Generation must not fail on a project laid out differently."""
        base = str(tmp_path / "no-config")
        os.makedirs(base)

        result = admin_scaffolder.build_admin(base)

        assert "config/auth.py" not in result["files"]


class TestOverwriteGuard:
    """Existing files are never replaced silently."""

    def test_refuses_to_overwrite_an_existing_file(self, tmp_path):
        """A half-generated panel must not be clobbered without consent."""
        base = _bare_project(tmp_path)
        target = os.path.join(base, "app", "Models", "Role.py")
        os.makedirs(os.path.dirname(target))
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("")

        with pytest.raises(FileExistsError):
            admin_scaffolder.build_admin(base)

    def test_force_overwrites(self, tmp_path):
        """`--force` is the explicit opt-in."""
        base = _bare_project(tmp_path)
        target = os.path.join(base, "app", "Models", "Role.py")
        os.makedirs(os.path.dirname(target))
        with open(target, "w", encoding="utf-8") as handle:
            handle.write("")

        result = admin_scaffolder.build_admin(base, force=True)

        assert result["already_configured"] is False
        assert os.path.getsize(target) > 0
