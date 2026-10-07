"""Tests for the installable agent catalog and its `dev.py agent:*` commands."""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from engine.cli import agent_catalog
from engine.cli.app import cli

EXPECTED_AGENTS = {"code-reviewer", "security-auditor", "test-engineer", "web-performance-auditor"}
EXPECTED_COMMANDS = {
    "build", "code-simplify", "constraints", "plan-tasks", "review-change", "ship", "spec", "test", "webperf",
}
EXPECTED_SKILLS = {
    "api-and-interface-design", "browser-testing-with-devtools", "ci-cd-and-automation",
    "code-review-and-quality", "code-simplification", "constraint-driven-development",
    "context-engineering", "craft-engine-pitfalls", "debugging-and-error-recovery", "deprecation-and-migration",
    "documentation-and-adrs", "doubt-driven-development", "frontend-ui-engineering",
    "git-workflow-and-versioning", "idea-refine", "incremental-implementation", "interview-me",
    "observability-and-instrumentation", "performance-optimization", "planning-and-task-breakdown",
    "security-and-hardening", "shipping-and-launch", "source-driven-development",
    "spec-driven-development", "test-driven-development", "tests-in-container", "using-agent-catalog",
}
FORBIDDEN_NAMES = ("laravel", "eloquent", "blade", "artisan", "illuminate", "django", "symfony", "jest", "vitest")


def _names(kind: str) -> set[str]:
    return {entry.name for entry in agent_catalog.list_entries(kind)}


class TestCatalogContent:
    def test_catalog_ships_every_agent_skill_and_command(self):
        assert _names("agent") == EXPECTED_AGENTS
        assert _names("skill") == EXPECTED_SKILLS
        assert _names("command") == EXPECTED_COMMANDS

    def test_every_agent_skill_and_command_declares_a_description(self):
        missing = [e.name for e in agent_catalog.list_entries() if e.kind != "reference" and not e.description]
        assert missing == []

    def test_skill_and_agent_frontmatter_name_matches_entry_name(self):
        for entry in agent_catalog.list_entries():
            if entry.kind not in {"agent", "skill"}:
                continue
            manifest = entry.source / "SKILL.md" if entry.kind == "skill" else entry.source
            assert f"\nname: {entry.name}\n" in manifest.read_text(encoding="utf-8")

    def test_catalog_never_names_third_party_web_frameworks(self):
        offenders = []
        for path in agent_catalog.CATALOG_ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            offenders += [f"{path.name}:{word}" for word in FORBIDDEN_NAMES if f" {word} " in f" {text} "]
        assert offenders == []

    def test_unknown_kind_is_rejected(self):
        with pytest.raises(ValueError):
            agent_catalog.list_entries("persona")


class TestCatalogInstall:
    def test_install_by_name_copies_entry_and_shared_references(self, tmp_path):
        installed = agent_catalog.install(str(tmp_path), ["code-reviewer", "test-driven-development"])

        assert (tmp_path / ".agents" / "agents" / "code-reviewer.md").is_file()
        assert (tmp_path / ".agents" / "skills" / "test-driven-development" / "SKILL.md").is_file()
        assert len(installed["agent"]) == 1 and len(installed["skill"]) == 1
        assert len(installed["reference"]) == len(agent_catalog.list_entries("reference"))

    def test_install_all_copies_the_whole_catalog(self, tmp_path):
        installed = agent_catalog.install(str(tmp_path))

        assert {Path(p).stem for p in installed["command"]} == EXPECTED_COMMANDS
        assert {Path(p).name for p in installed["skill"]} == EXPECTED_SKILLS

    def test_install_keeps_claude_as_a_symlink_to_the_single_directory(self, tmp_path):
        agent_catalog.install(str(tmp_path), ["ship"])

        link = tmp_path / ".claude"
        assert link.is_symlink()
        assert os.readlink(link) == ".agents"
        assert (link / "commands" / "ship.md").is_file()

    def test_a_legacy_physical_claude_directory_is_refused(self, tmp_path):
        legacy = tmp_path / ".claude"
        (legacy / "rules").mkdir(parents=True)
        (legacy / "rules" / "AGENTS.md").write_text("legacy layout", encoding="utf-8")

        with pytest.raises(agent_catalog.LegacyAgentDirectoryError):
            agent_catalog.install(str(tmp_path), ["ship"])

        assert not (tmp_path / ".agents").exists()
        assert (legacy / "rules" / "AGENTS.md").read_text(encoding="utf-8") == "legacy layout"

    def test_unknown_name_is_rejected_before_writing(self, tmp_path):
        with pytest.raises(agent_catalog.UnknownCatalogEntryError) as exc:
            agent_catalog.install(str(tmp_path), ["code-reviewer", "no-such-agent"])

        assert exc.value.names == ["no-such-agent"]
        assert not (tmp_path / ".agents").exists()

    def test_existing_entry_requires_force(self, tmp_path):
        agent_catalog.install(str(tmp_path), ["ship"])
        target = tmp_path / ".agents" / "commands" / "ship.md"
        target.write_text("local edit", encoding="utf-8")

        with pytest.raises(FileExistsError):
            agent_catalog.install(str(tmp_path), ["ship"])
        assert target.read_text(encoding="utf-8") == "local edit"

        agent_catalog.install(str(tmp_path), ["ship"], force=True)
        assert target.read_text(encoding="utf-8") != "local edit"


class TestAgentCommands:
    def test_agent_list_prints_catalog(self):
        result = CliRunner().invoke(cli, ["agent", "list", "--kind", "agent"])

        assert result.exit_code == 0
        assert all(name in result.output for name in EXPECTED_AGENTS)

    def test_agent_install_requires_names_or_all(self, tmp_path, monkeypatch):
        monkeypatch.setattr("engine.cli.app.base_path", lambda: str(tmp_path))

        assert CliRunner().invoke(cli, ["agent", "install"]).exit_code == 1
        result = CliRunner().invoke(cli, ["agent", "install", "security-auditor"])
        assert result.exit_code == 0
        assert (tmp_path / ".agents" / "agents" / "security-auditor.md").is_file()
