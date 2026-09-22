"""Route service provider - load route files."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from craft.providers import ServiceProvider


class RouteServiceProvider(ServiceProvider):
    def register(self):
        pass

    def boot(self):
        import os
        import importlib.util
        routes_dir = os.path.join(self.app.base_path, "routes")
        from craft.facades import Route

        # Load web routes
        web_path = os.path.join(routes_dir, "web.py")
        if os.path.exists(web_path):
            self._load_routes(web_path)

        # Load API routes
        api_path = os.path.join(routes_dir, "api.py")
        if os.path.exists(api_path):
            self._load_routes(api_path)

        # Load console routes
        console_path = os.path.join(routes_dir, "console.py")
        if os.path.exists(console_path):
            self._load_routes(console_path)

    def _load_routes(self, path: str):
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location(f"routes.{os.path.basename(path)}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Clear facade cache so Route facade picks up newly registered routes
        from craft.facades.base import Facade
        Facade._clear_resolved()
