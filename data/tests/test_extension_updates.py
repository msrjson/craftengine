"""Extension ownership, forward updates and compatibility across worker load paths."""

import json
import uuid
from contextvars import copy_context
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from bootstrap.app import app
from engine.config.repository import ConfigRepository
from engine.container.application import Application, Container
from engine.events.dispatcher import EventDispatcher
from engine.extensions.context import ExtensionContext
from engine.extensions.errors import ExtensionError
from engine.extensions.manager import Availability, ExtensionManager
from engine.extensions.store import ExtensionState, ExtensionStore
from engine.http.router import Router


@pytest.fixture
def runtime(tmp_path: Path, migrated_database: Application, monkeypatch: pytest.MonkeyPatch) -> Iterator[ExtensionManager]:
    """An independent worker sharing only the session's isolated test database."""
    worker = Application(str(tmp_path), bind_as_global=False)
    monkeypatch.syspath_prepend(str(tmp_path))
    config = ConfigRepository()
    config.set("extensions.paths", [str(tmp_path)])
    worker.instance("config", config)
    worker.instance("db", app.make("db"))
    worker.instance("router", Router(worker))
    worker.instance("events", EventDispatcher(worker))
    manager = ExtensionManager(worker)
    manager.store = ExtensionStore(None)
    yield manager
    for slug in manager.manifests():
        manager.loader.unload(slug)


def extension(
    runtime: ExtensionManager, *, slug: str | None = None, version: str = "1.0.0", kind: str = "module",
    engine: str = "", requires: dict[str, str] | None = None, provider: str | None = None, routes: str | None = None,
) -> tuple[str, Path]:
    """Write a self-contained extension with no shared test identity."""
    slug = slug or "unit_" + uuid.uuid4().hex[:12]
    directory = Path(runtime.app.base_path) / slug
    directory.mkdir(exist_ok=True)
    manifest = f'slug = "{slug}"\nkind = "{kind}"\nversion = "{version}"\nengine = "{engine}"\n'
    if requires:
        manifest += "[requires]\n" + "".join(f'{key} = "{value}"\n' for key, value in requires.items())
    (directory / "extension.toml").write_text(manifest)
    for name, source in (("provider.py", provider), ("routes.py", routes)):
        if source is not None:
            (directory / name).write_text(source)
    runtime.manifests(refresh=True)
    return slug, directory


def test_deactivation_releases_cached_service_and_alias(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime, provider="def register(context):\n    context.app.singleton('owned', lambda c: object())\n    context.app.alias('owned', 'owned_alias')\n")
    runtime.install(slug)
    runtime.activate(slug)
    first = runtime.app.make("owned_alias")
    runtime.deactivate(slug)
    assert not runtime.app.bound("owned")
    assert not runtime.app.bound("owned_alias")
    with pytest.raises(KeyError):
        runtime.app.make("owned")
    runtime.activate(slug)
    assert runtime.app.make("owned") is not first


def test_failed_provider_undoes_bindings_without_overwriting_application(runtime: ExtensionManager) -> None:
    original = object()
    runtime.app.instance("protected", original)
    slug, _ = extension(runtime, provider="def register(context):\n    context.app.singleton('temporary', lambda c: object())\n    context.app.singleton('protected', lambda c: object())\n")
    runtime.install(slug)
    with pytest.raises(ExtensionError, match="EXTENSION_BINDING_CONFLICT"):
        runtime.activate(slug)
    assert runtime.app.make("protected") is original
    assert not runtime.app.bound("temporary")
    assert runtime.state(slug) is ExtensionState.FAILED


def test_scoped_binding_cannot_reuse_a_previous_activation_cache(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime)
    manifest = runtime.manifest(slug)
    token = Container.begin_request_scope()
    try:
        context = ExtensionContext(runtime.app, manifest, runtime)
        context.app.scoped("owned_scope", lambda c: object())
        first = runtime.app.make("owned_scope")
        context.unload()
        context.app.scoped("owned_scope", lambda c: object())
        assert runtime.app.make("owned_scope") is not first
        context.unload()
    finally:
        Container.end_request_scope(token)


def test_scoped_caches_in_another_request_do_not_survive_reactivation(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime)
    context = ExtensionContext(runtime.app, runtime.manifest(slug), runtime)
    context.app.scoped("owned_scope", lambda c: object())
    request = copy_context()
    request.run(Container.begin_request_scope)
    first = request.run(runtime.app.make, "owned_scope")
    context.unload()
    context.app.scoped("owned_scope", lambda c: object())
    assert request.run(runtime.app.make, "owned_scope") is not first
    context.unload()


def test_partial_route_registration_is_undone_when_register_raises(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime, routes="def register(router):\n    router.get('/partial', lambda: None).name('partial')\n    raise RuntimeError('TEST_ROUTE_FAILURE')\n")
    runtime.install(slug)
    with pytest.raises(ExtensionError, match="EXTENSION_BOOT_FAILED"):
        runtime.activate(slug)
    assert runtime.app.make("router").routes == []


def test_update_failure_keeps_installed_version_and_successful_forward_steps(runtime: ExtensionManager) -> None:
    slug, directory = extension(runtime)
    runtime.install(slug)
    extension(runtime, slug=slug, version="1.1.0")
    migrations = directory / "migrations"
    migrations.mkdir()
    table = slug + "_checkpoint"
    first = f"2026_10_06_000010_create_{table}"
    (migrations / (first + ".py")).write_text(
        f"from craft.migrations import Schema\ndef up():\n    Schema.create_table('{table}', lambda t: t.id())\n"
    )
    second = f"2026_10_06_000011_complete_{table}"
    pending = migrations / (second + ".py")
    pending.write_text("def up():\n    raise RuntimeError('TEST_PENDING_MIGRATION')\n")
    with pytest.raises(RuntimeError, match="TEST_PENDING_MIGRATION"):
        runtime.update(slug)
    assert runtime.store.get(slug)["version"] == "1.0.0"
    runtime.app.make("db").table(table).insert({"id": 1})
    pending.write_text("def up():\n    pass\n")
    assert runtime.update(slug) == [second]
    assert runtime.app.make("db").table(table).count() == 1


def test_invalid_catalog_is_refused_before_running_update_migrations(runtime: ExtensionManager) -> None:
    slug, directory = extension(runtime)
    runtime.install(slug)
    extension(runtime, slug=slug, version="1.1.0")
    (directory / "lang").mkdir()
    (directory / "lang" / "catalog.json").write_text("{}")
    (directory / "migrations").mkdir()
    (directory / "migrations" / f"2026_10_06_000020_fail_{slug}.py").write_text(
        "def up():\n    raise RuntimeError('TEST_MIGRATION_MUST_NOT_RUN')\n"
    )
    with pytest.raises(ExtensionError, match="EXTENSION_CATALOG_LOCALE_MISSING"):
        runtime.update(slug)
    assert runtime.store.get(slug)["version"] == "1.0.0"


def _installed_record(runtime: ExtensionManager) -> tuple[str, Path, str, str, dict[str, Any]]:
    """Install a record-owning extension with one operator-edited translation."""
    slug, directory = extension(runtime)
    table = slug + "_records"
    migrations = directory / "migrations"
    migrations.mkdir()
    (migrations / f"2026_10_06_000001_create_{table}.py").write_text(
        f"from craft.migrations import Schema\ndef up():\n    Schema.create_table('{table}', lambda t: (t.id(), t.string('value')))\n"
    )
    lang = directory / "lang"
    lang.mkdir()
    key = slug + ".extension.name"
    catalog = {locale: {key: slug} for locale in ("en", "pt-BR", "es")}
    (directory / "lang" / "catalog.json").write_text(json.dumps(catalog))
    runtime.install(slug)
    db = runtime.app.make("db")
    db.table(table).insert({"value": "preserved"})
    db.table("translations").where("key", key).where("locale", "en").update({"value": "operator"})
    return slug, directory, table, key, catalog


def test_update_keeps_records_and_edited_translations_and_runs_pending_migrations(runtime: ExtensionManager) -> None:
    slug, directory, table, key, catalog = _installed_record(runtime)
    db = runtime.app.make("db")
    migrations = directory / "migrations"
    extension(runtime, slug=slug, version="1.1.0")
    migration = f"2026_10_06_000002_extend_{table}"
    (migrations / (migration + ".py")).write_text(
        f"from craft.migrations import Schema\ndef up():\n    Schema.table('{table}', lambda t: t.string('extra').nullable())\n"
    )
    new_key = slug + ".screen.title"
    for entries in catalog.values():
        entries[new_key] = slug
    (directory / "lang" / "catalog.json").write_text(json.dumps(catalog))
    assert runtime.update(slug) == [migration]
    assert runtime.store.get(slug)["version"] == "1.1.0"
    assert db.table(table).first()["value"] == "preserved"
    assert db.table(table).first()["extra"] is None
    assert db.table("translations").where("key", key).where("locale", "en").first()["value"] == "operator"
    assert {r["locale"] for r in db.table("translations").where("key", new_key).get()} == {"en", "pt-BR", "es"}
    assert runtime.update(slug) == []
    with pytest.raises(ExtensionError, match="EXTENSION_RESTART_REQUIRED"):
        runtime.activate(slug)


def test_deactivation_does_not_claim_a_new_disk_version_is_installed(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime)
    runtime.install(slug)
    runtime.activate(slug)
    extension(runtime, slug=slug, version="1.1.0")
    runtime.deactivate(slug)
    assert runtime.store.get(slug)["version"] == "1.0.0"
    assert runtime.status()[0]["update_required"] is True
    with pytest.raises(ExtensionError, match="EXTENSION_UPDATE_REQUIRED"):
        runtime.activate(slug)


@pytest.mark.parametrize(("changes", "code"), [
    ({"version": "0.9.0"}, "EXTENSION_DOWNGRADE_FORBIDDEN"),
    ({"kind": "plugin"}, "EXTENSION_KIND_CHANGE_FORBIDDEN"),
    ({"engine": "<1"}, "EXTENSION_ENGINE_INCOMPATIBLE"),
])
def test_invalid_update_is_refused_before_schema_changes(runtime: ExtensionManager, changes: dict[str, str], code: str) -> None:
    slug, _ = extension(runtime)
    runtime.install(slug)
    extension(runtime, slug=slug, **changes)
    with pytest.raises(ExtensionError, match=code):
        runtime.update(slug)
    assert runtime.store.get(slug)["version"] == "1.0.0"
    assert runtime.state(slug) is ExtensionState.INSTALLED


def test_active_update_and_incompatible_installed_dependents_are_refused(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime)
    runtime.install(slug)
    runtime.activate(slug)
    with pytest.raises(ExtensionError, match="EXTENSION_UPDATE_REQUIRES_INACTIVE"):
        runtime.update(slug)
    runtime.deactivate(slug)
    dependent, _ = extension(runtime, requires={slug: ">=1,<2"})
    runtime.install(dependent)
    extension(runtime, slug=slug, version="2.0.0")
    with pytest.raises(ExtensionError, match="EXTENSION_DEPENDENT_VERSION"):
        runtime.update(slug)
    assert runtime.store.get(slug)["version"] == "1.0.0"


def test_update_refuses_a_worker_that_has_not_unloaded_yet(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime)
    runtime.install(slug)
    runtime.activate(slug)
    runtime.store.save(slug, "module", "1.0.0", ExtensionState.INACTIVE)
    with pytest.raises(ExtensionError, match="EXTENSION_UPDATE_REQUIRES_INACTIVE"):
        runtime.update(slug)


@pytest.mark.parametrize("load", ["boot", "reconcile"])
def test_updated_worker_cannot_bypass_restart_by_following_external_activation(runtime: ExtensionManager, load: str) -> None:
    slug, _ = extension(runtime)
    runtime.install(slug)
    runtime.update(slug)
    runtime.store.save(slug, "module", "1.0.0", ExtensionState.ACTIVE)
    getattr(runtime, load)()
    assert not runtime.loader.is_loaded(slug)
    assert runtime.state(slug) is ExtensionState.FAILED


@pytest.mark.parametrize("load", ["boot", "reconcile"])
def test_workers_refuse_unapplied_versions_and_preserve_unrelated_extensions(runtime: ExtensionManager, load: str) -> None:
    slug, _ = extension(runtime)
    healthy, _ = extension(runtime)
    for name in (slug, healthy):
        runtime.install(name)
        runtime.store.save(name, "module", "1.0.0", ExtensionState.ACTIVE)
    extension(runtime, slug=slug, version="1.1.0")
    getattr(runtime, load)()
    assert runtime.state(slug) is ExtensionState.FAILED
    assert runtime.store.get(slug)["version"] == "1.0.0"
    assert runtime.availability(healthy) is Availability.SERVING


def test_reconcile_loads_dependencies_before_dependents(runtime: ExtensionManager) -> None:
    dependency, _ = extension(runtime, slug="zz_dependency")
    dependent, _ = extension(runtime, slug="aa_dependent", requires={dependency: ">=1"})
    for slug in (dependency, dependent):
        runtime.install(slug)
        runtime.store.save(slug, "module", "1.0.0", ExtensionState.ACTIVE)
    runtime.reconcile()
    assert runtime.availability(dependency) is Availability.SERVING
    assert runtime.availability(dependent) is Availability.SERVING


@pytest.mark.parametrize("load", ["boot", "reconcile"])
def test_workers_check_engine_and_dependency_versions_before_loading(runtime: ExtensionManager, load: str) -> None:
    old_engine, _ = extension(runtime, engine="<1")
    runtime.store.save(old_engine, "module", "1.0.0", ExtensionState.ACTIVE)
    dependency, _ = extension(runtime)
    runtime.install(dependency)
    dependent, _ = extension(runtime, requires={dependency: ">=2"})
    runtime.store.save(dependent, "module", "1.0.0", ExtensionState.ACTIVE)
    runtime.store.save(dependency, "module", "1.0.0", ExtensionState.ACTIVE)
    getattr(runtime, load)()
    assert runtime.state(old_engine) is ExtensionState.FAILED
    assert runtime.state(dependent) is ExtensionState.FAILED
    assert runtime.availability(dependency) is Availability.SERVING


def test_new_manager_in_same_process_cannot_reload_cached_python(runtime: ExtensionManager) -> None:
    slug, _ = extension(runtime, provider="def register(context):\n    context.app.singleton('cached_python', lambda c: 1)\n")
    runtime.install(slug)
    runtime.activate(slug)
    runtime.deactivate(slug)
    extension(runtime, slug=slug, version="1.1.0")
    runtime.update(slug)
    other = ExtensionManager(runtime.app)
    other.store = runtime.store
    with pytest.raises(ExtensionError, match="EXTENSION_RESTART_REQUIRED"):
        other.activate(slug)
    assert not runtime.app.bound("cached_python")


def test_update_refusal_messages_exist_in_all_three_database_locales(runtime: ExtensionManager) -> None:
    keys = {
        "extension_binding_conflict", "extension_update_requires_inactive", "extension_restart_required",
        "extension_update_required", "extension_kind_change_forbidden", "extension_downgrade_forbidden",
        "extension_dependent_version",
    }
    for code in keys:
        rows = runtime.app.make("db").table("translations").where("key", "extension.error." + code).get()
        assert {row["locale"] for row in rows} == {"en", "pt-BR", "es"}


def test_cli_update_invokes_the_same_manager_and_reports_refusals(runtime: ExtensionManager, monkeypatch: pytest.MonkeyPatch) -> None:
    from engine.cli import extension_commands

    monkeypatch.setattr(extension_commands, "_manager", lambda: runtime)
    slug, _ = extension(runtime)
    runtime.install(slug)
    result = CliRunner().invoke(extension_commands.extension_app, ["update", slug])
    assert result.exit_code == 0
    runtime.store.save(slug, "module", "1.0.0", ExtensionState.ACTIVE)
    result = CliRunner().invoke(extension_commands.extension_app, ["update", slug])
    assert result.exit_code == 1
    assert "EXTENSION_UPDATE_REQUIRES_INACTIVE" in result.output
