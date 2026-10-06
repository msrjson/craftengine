"""Generated application agents must keep product features out of the engine."""

import subprocess
import sys
import json
from pathlib import Path

import pytest

from engine.cli.project_scaffolder import AGENT_LINKS, build_project


def _git(root: Path, *args: str) -> str:
    """Run Git only in the isolated generated test project."""
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, str]:
    """A generated application with a committed, reviewable starting point."""
    root = tmp_path / "commercial_app"
    build_project(str(root))
    _git(root, "init")
    _git(root, "config", "user.name", "Test Agent")
    _git(root, "config", "user.email", "agent@example.invalid")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "chore: initialize test application")
    return root, _git(root, "rev-parse", "HEAD")


def _check(root: Path, base: str) -> subprocess.CompletedProcess[str]:
    """Exercise the shipped script through its public CLI."""
    return subprocess.run(
        [sys.executable, str(root / "tools" / "check_engine_changes.py"), "--base", base],
        capture_output=True, text=True,
    )


def test_generated_tools_share_one_instruction_source(project: tuple[Path, str]) -> None:
    """Every supported tool reads the same application boundary instructions."""
    root, base = project
    for name in AGENT_LINKS:
        assert (root / name).is_symlink()
        assert (root / name).resolve() == root / "AGENTS.md"
    assert _check(root, base).returncode == 0


def test_normal_product_feature_passes_the_boundary_guard(project: tuple[Path, str]) -> None:
    """Application code may evolve, including staged and committed additions."""
    root, base = project
    module = root / "app" / "modules" / "orders"
    module.mkdir()
    (module / "provider.py").write_text("def register(context):\n    pass\n")
    _git(root, "add", "app")
    _git(root, "commit", "-m", "feat: add order module")
    assert _check(root, base).returncode == 0


@pytest.mark.parametrize("committed", [False, True])
def test_local_engine_copy_is_refused_even_when_already_committed(project: tuple[Path, str], committed: bool) -> None:
    """Committing an engine edit cannot erase the task's original comparison."""
    root, base = project
    (root / "engine").mkdir()
    (root / "engine" / "feature.py").write_text("PRODUCT_FEATURE = True\n")
    if committed:
        _git(root, "add", "engine")
        _git(root, "commit", "-m", "test: attempt local engine copy")
    result = _check(root, base)
    assert result.returncode == 1
    assert "APPLICATION_ENGINE_CHANGE_FORBIDDEN engine/" in result.stdout


def test_ignored_local_engine_copy_is_also_refused(project: tuple[Path, str]) -> None:
    """A package-mode project cannot hide a local engine with Git ignore rules."""
    root, base = project
    (root / ".gitignore").write_text("engine/\n")
    (root / "engine").mkdir()
    assert _check(root, base).returncode == 1


@pytest.mark.parametrize("path", ["craft-engine.lock", "AGENTS.md", "CLAUDE.md"])
def test_engine_lock_and_governance_changes_require_separate_review(project: tuple[Path, str], path: str) -> None:
    """A feature cannot move its engine pin or change the instructions it follows."""
    root, base = project
    with (root / path).open("a") as handle:
        handle.write("\nCHANGED_FOR_TEST\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "test: attempt protected change")
    assert _check(root, base).returncode == 1


def test_missing_baseline_fails_closed(project: tuple[Path, str]) -> None:
    """The guard never guesses a replacement comparison commit."""
    root, _ = project
    result = _check(root, "missing-baseline")
    assert result.returncode == 2
    assert "APPLICATION_ENGINE_CHECK_UNAVAILABLE" in result.stdout


@pytest.mark.parametrize("committed", [False, True])
def test_existing_vendored_engine_uses_the_recorded_baseline(project: tuple[Path, str], committed: bool) -> None:
    """An unchanged vendored engine passes; changes remain visible after a commit."""
    root, _ = project
    lock_file = root / "craft-engine.lock"
    lock = json.loads(lock_file.read_text())
    lock.update(mode="vendored", engine_path="vendor/framework")
    lock_file.write_text(json.dumps(lock))
    directory = root / "vendor" / "framework"
    directory.mkdir(parents=True)
    source = directory / "core.py"
    source.write_text("VERSION = 1\n")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "chore: establish reviewed vendored baseline")
    base = _git(root, "rev-parse", "HEAD")
    assert _check(root, base).returncode == 0
    source.write_text("VERSION = 2\n")
    if committed:
        _git(root, "add", ".")
        _git(root, "commit", "-m", "test: attempt vendored edit")
    assert _check(root, base).returncode == 1


def test_invalid_baseline_lock_shape_fails_closed(project: tuple[Path, str]) -> None:
    """Missing lock structure is an unavailable check, never a successful result."""
    root, _ = project
    (root / "craft-engine.lock").write_text("[]")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "test: establish invalid lock baseline")
    result = _check(root, _git(root, "rev-parse", "HEAD"))
    assert result.returncode == 2


def test_force_generation_preserves_existing_tool_instructions(tmp_path: Path) -> None:
    """Explicitly regenerating a project does not overwrite an existing tool file."""
    root = tmp_path / "existing_app"
    root.mkdir()
    existing = root / "CLAUDE.md"
    existing.write_text("EXISTING_OWNER_RULE\n")
    build_project(str(root), force=True)
    assert existing.read_text() == "EXISTING_OWNER_RULE\n"
    assert not existing.is_symlink()
