"""Tests for `craft new`, the bare project generator."""

import os
import tomllib

import pytest

from engine.cli import project_scaffolder


class TestSkeletonTemplates:
    """The template tree itself, independent of any generated project."""

    def test_every_template_carries_the_stub_suffix(self):
        """A template without the suffix would be invisible to the generator."""
        for directory, _, filenames in os.walk(project_scaffolder.SKELETON_ROOT):
            for filename in filenames:
                assert filename.endswith(project_scaffolder.STUB_SUFFIX), os.path.join(directory, filename)

    def test_no_template_is_a_hidden_file(self):
        """Hidden templates are dropped by setuptools' package-data globs.

        A template stored as `.env.example.stub` is present in a source
        checkout and missing from an installed package, so the failure only
        reaches people who installed the framework normally. Templates whose
        generated name needs a leading dot are stored without one and renamed
        by DOTFILE_RENAMES.
        """
        for directory, _, filenames in os.walk(project_scaffolder.SKELETON_ROOT):
            for filename in filenames:
                assert not filename.startswith("."), os.path.join(directory, filename)

    def test_packaging_ships_the_templates(self):
        """`pyproject.toml` must declare the templates as package data.

        Without the declaration the command installs cleanly and then writes
        an empty project, which no test running from a source checkout can
        detect.
        """
        root = os.path.dirname(os.path.dirname(os.path.abspath(project_scaffolder.__file__)))
        with open(os.path.join(os.path.dirname(root), "pyproject.toml"), "rb") as handle:
            config = tomllib.load(handle)
        package_data = config["tool"]["setuptools"]["package-data"]
        assert any("skeleton" in pattern for pattern in package_data.get("engine.cli", []))


class TestBuildProject:
    """Generating a project into a target directory."""

    def test_generates_a_bootable_project(self, tmp_path):
        """The generated tree carries everything the application needs to boot."""
        result = project_scaffolder.build_project(str(tmp_path / "app"))
        written = result["files"]

        for required in (
            "bootstrap/app.py",
            "routes/web.py",
            "resources/views/welcome.forge.py",
            "config/app.py",
            "config/auth.py",
            "app/Providers/RouteServiceProvider.py",
            "database/seeders/DatabaseSeeder.py",
            "dev.py",
            "public/index.py",
        ):
            assert required in written, required
            assert os.path.isfile(written[required])

    def test_generates_the_environment_template(self, tmp_path):
        """`.env.example` reaches the project with its leading dot restored."""
        result = project_scaffolder.build_project(str(tmp_path / "app"))

        assert ".env.example" in result["files"]
        assert os.path.isfile(os.path.join(str(tmp_path / "app"), ".env.example"))
        assert "env.example" not in result["files"]

    def test_carries_no_application_code(self, tmp_path):
        """The point of the skeleton is that there is nothing to reuse.

        Models, controllers, a theme and an admin panel are what made agents
        graft new work onto a demo application instead of building their own.
        """
        result = project_scaffolder.build_project(str(tmp_path / "app"))
        written = result["files"]

        assert not [path for path in written if path.startswith("app/Models/") and path != "app/Models/__init__.py"]
        assert not [
            path
            for path in written
            if path.startswith("app/Http/Controllers/") and path != "app/Http/Controllers/__init__.py"
        ]
        assert not [path for path in written if path.startswith("public/assets/")]
        assert not [path for path in written if path.startswith("resources/views/layouts/")]

    def test_creates_the_runtime_directories(self, tmp_path):
        """The framework writes into these at runtime and does not create them."""
        target = str(tmp_path / "app")
        project_scaffolder.build_project(target)

        for runtime in project_scaffolder.RUNTIME_DIRECTORIES:
            assert os.path.isdir(os.path.join(target, runtime)), runtime

    def test_refuses_a_directory_that_already_holds_files(self, tmp_path):
        """Generating over an existing project would overwrite its code."""
        target = tmp_path / "app"
        target.mkdir()
        (target / "existing.py").write_text("", encoding="utf-8")

        with pytest.raises(project_scaffolder.ProjectDirectoryNotEmpty) as excinfo:
            project_scaffolder.build_project(str(target))

        assert excinfo.value.code == "PROJECT_DIRECTORY_NOT_EMPTY"

    def test_force_generates_into_a_non_empty_directory(self, tmp_path):
        """`--force` is the explicit opt-in to overwrite."""
        target = tmp_path / "app"
        target.mkdir()
        (target / "existing.py").write_text("", encoding="utf-8")

        result = project_scaffolder.build_project(str(target), force=True)

        assert "bootstrap/app.py" in result["files"]
        assert (target / "existing.py").exists()


def test_new_projects_create_the_tables_the_engine_writes_to(tmp_path):
    """Security services and the catch-up scheduler need their tables from day one."""
    import os

    from craft.cli import project_scaffolder

    project_scaffolder.build_project(str(tmp_path / "app"))
    migrations = os.listdir(tmp_path / "app" / "database" / "migrations")
    assert any(name.endswith("_create_security_tables.py") for name in migrations)
    assert any(name.endswith("_create_scheduler_runs_table.py") for name in migrations)
