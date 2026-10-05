"""The extension model: modules, plugins and themes the engine runs and isolates (ADR 0004).

The fixtures under `tests/fixtures/extensions/` are a small application made
only of extensions: `catalog` exposes a service, `ordering` reaches it only
through the internal proxy, `member_pricing` filters its prices, `sunrise`
overrides its view, `flaky` fails at runtime and `broken` fails at load.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import os
import uuid

import pytest
from starlette.testclient import TestClient

from bootstrap.app import app, asgi_app
from craft.facades import DB, Proxy
from engine.container.internal_proxy import InternalProxyError
from engine.extensions.breaker import BreakerState, CircuitBreaker
from engine.extensions.errors import ExtensionError
from engine.extensions.manager import Availability, ExtensionManager, ReconcileTicker
from engine.extensions.manifest import ExtensionKind, load_manifest
from engine.extensions.store import ExtensionState, ExtensionStore
from engine.extensions.versions import satisfies
from engine.migrations.migrator import Migrator

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "extensions")
ROOTS = [os.path.join(FIXTURES, kind) for kind in ("modules", "plugins", "themes")]

#: Routes are registered once per process; every test manager shares the set.
_ROUTES_LOADED: set = set()


@pytest.fixture
def extensions(migrated_database):
    """A manager over the fixtures, in memory, installed as the app's `extensions`."""
    manager = ExtensionManager(app)
    manager.roots = list(ROOTS)
    manager.store = ExtensionStore(None)
    manager.loader._routes_loaded = _ROUTES_LOADED
    manager.breaker = CircuitBreaker(threshold=3, window=60, cooldown=3600)
    previous = app.make("extensions")
    proxy = app.make("proxy")
    app.instance("extensions", manager)
    proxy.set_gate(manager)
    yield manager
    for slug in list(manager.manifests()):
        manager.loader.unload(slug)
    app.instance("extensions", previous)
    proxy.set_gate(previous)
    app.make("view").set_theme_resolver(None)


@pytest.fixture
def client():
    return TestClient(asgi_app)


def _activate(manager, *slugs):
    for slug in slugs:
        if manager.state(slug) is ExtensionState.DISCOVERED:
            manager.install(slug)
        manager.activate(slug)


def _write_extension(root, slug, manifest, files=None):
    directory = root / slug
    directory.mkdir(parents=True)
    (directory / "extension.toml").write_text(manifest)
    for name, content in (files or {}).items():
        (directory / name).write_text(content)
    return str(directory)


class TestVersions:
    @pytest.mark.parametrize(
        ("version", "spec", "expected"),
        [("4.3.0", ">=4.3,<5", True), ("5.0", ">=4.3,<5", False), ("1.2.0", "", True), ("2.0.1", "!=2.0.1", False), ("3", "==3.0.0", True)],
    )
    def test_ranges(self, version, spec, expected):
        assert satisfies(version, spec) is expected

    def test_a_malformed_range_is_refused(self):
        with pytest.raises(ExtensionError) as refused:
            satisfies("1.0", "~>1")
        assert refused.value.code == "EXTENSION_VERSION_RANGE_INVALID"


class TestManifest:
    def test_the_fixture_manifest_parses(self):
        manifest = load_manifest(os.path.join(FIXTURES, "modules", "ordering"))
        assert (manifest.slug, manifest.kind, manifest.requires) == ("ordering", ExtensionKind.MODULE, {"catalog": ">=1.0,<2"})

    @pytest.mark.parametrize(
        ("manifest", "files", "code"),
        [
            ('slug = "Bad-Slug"\nkind = "module"\nversion = "1.0"\n', {}, "EXTENSION_SLUG_INVALID"),
            ('slug = "ok_one"\nkind = "widget"\nversion = "1.0"\n', {}, "EXTENSION_KIND_INVALID"),
            ('slug = "ok_one"\nkind = "module"\nversion = "one"\n', {}, "EXTENSION_VERSION_INVALID"),
            ('slug = "ok_one"\nkind = "module"\nversion = "1.0"\n[requires]\nok_one = ">=1"\n', {}, "EXTENSION_REQUIRES_INVALID"),
            ('slug = "ok_one"\nkind = "theme"\nversion = "1.0"\n', {"routes.py": ""}, "EXTENSION_KIND_CONTRIBUTION_FORBIDDEN"),
            ("slug = \n", {}, "EXTENSION_MANIFEST_UNREADABLE"),
        ],
    )
    def test_invalid_manifests_are_refused_with_a_code(self, tmp_path, manifest, files, code):
        directory = _write_extension(tmp_path, "candidate", manifest, files)
        with pytest.raises(ExtensionError) as refused:
            load_manifest(directory)
        assert refused.value.code == code
        assert refused.value.message_key == "extension.error." + code.lower()

    def test_one_broken_manifest_never_stops_discovery(self, tmp_path):
        _write_extension(tmp_path, "good", 'slug = "good"\nkind = "module"\nversion = "1.0"\n')
        _write_extension(tmp_path, "bad", "not toml at all = = =\n")
        _write_extension(tmp_path, "twin", 'slug = "good"\nkind = "module"\nversion = "1.0"\n')
        manager = ExtensionManager(app)
        manager.roots = [str(tmp_path)]
        assert list(manager.manifests()) == ["good"]
        codes = sorted(error.code for error in manager.discovery_errors.values())
        assert codes == ["EXTENSION_MANIFEST_UNREADABLE", "EXTENSION_SLUG_DUPLICATE"]


class TestCircuitBreaker:
    def test_it_opens_at_the_threshold_and_lets_one_trial_through_after_the_cooldown(self):
        now = [0.0]
        breaker = CircuitBreaker(threshold=2, window=10, cooldown=5, clock=lambda: now[0])
        assert breaker.record_failure("x") is False
        assert breaker.record_failure("x") is True
        assert (breaker.allow("x"), breaker.state("x")) == (False, BreakerState.OPEN)
        now[0] = 6.0
        assert breaker.allow("x") is True
        assert breaker.allow("x") is False
        breaker.record_success("x")
        assert breaker.state("x") is BreakerState.CLOSED

    def test_failures_outside_the_window_do_not_add_up(self):
        now = [0.0]
        breaker = CircuitBreaker(threshold=2, window=10, cooldown=5, clock=lambda: now[0])
        breaker.record_failure("x")
        now[0] = 11.0
        assert breaker.record_failure("x") is False


class TestLifecycle:
    def test_install_refuses_a_missing_dependency(self, extensions):
        with pytest.raises(ExtensionError) as refused:
            extensions.install("ordering")
        assert (refused.value.code, refused.value.detail) == ("EXTENSION_DEPENDENCY_MISSING", "catalog")

    def test_activation_needs_the_dependency_active(self, extensions):
        extensions.install("catalog")
        extensions.install("ordering")
        with pytest.raises(ExtensionError) as refused:
            extensions.activate("ordering")
        assert refused.value.code == "EXTENSION_DEPENDENCY_INACTIVE"

    def test_an_active_dependent_blocks_deactivation(self, extensions):
        _activate(extensions, "catalog", "ordering")
        with pytest.raises(ExtensionError) as refused:
            extensions.deactivate("catalog")
        assert (refused.value.code, refused.value.detail) == ("EXTENSION_HAS_ACTIVE_DEPENDENTS", "ordering")

    def test_uninstall_keeps_the_data(self, extensions):
        _activate(extensions, "catalog")
        with pytest.raises(ExtensionError):
            extensions.uninstall("catalog")
        extensions.deactivate("catalog")
        extensions.uninstall("catalog")
        assert extensions.state("catalog") is ExtensionState.UNINSTALLED
        DB.table("ext_test_catalog_items").count()

    def test_an_engine_out_of_range_is_refused(self, extensions, tmp_path):
        _write_extension(tmp_path, "ancient", 'slug = "ancient"\nkind = "module"\nversion = "1.0"\nengine = "<1"\n')
        extensions.roots = [str(tmp_path)]
        with pytest.raises(ExtensionError) as refused:
            extensions.install("ancient")
        assert refused.value.code == "EXTENSION_ENGINE_INCOMPATIBLE"

    def test_install_runs_its_migrations_and_seeds_three_locales(self, extensions):
        extensions.install("catalog")
        locales = {row["locale"] for row in DB.table("translations").where("key", "catalog.extension.name").get()}
        assert locales == {"en", "pt-BR", "es"}
        assert "2026_10_05_120001_create_ext_test_catalog_items" in Migrator(app).applied()

    def test_the_default_migrator_covers_installed_extensions(self, extensions):
        extensions.install("catalog")
        assert os.path.join(FIXTURES, "modules", "catalog", "migrations") in Migrator(app).directories()

    def test_a_catalog_key_without_the_slug_prefix_is_refused(self, extensions, tmp_path):
        directory = _write_extension(tmp_path, "labels", 'slug = "labels"\nkind = "plugin"\nversion = "1.0"\n')
        os.makedirs(os.path.join(directory, "lang"))
        with open(os.path.join(directory, "lang", "catalog.json"), "w") as handle:
            handle.write('{"en": {"other.key": "x"}, "pt-BR": {"other.key": "x"}, "es": {"other.key": "x"}}')
        extensions.roots = [str(tmp_path)]
        with pytest.raises(ExtensionError) as refused:
            extensions.install("labels")
        assert refused.value.code == "EXTENSION_CATALOG_KEY_PREFIX"


class TestFaultIsolation:
    def test_a_module_failing_at_load_is_marked_failed_and_the_rest_boot(self, extensions):
        for slug in ("broken", "catalog"):
            extensions.install(slug)
            extensions.store.save(slug, "module", "1.0.0", ExtensionState.ACTIVE)
        assert extensions.boot() == ["catalog"]
        assert extensions.state("broken") is ExtensionState.FAILED
        assert extensions.availability("broken") is Availability.UNAVAILABLE

    def test_a_failing_route_trips_only_its_own_breaker(self, extensions, client):
        _activate(extensions, "catalog", "flaky")
        statuses = [client.get("/ext-test/flaky").status_code for _ in range(4)]
        assert statuses == [500, 500, 500, 503]
        refused = client.get("/ext-test/flaky", headers={"accept": "application/json"}).json()
        assert (refused["code"], refused["message_key"]) == ("EXTENSION_UNAVAILABLE", "extension.error.unavailable")
        assert client.get("/ext-test/catalog/tea").status_code == 200

    def test_a_failing_listener_is_contained(self, extensions):
        _activate(extensions, "flaky")
        app.make("events").dispatch("ext_test.pinged")
        assert extensions.breaker.last_error("flaky") == "RuntimeError"

    def test_domain_errors_never_trip_the_breaker(self, extensions, client):
        _activate(extensions, "catalog")
        responses = [client.get("/ext-test/catalog/unknown", headers={"accept": "application/json"}) for _ in range(5)]
        assert {response.status_code for response in responses} == {404}
        assert responses[-1].json()["code"] == "CATALOG_PRODUCT_UNKNOWN"
        assert extensions.breaker.state("catalog") is BreakerState.CLOSED

    def test_an_open_breaker_refuses_proxy_calls_without_running_the_target(self, extensions):
        _activate(extensions, "catalog")
        for _ in range(3):
            extensions.breaker.record_failure("catalog", "TEST")
        with pytest.raises(InternalProxyError) as refused:
            Proxy.call("catalog", "price_cents", "tea")
        assert refused.value.code == "INTERNAL_TARGET_UNAVAILABLE"


class TestContributions:
    def test_modules_talk_only_through_the_proxy(self, extensions, client):
        _activate(extensions, "catalog", "ordering")
        assert client.get("/ext-test/ordering/tea/2").json() == {"sku": "tea", "total_cents": 2500}

    def test_a_plugin_filters_another_modules_value(self, extensions, client):
        _activate(extensions, "catalog", "ordering", "member_pricing")
        assert client.get("/ext-test/ordering/tea/2").json()["total_cents"] == 2250

    def test_deactivation_removes_every_contribution_without_a_restart(self, extensions, client):
        _activate(extensions, "catalog", "flaky")
        listeners = app.make("events").listeners_for("ext_test.pinged")
        assert any(listener.__qualname__.startswith("flaky:") for listener in listeners)
        extensions.deactivate("flaky")
        listeners = app.make("events").listeners_for("ext_test.pinged")
        assert not any(getattr(listener, "__qualname__", "").startswith("flaky:") for listener in listeners)
        extensions.deactivate("catalog")
        refused = client.get("/ext-test/catalog/tea", headers={"accept": "application/json"})
        assert (refused.status_code, refused.json()["code"], refused.json()["message_key"]) == (404, "MODULE_DISABLED", "module.error.disabled")
        assert "catalog" not in app.make("proxy").exposed()

    def test_a_theme_overrides_a_module_view(self, extensions, client):
        _activate(extensions, "catalog", "sunrise")
        assert 'data-layer="module"' in client.get("/ext-test/catalog/tea").text
        app.make("view").set_theme_resolver(lambda: "sunrise")
        assert 'data-layer="theme"' in client.get("/ext-test/catalog/tea").text

    def test_assets_are_served_only_while_the_extension_serves(self, extensions, client):
        _activate(extensions, "catalog")
        assert client.get("/extensions/catalog/css/catalog.css").status_code == 200
        extensions.deactivate("catalog")
        assert client.get("/extensions/catalog/css/catalog.css").status_code == 404


class TestScaffolding:
    def test_a_generated_module_with_a_screen_installs_activates_and_renders(self, extensions, client, tmp_path):
        from engine.cli.extension_scaffolder import build_extension, build_screen

        slug = "gen_" + uuid.uuid4().hex[:8]
        build_extension(str(tmp_path), ExtensionKind.MODULE, slug)
        build_screen(str(tmp_path), slug, "reports")
        extensions.roots = [str(tmp_path / "app" / "modules")]
        _activate(extensions, slug)
        url = "/" + slug.replace("_", "-")
        assert client.get(url).status_code == 200
        assert client.get(url + "/reports").status_code == 200
        assert Proxy.call(slug, "summary") == {"items": 0}

    @pytest.mark.parametrize("kind", [ExtensionKind.PLUGIN, ExtensionKind.THEME])
    def test_generated_plugins_and_themes_install_and_activate(self, extensions, tmp_path, kind):
        from engine.cli.extension_scaffolder import DEFAULT_ROOTS, build_extension

        slug = "gen_" + uuid.uuid4().hex[:8]
        build_extension(str(tmp_path), kind, slug)
        extensions.roots = [str(tmp_path / DEFAULT_ROOTS[kind])]
        _activate(extensions, slug)
        assert extensions.availability(slug) is Availability.SERVING

    def test_an_existing_extension_is_not_overwritten(self, tmp_path):
        from engine.cli.extension_scaffolder import build_extension

        build_extension(str(tmp_path), ExtensionKind.PLUGIN, "keeper")
        with pytest.raises(ExtensionError) as refused:
            build_extension(str(tmp_path), ExtensionKind.PLUGIN, "keeper")
        assert refused.value.code == "EXTENSION_ALREADY_EXISTS"


class TestWorkersConverge:
    def test_reconcile_loads_what_another_worker_activated(self, extensions):
        extensions.install("catalog")
        extensions.store.save("catalog", "module", "1.2.0", ExtensionState.ACTIVE)
        assert extensions.availability("catalog") is not Availability.SERVING
        extensions.reconcile()
        assert extensions.availability("catalog") is Availability.SERVING

    def test_reconcile_discovers_an_extension_added_after_boot(self, extensions, tmp_path):
        extensions.roots = [str(tmp_path)]
        assert extensions.manifests() == {}
        _write_extension(tmp_path, "late_arrival", 'slug = "late_arrival"\nkind = "plugin"\nversion = "1.0"\n')
        extensions.store.save("late_arrival", "plugin", "1.0", ExtensionState.ACTIVE)
        extensions.reconcile()
        assert extensions.availability("late_arrival") is Availability.SERVING

    def test_the_router_asks_the_ticker_once_the_interval_elapsed(self, extensions):
        extensions.reconcile_interval = 0
        assert ReconcileTicker(extensions).due() is True

    def test_state_is_persisted_in_the_extensions_table(self, migrated_database):
        store = ExtensionStore(lambda: app.make("db"))
        slug = "persisted_" + uuid.uuid4().hex[:8]
        store.save(slug, "module", "1.0.0", ExtensionState.INSTALLED)
        store.save(slug, "module", "1.0.0", ExtensionState.ACTIVE)
        assert DB.table("extensions").where("slug", slug).first()["state"] == "active"


class TestLegacyModules:
    """A route tagged with a module that is not an extension keeps the old contract, typed."""

    def test_a_disabled_module_answers_a_typed_404(self, migrated_database, client):
        slug = "legacy_" + uuid.uuid4().hex[:8]
        app.make("router").get(f"/ext-test/{slug}", lambda: "served").module(slug)
        modules = app.make("module")
        modules.register(slug, slug)
        assert client.get(f"/ext-test/{slug}").text == "served"
        modules.disable(slug)
        refused = client.get(f"/ext-test/{slug}", headers={"accept": "application/json"})
        assert refused.status_code == 404
        assert (refused.json()["code"], refused.json()["message_key"]) == ("MODULE_DISABLED", "module.error.disabled")

    def test_the_disabled_message_exists_in_every_locale(self, migrated_database):
        rows = DB.table("translations").where("key", "module.error.disabled").get()
        assert {row["locale"] for row in rows} == {"en", "pt-BR", "es"}
