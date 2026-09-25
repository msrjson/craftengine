"""Config Repository for Craft Framework."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import importlib.util
import os
from typing import Any, Dict, Optional


def load_dotenv(path: str, override: bool = False) -> Dict[str, str]:
    """Load a `.env` file into `os.environ`.

    Supports `KEY=value`, quoted values, `#` comments and `${VAR}` interpolation
    against values already loaded. Existing environment variables win unless
    `override` is set, so real env vars stay authoritative in production.
    """
    loaded: Dict[str, str] = {}
    if not os.path.isfile(path):
        return loaded

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            else:
                value = value.split(" #", 1)[0].strip()

            for name, resolved in list(loaded.items()) + list(os.environ.items()):
                value = value.replace(f"${{{name}}}", resolved)

            if value.lower() in ("null", "none"):
                value = ""

            loaded[key] = value
            if override or key not in os.environ:
                os.environ[key] = value

    return loaded


def env(key: str, default: Any = None) -> Any:
    """Helper to retrieve environment variables with type coercion."""
    val = os.environ.get(key)
    if val is None:
        return default
    lowered = val.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "none", ""):
        return default
    if val.isdigit():
        return int(val)
    return val


class MissingConfigKeyError(KeyError):
    """A required configuration key does not exist."""

    def __init__(self, key: str, suggestions: list) -> None:
        super().__init__(key)
        self.key = key
        self.suggestions = suggestions

    def __str__(self) -> str:
        from engine.support.diagnostics import describe

        return describe("CONFIG_KEY_MISSING", key=self.key, closest=", ".join(self.suggestions) or "none")


class ConfigRepository:
    """Repository storing application configurations with dot notation access."""

    def __init__(self, config_dir: Optional[str] = None):
        self._items: Dict[str, Any] = {}
        if config_dir and os.path.exists(config_dir):
            self.load_from_directory(config_dir)

    def load_from_directory(self, config_dir: str) -> None:
        for file in os.listdir(config_dir):
            if file.endswith(".py") and not file.startswith("__"):
                key = file[:-3]
                file_path = os.path.join(config_dir, file)
                spec = importlib.util.spec_from_file_location(f"config.{key}", file_path)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    config_dict = {}
                    for attr in dir(mod):
                        if not attr.startswith("__") and not callable(getattr(mod, attr)):
                            config_dict[attr.lower()] = getattr(mod, attr)
                            config_dict[attr] = getattr(mod, attr)
                    self._items[key] = config_dict

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        current = self._items

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def require(self, key: str) -> Any:
        """Return the value at `key`, or raise naming the closest existing keys.

        `get()` answers None for a key that does not exist, so a typo reads as
        "not configured". Keys use the module attribute name: `app.APP_DEBUG`
        (or `app.app_debug`), never `app.debug`.

        Raises:
            MissingConfigKeyError: `key` does not exist.
        """
        missing = object()
        value = self.get(key, missing)
        if value is missing:
            raise MissingConfigKeyError(key, self.suggest(key))
        return value

    def suggest(self, key: str) -> list:
        """Return up to three existing keys closest to `key`."""
        import difflib

        flat: list = []

        def walk(prefix: str, node: Any) -> None:
            for name, child in node.items():
                path = f"{prefix}.{name}" if prefix else str(name)
                flat.append(path)
                if isinstance(child, dict) and len(flat) < 5000:
                    walk(path, child)

        walk("", self._items)
        return difflib.get_close_matches(key, flat, n=3, cutoff=0.5)

    def set(self, key: str, value: Any) -> None:
        parts = key.split(".")
        current = self._items

        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def has(self, key: str) -> bool:
        return self.get(key) is not None
