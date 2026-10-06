"""Tests for the engine lifecycle: lock, status, patch, hotfix, update and upgrade (ADR 0005).

Releases are real `tar.gz` archives laid out like the canonical repository's
tag archives and read through `file://` URLs, so the download, extraction,
planning and swap paths all run for real, without the network.
"""

from __future__ import annotations

import io
import json
import shlex
import sys
import tarfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from engine.lifecycle import EngineLifecycle, EngineLifecycleError, Source
from engine.lifecycle.lock import LOCK_FILE, load_lock
from engine.lifecycle.release import find_version, newest_patch, parse_ref, releases_from_tags
from engine.lifecycle.source import read_url

BASE_FILES = {"__init__.py": "version = 1\n", "http/response.py": "response = 1\n", "orm/model.py": "model = 1\n"}

CHANGELOG = """# Changelog

## [Unreleased]

## [4.5.0] r00026 - 2026-10-08

### Removed

- **Legacy helper**: gone.

### Added

- Something new.

## [4.4.3] r00025 - 2026-10-07

### Security

- **Response header fix**.

## [4.4.2] r00024 - 2026-10-06

### Fixed

- Older entry.
"""


class Releases:
    """A local stand-in for the canonical repository: tag archives plus a tag listing."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.tags: list[str] = []
        (self.root / "tags.json").write_text("[]", encoding="utf-8")

    @property
    def source(self) -> Source:
        """Return a source that reads this directory."""
        return Source(f"file://{self.root}/{{ref}}.tar.gz", f"file://{self.root}/tags.json", "data")

    def publish(self, ref: str, files: dict[str, str], *, tag: bool = True) -> None:
        """Write the archive of `ref` with `files` in the archived engine directory, and list it as a tag."""
        with tarfile.open(self.root / f"{ref}.tar.gz", "w:gz") as bundle:
            entries = {f"data/engine/{path}": text for path, text in files.items()}
            entries["data/CHANGELOG.md"] = CHANGELOG
            entries["data/app/unrelated.py"] = "ignored = True\n"
            for name, text in entries.items():
                payload = text.encode("utf-8")
                member = tarfile.TarInfo(f"craftengine-{ref.lstrip('v')}/{name}")
                member.size = len(payload)
                bundle.addfile(member, io.BytesIO(payload))
        if tag:
            self.tags.append(ref)
            (self.root / "tags.json").write_text(json.dumps([{"name": name} for name in self.tags]), encoding="utf-8")


@pytest.fixture
def releases(tmp_path: Path) -> Releases:
    """Three published releases: 4.4.2, a 4.4.3 security fix and 4.5.0."""
    repository = Releases(tmp_path / "releases")
    repository.publish("v4.4.2-r00024", BASE_FILES)
    repository.publish("v4.4.3-r00025", {**BASE_FILES, "http/response.py": "response = 2\n"})
    repository.publish("v4.5.0-r00026", {**BASE_FILES, "http/response.py": "response = 2\n", "orm/model.py": "model = 3\n"})
    return repository


def vendored_project(root: Path, releases: Releases, files: dict[str, str] = BASE_FILES) -> EngineLifecycle:
    """Create a project with a vendored engine and adopt v4.4.2."""
    for path, text in files.items():
        (root / "engine" / path).parent.mkdir(parents=True, exist_ok=True)
        (root / "engine" / path).write_text(text, encoding="utf-8")
    lifecycle = EngineLifecycle(root, ("4.4.2", "r00024"))
    lifecycle.adopt("v4.4.2-r00024", "vendored", source=releases.source)
    return lifecycle


def python_command(code: str) -> str:
    """Return a verification command line that runs `code` with this interpreter."""
    return shlex.join([sys.executable, "-c", code])


def engine_text(root: Path, path: str) -> str:
    """Return a vendored engine file's content."""
    return (root / "engine" / path).read_text(encoding="utf-8")


def refusal(action: object) -> str:
    """Return the refusal code `action()` raises."""
    with pytest.raises(EngineLifecycleError) as refused:
        action()  # type: ignore[operator]
    return refused.value.code


class TestReleaseIdentity:
    """Release tags, ordering and target selection."""

    def test_parses_the_nr01_tag_format_and_ignores_other_tags(self) -> None:
        assert parse_ref("v4.4.2-r00024").version == (4, 4, 2)
        assert parse_ref("4.4.2") is None
        assert [r.ref for r in releases_from_tags(["v4.5.0-r00026", "latest", "v4.4.2-r00024"])] == [
            "v4.4.2-r00024",
            "v4.5.0-r00026",
        ]

    def test_update_target_stays_on_the_same_minor_line(self) -> None:
        releases = releases_from_tags(["v4.4.2-r00024", "v4.4.3-r00025", "v4.5.0-r00026"])
        assert newest_patch(releases[0], releases).ref == "v4.4.3-r00025"
        assert newest_patch(releases[1], releases) is None

    def test_find_version_refuses_an_unpublished_version(self) -> None:
        releases = releases_from_tags(["v4.4.2-r00024"])
        assert refusal(lambda: find_version(releases, (9, 9, 9))) == "ENGINE_RELEASE_NOT_FOUND"


class TestAdoptAndStatus:
    """The lock, and what status reads from it."""

    def test_package_adoption_needs_no_network(self, tmp_path: Path) -> None:
        lock = EngineLifecycle(tmp_path, ("4.4.2", "r00024")).adopt("v4.4.2-r00024", "package")
        assert (lock.version, lock.release, lock.manifest) == ("4.4.2", "r00024", {})
        assert load_lock(tmp_path).ref == "v4.4.2-r00024"

    def test_adoption_refuses_an_existing_lock_a_bad_ref_and_a_bad_mode(self, tmp_path: Path) -> None:
        lifecycle = EngineLifecycle(tmp_path, ("4.4.2", "r00024"))
        assert refusal(lambda: lifecycle.adopt("main", "package")) == "ENGINE_REF_INVALID"
        assert refusal(lambda: lifecycle.adopt("v4.4.2-r00024", "copied")) == "ENGINE_MODE_INVALID"
        lifecycle.adopt("v4.4.2-r00024", "package")
        assert refusal(lambda: lifecycle.adopt("v4.4.2-r00024", "package")) == "ENGINE_LOCK_EXISTS"

    def test_vendored_adoption_records_the_release_manifest_not_the_local_tree(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases, {**BASE_FILES, "orm/model.py": "local edit\n"})
        assert sorted(load_lock(tmp_path).manifest) == sorted(BASE_FILES)
        assert lifecycle.status(check_remote=False).drift.modified == ["orm/model.py"]

    def test_status_reports_newer_releases(self, tmp_path: Path, releases: Releases) -> None:
        report = vendored_project(tmp_path, releases).status()
        assert (report.update.ref, report.newest.ref, bool(report.drift)) == ("v4.4.3-r00025", "v4.5.0-r00026", False)

    def test_status_reports_an_unreachable_source_instead_of_failing(self, tmp_path: Path) -> None:
        lifecycle = EngineLifecycle(tmp_path, ("4.4.2", "r00024"))
        lifecycle.adopt("v4.4.2-r00024", "package", source=Source(tags_url=f"file://{tmp_path}/absent.json"))
        assert lifecycle.status().remote_error == "ENGINE_SOURCE_UNREACHABLE"

    def test_only_https_and_file_sources_are_read(self) -> None:
        assert refusal(lambda: read_url("http://example.com/tags.json")) == "ENGINE_SOURCE_SCHEME_REFUSED"

    def test_a_corrupt_lock_is_refused(self, tmp_path: Path) -> None:
        (tmp_path / LOCK_FILE).write_text(json.dumps({"schema": 1, "mode": "copied"}), encoding="utf-8")
        assert refusal(lambda: load_lock(tmp_path)) == "ENGINE_LOCK_INVALID"


class TestPatches:
    """Registering local changes of a vendored engine."""

    def test_recording_a_patch_clears_the_drift(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        (tmp_path / "engine/orm/model.py").write_text("patched\n", encoding="utf-8")
        patch = lifecycle.record_patch(["engine/orm/model.py"], "SP-1", "improvement", "faster", "tester")
        assert list(patch.files) == ["orm/model.py"]
        assert not lifecycle.status(check_remote=False).drift

    def test_patch_refusals(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        assert refusal(lambda: lifecycle.record_patch(["orm/model.py"], "P", "cosmetic", "r", "t")) == "ENGINE_PATCH_CLASS_INVALID"
        assert refusal(lambda: lifecycle.record_patch(["orm/model.py"], "P", "security", "r", "t")) == "ENGINE_PATCH_EMPTY"
        (tmp_path / "engine/orm/model.py").write_text("patched\n", encoding="utf-8")
        lifecycle.record_patch(["orm/model.py"], "P", "security", "r", "t")
        assert refusal(lambda: lifecycle.record_patch(["orm/model.py"], "P", "security", "r", "t")) == "ENGINE_PATCH_EXISTS"

    def test_a_package_project_has_no_vendored_files_to_patch(self, tmp_path: Path) -> None:
        lifecycle = EngineLifecycle(tmp_path, ("4.4.2", "r00024"))
        lifecycle.adopt("v4.4.2-r00024", "package")
        assert refusal(lambda: lifecycle.record_patch(["x.py"], "P", "security", "r", "t")) == "ENGINE_NOT_VENDORED"

    def test_a_deleted_file_can_be_registered(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        (tmp_path / "engine/orm/model.py").unlink()
        assert lifecycle.record_patch(["orm/model.py"], "P", "improvement", "r", "t").files == {"orm/model.py": None}
        assert not lifecycle.status(check_remote=False).drift


class TestHotfix:
    """Taking a fix from a canonical ref without moving the pin."""

    def test_hotfix_takes_the_file_and_keeps_the_pin(self, tmp_path: Path, releases: Releases) -> None:
        releases.publish("abc123", {**BASE_FILES, "http/response.py": "response = fixed\n"}, tag=False)
        lifecycle = vendored_project(tmp_path, releases)
        patch = lifecycle.hotfix("abc123", ["http/response.py"], "GHSA-1", "header injection", "tester")
        assert (patch.patch_class, patch.source_ref) == ("security", "abc123")
        assert engine_text(tmp_path, "http/response.py") == "response = fixed\n"
        assert load_lock(tmp_path).ref == "v4.4.2-r00024"
        assert not lifecycle.status(check_remote=False).drift

    def test_hotfix_never_overwrites_unregistered_local_edits(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases, {**BASE_FILES, "http/response.py": "local\n"})
        assert refusal(lambda: lifecycle.hotfix("v4.4.3-r00025", ["http/response.py"], "H", "r", "t")) == "ENGINE_DRIFT_UNREGISTERED"
        assert engine_text(tmp_path, "http/response.py") == "local\n"

    def test_hotfix_refuses_a_missing_or_unchanged_file(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        assert refusal(lambda: lifecycle.hotfix("v4.4.3-r00025", ["absent.py"], "H", "r", "t")) == "ENGINE_HOTFIX_PATH_MISSING"
        assert refusal(lambda: lifecycle.hotfix("v4.4.3-r00025", ["orm/model.py"], "H", "r", "t")) == "ENGINE_HOTFIX_NO_CHANGE"


class TestVendoredMoves:
    """Update and upgrade of a vendored engine."""

    def test_update_moves_to_the_newest_patch_release_and_reports_notes(self, tmp_path: Path, releases: Releases) -> None:
        report = vendored_project(tmp_path, releases).update()
        assert (report.applied, report.target.ref) == (True, "v4.4.3-r00025")
        assert engine_text(tmp_path, "http/response.py") == "response = 2\n"
        assert load_lock(tmp_path).ref == "v4.4.3-r00025"
        assert [section.version for section in report.notes] == [(4, 4, 3)]
        assert not (tmp_path / ".engine.previous").exists() and not (tmp_path / ".engine.incoming").exists()

    def test_update_refuses_when_already_on_the_newest_patch(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        lifecycle.update()
        assert refusal(lifecycle.update) == "ENGINE_ALREADY_LATEST"

    def test_dry_run_changes_nothing(self, tmp_path: Path, releases: Releases) -> None:
        report = vendored_project(tmp_path, releases).update(dry_run=True)
        assert report.applied is False
        assert engine_text(tmp_path, "http/response.py") == "response = 1\n"
        assert load_lock(tmp_path).ref == "v4.4.2-r00024"

    def test_unregistered_drift_blocks_a_move(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases, {**BASE_FILES, "orm/model.py": "local\n"})
        assert refusal(lifecycle.update) == "ENGINE_DRIFT_UNREGISTERED"

    def test_a_patch_untouched_upstream_is_carried_over(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        (tmp_path / "engine/orm/model.py").write_text("patched\n", encoding="utf-8")
        lifecycle.record_patch(["orm/model.py"], "SP-1", "improvement", "r", "t")
        report = lifecycle.update()
        assert [patch.id for patch in report.plan.carried] == ["SP-1"]
        assert engine_text(tmp_path, "orm/model.py") == "patched\n"
        assert not lifecycle.status(check_remote=False).drift

    def test_a_patch_absorbed_upstream_is_retired(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        (tmp_path / "engine/http/response.py").write_text("response = 2\n", encoding="utf-8")
        lifecycle.record_patch(["http/response.py"], "SEC-1", "security", "r", "t")
        report = lifecycle.update()
        assert report.plan.retired == ["SEC-1"]
        assert load_lock(tmp_path).patches == []

    def test_a_conflicting_patch_blocks_the_move_until_dropped(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        (tmp_path / "engine/http/response.py").write_text("ours\n", encoding="utf-8")
        lifecycle.record_patch(["http/response.py"], "SP-2", "improvement", "r", "t")
        assert refusal(lifecycle.update) == "ENGINE_PATCH_CONFLICT"
        assert engine_text(tmp_path, "http/response.py") == "ours\n"
        report = lifecycle.update(dropped=["SP-2"])
        assert report.plan.retired == ["SP-2"]
        assert engine_text(tmp_path, "http/response.py") == "response = 2\n"

    def test_a_failed_verification_rolls_the_engine_back(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        assert refusal(lambda: lifecycle.update(verify=python_command("raise SystemExit(3)"))) == "ENGINE_VERIFY_FAILED"
        assert engine_text(tmp_path, "http/response.py") == "response = 1\n"
        assert load_lock(tmp_path).ref == "v4.4.2-r00024"
        assert not [path.name for path in tmp_path.iterdir() if path.name.startswith(".engine.")]

    def test_a_passing_verification_runs_against_the_new_engine(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        check = "import pathlib, sys; sys.exit(pathlib.Path('engine/http/response.py').read_text() != 'response = 2\\n')"
        assert lifecycle.update(verify=python_command(check)).applied

    def test_upgrade_crosses_minors_and_lists_what_needs_attention(self, tmp_path: Path, releases: Releases) -> None:
        report = vendored_project(tmp_path, releases).upgrade("4.5.0")
        assert report.target.ref == "v4.5.0-r00026"
        assert engine_text(tmp_path, "orm/model.py") == "model = 3\n"
        attention = [entry for section in report.notes for entry in section.attention]
        assert attention == ["Removed: **Legacy helper**: gone.", "Security: **Response header fix**."]

    def test_upgrade_refuses_a_version_that_is_not_newer(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = vendored_project(tmp_path, releases)
        assert refusal(lambda: lifecycle.upgrade("4.4.2")) == "ENGINE_NOT_NEWER"
        assert refusal(lambda: lifecycle.upgrade("five")) == "ENGINE_VERSION_INVALID"


class TestPackageMoves:
    """Update of an engine installed from a pinned archive."""

    def package_project(self, root: Path, releases: Releases) -> EngineLifecycle:
        """Create a project whose Dockerfile pins v4.4.2 and adopt it."""
        (root / "Dockerfile").write_text("ARG CRAFT_ENGINE_REF=v4.4.2-r00024\n", encoding="utf-8")
        lifecycle = EngineLifecycle(root, ("4.4.2", "r00024"))
        lifecycle.adopt("v4.4.2-r00024", "package", pin_files=["Dockerfile"], source=releases.source)
        return lifecycle

    def test_update_rewrites_the_pin(self, tmp_path: Path, releases: Releases) -> None:
        self.package_project(tmp_path, releases).update()
        assert (tmp_path / "Dockerfile").read_text(encoding="utf-8") == "ARG CRAFT_ENGINE_REF=v4.4.3-r00025\n"
        assert load_lock(tmp_path).ref == "v4.4.3-r00025"

    def test_a_failed_verification_restores_the_pin(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = self.package_project(tmp_path, releases)
        assert refusal(lambda: lifecycle.update(verify=python_command("raise SystemExit(1)"))) == "ENGINE_VERIFY_FAILED"
        assert "v4.4.2-r00024" in (tmp_path / "Dockerfile").read_text(encoding="utf-8")

    def test_a_pin_file_that_no_longer_spells_the_ref_is_refused(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = self.package_project(tmp_path, releases)
        (tmp_path / "Dockerfile").write_text("ARG CRAFT_ENGINE_REF=main\n", encoding="utf-8")
        assert refusal(lifecycle.update) == "ENGINE_PIN_NOT_FOUND"

    def test_hotfix_needs_a_vendored_engine(self, tmp_path: Path, releases: Releases) -> None:
        lifecycle = self.package_project(tmp_path, releases)
        assert refusal(lambda: lifecycle.hotfix("v4.4.3-r00025", ["http/response.py"], "H", "r", "t")) == "ENGINE_NOT_VENDORED"


class TestConsole:
    """The `engine` command group."""

    def test_status_and_refusal_exit_codes(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from engine.cli.app import cli

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        refused = runner.invoke(cli, ["engine", "status", "--offline"])
        assert refused.exit_code == 1 and "ENGINE_LOCK_MISSING" in refused.output
        assert runner.invoke(cli, ["engine", "adopt", "v4.4.2-r00024"]).exit_code == 0
        status = runner.invoke(cli, ["engine", "status", "--offline"])
        assert status.exit_code == 0 and "v4.4.2-r00024" in status.output
