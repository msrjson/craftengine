"""Resolution of the application's identity models from configuration.

The engine ships authentication, authorization and the RBAC console commands,
but it does not ship the models those act on. A project declares its own
`User`, `Role`, `Permission` and `Group` and points `config/auth.py` at them.
This module is the single place that turns a configured dotted path into a
class.

It exists because the engine used to import `app.Models.Role` and its
siblings directly, roughly twenty times in `engine/cli/app.py` alone. That
made the framework unable to run its own CLI in a project that had not
recreated the demo application's model layout, which is the opposite of what
a framework is for.
"""

import importlib
from typing import Any, Dict, Final, Optional

#: Configuration keys, by model kind. A project overrides any of these in
#: `config/auth.py` under `models`.
_CONFIG_KEYS: Final[Dict[str, str]] = {
    "user": "auth.models.user",
    "role": "auth.models.role",
    "permission": "auth.models.permission",
    "group": "auth.models.group",
}

#: Why a resolution failed. Callers branch on these rather than on message
#: text, and the console layer maps them to operator guidance.
REASON_UNKNOWN_KIND: Final[str] = "unknown_kind"
REASON_NOT_CONFIGURED: Final[str] = "not_configured"
REASON_IMPORT_FAILED: Final[str] = "import_failed"


class IdentityModelNotConfigured(RuntimeError):
    """Raised when a required identity model is absent or unimportable.

    A developer-facing configuration failure, never rendered to an end user,
    so it carries a stable code and structured parameters instead of a
    sentence.

    Attributes:
        code: Stable machine code for this failure.
        kind: The model kind that could not be resolved.
        reason: One of the `REASON_*` constants.
        params: Additional context, such as the path that failed to import.
    """

    code: str = "IDENTITY_MODEL_NOT_CONFIGURED"

    def __init__(self, kind: str, reason: str, **params: object) -> None:
        super().__init__(self.code)
        self.kind = kind
        self.reason = reason
        self.params = params

    def __str__(self) -> str:
        """Say which model, why, and what to change - not only the code."""
        if self.reason == REASON_IMPORT_FAILED:
            return (
                f"{self.code}: the {self.kind} model path {self.params.get('path')!r} does not import "
                f"({self.params.get('cause')}). Fix the path in config/auth.py or the module it names."
            )
        if self.reason == REASON_NOT_CONFIGURED:
            remedy = "craft make:auth" if self.kind == "user" else "craft make:admin"
            return (
                f"{self.code}: no {self.kind} model is configured ({self.params.get('key')} is empty). "
                f"Run `{remedy}` or point that key at your model class."
            )
        return f"{self.code}: unknown identity model kind {self.kind!r}."


def _import_class(path: str) -> Any:
    """Import a class from a dotted path.

    Args:
        path: A fully qualified path such as `app.Models.User.User`.

    Returns:
        The imported class object.

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the module has no such attribute.
    """
    module_path, _, class_name = path.rpartition(".")
    return getattr(importlib.import_module(module_path), class_name)


def config_key(kind: str) -> str:
    """Return the configuration key backing a model kind.

    Args:
        kind: One of `user`, `role`, `permission`, `group`.

    Returns:
        The dotted configuration key.

    Raises:
        IdentityModelNotConfigured: If `kind` is not a known model kind.
    """
    key = _CONFIG_KEYS.get(kind)
    if key is None:
        raise IdentityModelNotConfigured(kind, REASON_UNKNOWN_KIND)
    return key


def configured_path(kind: str, config: Any) -> Optional[str]:
    """Return the configured dotted path for a model kind, if any.

    Args:
        kind: One of `user`, `role`, `permission`, `group`.
        config: The configuration repository, or None when unavailable.

    Returns:
        The dotted path, or None when nothing is configured.

    Raises:
        IdentityModelNotConfigured: If `kind` is not a known model kind.
    """
    key = config_key(kind)
    if config is None:
        return None
    return config.get(key)


def model_for(kind: str, config: Any) -> Any:
    """Resolve a configured identity model class.

    Args:
        kind: One of `user`, `role`, `permission`, `group`.
        config: The configuration repository.

    Returns:
        The model class.

    Raises:
        IdentityModelNotConfigured: If nothing is configured for `kind`, or
            the configured path cannot be imported.
    """
    path = configured_path(kind, config)
    if not path:
        raise IdentityModelNotConfigured(kind, REASON_NOT_CONFIGURED, key=config_key(kind))
    try:
        return _import_class(path)
    except (ImportError, AttributeError) as exc:
        raise IdentityModelNotConfigured(kind, REASON_IMPORT_FAILED, path=path, cause=str(exc)) from exc


def is_available(kind: str, config: Any) -> bool:
    """Report whether a model kind is configured and importable.

    Used to decide whether an optional console command group should register
    at all, so a bare project does not advertise commands that cannot run.

    Args:
        kind: One of `user`, `role`, `permission`, `group`.
        config: The configuration repository.

    Returns:
        True when `model_for` would succeed.
    """
    try:
        model_for(kind, config)
    except IdentityModelNotConfigured:
        return False
    return True
