"""The engine never imports the application.

Business rules live in the application's modules and plugins; the engine is
extended only through its seams. These tests pin that boundary inside the
suite and cover the ratcheted gate in `tools/check_engine_boundary.py`.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: The CLI launcher loads the application's composition root. Known debt,
#: held by the gate's ratchet; this set may only shrink.
KNOWN_ENGINE_DEBT = {("engine/cli/app.py", "ENGINE_APP_IMPORT", "bootstrap.app")}


def _load_gate() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("check_engine_boundary", ROOT / "tools" / "check_engine_boundary.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_gate()
POLICY = json.loads((ROOT / "tools" / "engine-boundary-policy.json").read_text())


def _codes(path: str, source: str) -> list[tuple[str, str]]:
    return [(f.code, f.target) for f in gate.scan_source(path, source, POLICY)]


class TestTheRealEngine:
    def test_engine_imports_no_application_code_beyond_known_debt(self):
        found = {f.signature() for f in gate.scan_tree(ROOT, POLICY)}
        assert found <= KNOWN_ENGINE_DEBT

    def test_gate_passes_when_the_base_holds_the_same_debt(self, monkeypatch, capsys):
        same_tree = lambda path: (ROOT / path).read_text(encoding="utf-8")  # noqa: E731
        monkeypatch.setattr(gate, "git_source_at", lambda _revision: same_tree)
        assert gate.main([]) == 0
        assert "ENGINE_BOUNDARY_NEW_FINDINGS 0" in capsys.readouterr().out

    def test_an_unreadable_base_blocks_instead_of_guessing(self, monkeypatch, capsys):
        def unreadable(_revision):
            raise gate.GateBlocked("BOUNDARY_BASE_UNREADABLE")

        monkeypatch.setattr(gate, "git_source_at", unreadable)
        assert gate.main([]) == 2
        assert "ENGINE_BOUNDARY_BLOCKED BOUNDARY_BASE_UNREADABLE" in capsys.readouterr().out


class TestDetection:
    @pytest.mark.parametrize("source,target", [
        ("import app.Models.User\n", "app.Models.User"),
        ("import routes.web as web\n", "routes.web"),
        ("from config.app import APP_KEY\n", "config.app"),
        ("from database.seeders import run\n", "database.seeders"),
        ("import importlib\nimportlib.import_module('app.Services.billing')\n", "app.Services.billing"),
        ("__import__('bootstrap.app')\n", "bootstrap.app"),
        ("from importlib import import_module as load\nload('app.Models.User')\n", "app.Models.User"),
        ("import importlib\nimportlib.import_module(name='routes.web')\n", "routes.web"),
    ])
    def test_engine_importing_the_application_is_found(self, source, target):
        assert _codes("engine/http/x.py", source) == [("ENGINE_APP_IMPORT", target)]

    @pytest.mark.parametrize("source", [
        "from . import router\n",
        "from engine.config.repository import env\n",
        "import application_helpers\n",
        "TEMPLATE = 'from app.Models.User import User'\n",
        "importlib.import_module(name)\n",
    ])
    def test_engine_internal_and_template_code_is_not_flagged(self, source):
        assert _codes("engine/cli/generators.py", source) == []

    def test_application_files_may_import_the_application(self):
        assert _codes("app/Http/Controllers/HomeController.py", "import app.Models.User\n") == []

    def test_service_importing_a_controller_is_found(self):
        source = "from app.Http.Controllers.InvoiceController import InvoiceController\n"
        found = _codes("app/Services/billing_service.py", source)
        assert found == [("SERVICE_CONTROLLER_IMPORT", "app.Http.Controllers.InvoiceController")]

    def test_an_undecodable_engine_file_is_a_finding(self, tmp_path):
        policy = {**POLICY, "scan_roots": ["engine"]}
        (tmp_path / "engine").mkdir()
        (tmp_path / "engine" / "latin.py").write_bytes(b"# caf\xe9\n")
        found = [(f.code, f.target) for f in gate.scan_tree(tmp_path, policy)]
        assert found == [("BOUNDARY_SYNTAX", "undecodable")]

    def test_a_missing_scan_root_blocks_the_gate(self, tmp_path):
        with pytest.raises(gate.GateBlocked) as blocked:
            gate.scan_tree(tmp_path, {**POLICY, "scan_roots": ["engine"]})
        assert blocked.value.code == "BOUNDARY_SCAN_ROOT_MISSING"

    def test_unparseable_engine_file_is_a_finding(self):
        assert _codes("engine/broken.py", "def (:\n") == [("BOUNDARY_SYNTAX", "unparseable")]


class TestRatchet:
    current_source = "import app.a\n\n\nimport app.a\nimport app.b\n"

    def _new(self, base_source):
        current = gate.scan_source("engine/x.py", self.current_source, POLICY)
        return [(f.target, f.line) for f in gate.new_findings(current, lambda _path: base_source, POLICY)]

    def test_debt_moved_to_another_line_is_not_new(self):
        assert self._new("import app.b\nimport app.a\nimport app.a\n") == []

    def test_a_duplicate_of_existing_debt_is_new(self):
        assert self._new("import app.a\nimport app.b\n") == [("app.a", 4)]

    def test_a_file_absent_at_the_base_is_entirely_new(self):
        assert len(self._new(None)) == 3


class TestPolicy:
    def test_a_base_that_is_not_a_full_sha_blocks_the_gate(self, tmp_path):
        policy = tmp_path / "policy.json"
        policy.write_text(json.dumps({**POLICY, "base_commit": "HEAD"}))
        with pytest.raises(gate.GateBlocked) as blocked:
            gate.load_policy(policy)
        assert blocked.value.code == "BOUNDARY_BASE_MISSING_OR_INVALID"

    def test_an_unreadable_policy_blocks_the_gate(self, tmp_path):
        with pytest.raises(gate.GateBlocked) as blocked:
            gate.load_policy(tmp_path / "missing.json")
        assert blocked.value.code == "BOUNDARY_POLICY_UNREADABLE"


class TestConsoleRoutesSeam:
    """The application names its console module; the engine hardcodes no path."""

    def _provider(self, module_path):
        from engine.providers.service_providers import FrameworkSubsystemsServiceProvider

        app = MagicMock()
        app.make.return_value.get.return_value = module_path
        return FrameworkSubsystemsServiceProvider(app)

    def _provider_without_the_key(self):
        from engine.providers.service_providers import FrameworkSubsystemsServiceProvider

        app = MagicMock()
        app.make.return_value.get.side_effect = lambda _key, default=None: default
        return FrameworkSubsystemsServiceProvider(app)

    def test_a_project_without_the_key_keeps_the_conventional_module(self, monkeypatch):
        registered = []
        module = types.ModuleType("routes.console")
        module.register_console = lambda: registered.append(True)
        monkeypatch.setitem(sys.modules, "routes.console", module)
        self._provider_without_the_key()._load_scheduled_tasks()
        assert registered == [True]

    def test_a_missing_console_module_is_skipped_quietly(self, monkeypatch, caplog):
        missing = ModuleNotFoundError("PROBE", name="console_seam_absent")
        monkeypatch.setattr(importlib, "import_module", MagicMock(side_effect=missing))
        self._provider("console_seam_absent")._load_scheduled_tasks()
        assert "console" not in caplog.text

    def test_a_broken_import_inside_the_console_module_is_logged(self, monkeypatch, caplog):
        broken = ModuleNotFoundError("PROBE", name="a_dependency_it_needs")
        monkeypatch.setattr(importlib, "import_module", MagicMock(side_effect=broken))
        self._provider("console_seam_probe")._load_scheduled_tasks()
        assert "console_routes_import_failed" in caplog.text

    def test_the_module_named_in_config_is_registered(self, monkeypatch):
        registered = []
        module = types.ModuleType("console_seam_probe")
        module.register_console = lambda: registered.append(True)
        monkeypatch.setitem(sys.modules, "console_seam_probe", module)
        self._provider("console_seam_probe")._load_scheduled_tasks()
        assert registered == [True]

    def test_an_empty_setting_loads_nothing(self, monkeypatch):
        monkeypatch.setattr(importlib, "import_module", MagicMock(side_effect=AssertionError))
        self._provider("")._load_scheduled_tasks()
