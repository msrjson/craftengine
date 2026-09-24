"""Recording generated identity models in `config/auth.py`.

The engine resolves `User`, `Role`, `Permission` and `Group` from
configuration rather than importing `app.Models.*` (see
`engine/auth/registry.py`). A generator that writes one of those classes and
does not declare it leaves the engine unable to find it: authentication falls
over, and the RBAC console commands decline to register.

Both `make:auth` and `make:admin` write identity models, so the parsing lives
here once. Two implementations of the same edit would drift, and the failure
would be a configuration file that looks right and resolves to nothing.
"""

from __future__ import annotations

import os
import re
from typing import Dict, Optional

#: Where each model kind is declared inside `config/auth.py`.
MODELS_BLOCK_PATTERN = re.compile(r"^models\s*=\s*\{", re.MULTILINE)


def _fill_entries(content: str, models: Dict[str, str]) -> str:
    """Point empty `models` entries at the generated classes.

    Only an entry left empty is filled, so a project that named its own class
    keeps it.

    Args:
        content: Current contents of `config/auth.py`.
        models: Model kind to dotted path.

    Returns:
        The updated contents.
    """
    for kind, dotted_path in models.items():
        pattern = rf'(["\']{kind}["\']\s*:\s*)["\']["\']'
        content = re.sub(pattern, rf'\g<1>"{dotted_path}"', content)
    return content


def _models_block(models: Dict[str, str]) -> str:
    """Return a `models` block naming the generated classes.

    Written only into a `config/auth.py` that has no `models` mapping at all.

    Args:
        models: Model kind to dotted path.

    Returns:
        The Python source of the block, including its explanatory comment.
    """
    entries = "".join(f'    "{kind}": "{path}",\n' for kind, path in models.items())
    return (
        "\n# Identity models written by a `craft make:` command, resolved by the\n"
        "# engine through `craft.auth.registry`.\n"
        f"models = {{\n{entries}}}\n"
    )


def _fill_provider_model(content: str, dotted_path: str) -> str:
    """Point an empty `providers.users.model` at the generated user class.

    The guard reads its subject from the provider, so a filled `models` entry
    with an empty provider still cannot authenticate anyone.

    Args:
        content: Current contents of `config/auth.py`.
        dotted_path: Dotted path to the user model.

    Returns:
        The updated contents.
    """
    return re.sub(r'(["\']model["\']\s*:\s*)["\']["\']', rf'\g<1>"{dotted_path}"', content, count=1)


def record_models(base_path: str, models: Dict[str, str], *, user_provider: bool = False) -> Optional[str]:
    """Declare generated identity models in `config/auth.py`.

    Args:
        base_path: Root of the target project.
        models: Model kind (`user`, `role`, `permission`, `group`) to the
            dotted path of the generated class.
        user_provider: Also point the default provider's `model` at the user
            class. Passed by `make:auth`, which owns authentication.

    Returns:
        The path to `config/auth.py`, or None when the project has no such
        file.
    """
    config_path = os.path.join(base_path, "config", "auth.py")
    if not os.path.isfile(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    updated = _fill_entries(content, models)
    if user_provider and "user" in models:
        updated = _fill_provider_model(updated, models["user"])
    if not MODELS_BLOCK_PATTERN.search(updated):
        updated = updated.rstrip("\n") + "\n" + _models_block(models)

    if updated != content:
        with open(config_path, "w", encoding="utf-8") as handle:
            handle.write(updated)
    return config_path
