"""Tests for make:auth and agent:scaffold CLI commands and scaffolders."""

import os

import pytest

from engine.cli import agent_scaffolder, auth_scaffolder


class TestAuthScaffolder:
    def test_build_auth_creates_all_files(self, tmp_path):
        base_dir = str(tmp_path)
        routes_dir = os.path.join(base_dir, "routes")
        os.makedirs(routes_dir, exist_ok=True)
        with open(os.path.join(routes_dir, "web.py"), "w", encoding="utf-8") as f:
            f.write("# Routes\n")

        result = auth_scaffolder.build_auth(base_dir)
        files = result["files"]

        assert os.path.exists(files["view_login"])
        assert os.path.exists(files["view_register"])
        assert os.path.exists(files["view_dashboard"])
        assert os.path.exists(files["request_login"])
        assert os.path.exists(files["request_register"])
        assert os.path.exists(files["controller"])
        assert os.path.exists(files["routes"])

        # Check content includes validation & anti-spam directives
        with open(files["view_login"], "r", encoding="utf-8") as f:
            content = f.read()
            assert "@honeypot" in content
            assert "@error('email')" in content
            assert "@csrf" in content

    def test_build_auth_views_only(self, tmp_path):
        base_dir = str(tmp_path)
        result = auth_scaffolder.build_auth(base_dir, views_only=True)
        files = result["files"]

        assert "view_login" in files
        assert "view_register" in files
        assert "view_dashboard" in files
        assert "controller" not in files
        assert "request_login" not in files

    def test_build_auth_refuses_overwrite_without_force(self, tmp_path):
        base_dir = str(tmp_path)
        auth_scaffolder.build_auth(base_dir)

        with pytest.raises(FileExistsError):
            auth_scaffolder.build_auth(base_dir, force=False)

        # Works with force=True
        result = auth_scaffolder.build_auth(base_dir, force=True)
        assert len(result["files"]) > 0

    def test_register_auth_routes_idempotency(self, tmp_path):
        base_dir = str(tmp_path)
        routes_dir = os.path.join(base_dir, "routes")
        os.makedirs(routes_dir, exist_ok=True)
        web_file = os.path.join(routes_dir, "web.py")
        with open(web_file, "w", encoding="utf-8") as f:
            f.write("# Existing routes\n")

        auth_scaffolder.register_auth_routes(base_dir)
        with open(web_file, "r", encoding="utf-8") as f:
            content_after_first = f.read()
        assert "/login" in content_after_first

        # Second run does not duplicate routes
        auth_scaffolder.register_auth_routes(base_dir)
        with open(web_file, "r", encoding="utf-8") as f:
            content_after_second = f.read()
        assert content_after_first == content_after_second


class TestAgentScaffolder:
    def test_scaffold_agent_stack_creates_expected_artifacts(self, tmp_path):
        base_dir = str(tmp_path)
        result = agent_scaffolder.scaffold_agent_stack(base_dir)
        files = result["files"]

        assert os.path.exists(files["cursorrules"])
        assert os.path.exists(files["llms_root"])
        assert os.path.exists(files["llms_docs"])
        assert os.path.exists(files["llms_full_root"])
        assert os.path.exists(files["llms_full_docs"])
        assert os.path.exists(files["mcp"])
        assert os.path.exists(files["agents_md"])
        assert os.path.exists(files["agents_pointer"])
        assert os.path.exists(os.path.join(base_dir, ".claude", "agents", "code-reviewer.md"))
        assert len(result["catalog"]["skill"]) > 0

        with open(files["cursorrules"], "r", encoding="utf-8") as f:
            rules = f.read()
            assert "Craft Engine" in rules
            assert "Absolute Data Persistence" in rules
            assert "Validator.make" in rules

        with open(files["llms_root"], "r", encoding="utf-8") as f:
            llms = f.read()
            assert "# Craft Engine" in llms
            assert "python dev.py make:auth" in llms

    def test_scaffold_agent_refuses_overwrite_without_force(self, tmp_path):
        base_dir = str(tmp_path)
        agent_scaffolder.scaffold_agent_stack(base_dir)

        with pytest.raises(FileExistsError):
            agent_scaffolder.scaffold_agent_stack(base_dir, force=False)

        # Overwrite with force=True
        result = agent_scaffolder.scaffold_agent_stack(base_dir, force=True)
        assert len(result["files"]) > 0
