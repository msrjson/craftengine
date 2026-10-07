"""`release:sync` records what a deploy did; `VERSION` must match the running code."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import pytest

from engine.lifecycle.errors import EngineLifecycleError
from engine.lifecycle.sync import ReleaseSync


def _app():
    from bootstrap.app import app

    return app


def _db():
    return _app().make("db")


def test_code_identity_is_the_version_and_release_counter():
    import engine

    assert ReleaseSync.code_identity() == f"{engine.__version__}-{engine.__release__}"


def test_the_version_file_matches_the_running_code(migrated_database):
    assert ReleaseSync(_app()).read_version_file() == ReleaseSync.code_identity()


def test_a_stale_version_file_is_refused(migrated_database, monkeypatch):
    sync = ReleaseSync(_app())
    monkeypatch.setattr(sync, "read_version_file", lambda: "0.0.0-r00000")
    with pytest.raises(EngineLifecycleError) as refused:
        sync.verify_identity()
    assert refused.value.code == "RELEASE_VERSION_DRIFT"


def test_a_missing_version_file_is_refused(migrated_database, monkeypatch):
    sync = ReleaseSync(_app())
    monkeypatch.setattr(sync, "read_version_file", lambda: None)
    with pytest.raises(EngineLifecycleError) as refused:
        sync.verify_identity()
    assert refused.value.code == "RELEASE_VERSION_FILE_MISSING"


def test_sync_records_a_row_and_runs_the_seeders(migrated_database):
    result = ReleaseSync(_app()).sync()
    assert result["version"] == ReleaseSync.code_identity()
    assert result["status"] == "ok"
    assert result["seeders_run"] == 1

    row = _db().statement(
        "SELECT version, status FROM release_syncs ORDER BY id DESC LIMIT 1", read=True
    ).fetchone()
    assert row["version"] == ReleaseSync.code_identity()
    assert row["status"] == "ok"


def test_sync_appends_without_deleting_the_trail(migrated_database):
    before = _db().statement("SELECT COUNT(*) AS n FROM release_syncs", read=True).fetchone()["n"]
    ReleaseSync(_app()).sync()
    ReleaseSync(_app()).sync()
    after = _db().statement("SELECT COUNT(*) AS n FROM release_syncs", read=True).fetchone()["n"]
    assert after == before + 2


def test_status_reports_the_last_sync(migrated_database):
    ReleaseSync(_app()).sync()
    report = ReleaseSync(_app()).status()
    assert report["code"] == ReleaseSync.code_identity()
    assert report["version_file"] == ReleaseSync.code_identity()
    assert report["last_sync"]["version"] == ReleaseSync.code_identity()
