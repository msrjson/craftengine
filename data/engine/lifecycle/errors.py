"""Typed refusals of the engine lifecycle (adopt, update, upgrade, hotfix).

Every refusal carries a stable machine `code` and a `message_key`; the engine
never renders a sentence for a user. The `detail` is engineer-facing context.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations


class EngineLifecycleError(RuntimeError):
    """A lifecycle operation the engine refuses.

    Args:
        code: Machine code naming the refusal, e.g. `ENGINE_DRIFT_UNREGISTERED`.
        detail: Engineer-facing context (a path, a ref, a patch id).
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code, detail)
        self.code = code
        self.detail = detail
        self.message_key = "engine.lifecycle.error." + code.lower()
        self.params = {"detail": detail}

    def __str__(self) -> str:
        return " ".join(part for part in (self.code, self.detail) if part)


__all__ = ["EngineLifecycleError"]
