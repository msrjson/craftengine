"""
MessageBag / ViewErrorBag for Craft Framework.

Encapsulates validation error messages, providing convenient methods for
view templates and API controllers.
Category: Core Framework (Validation).
Relations:
  - Produced by `engine/validation/validator.py`.
  - Injected into `engine/view/forge.py` as template global `errors`.
References:
  - Guide: `documentation/validation.md#error-messages`
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional


class MessageBag:
    """Convenient container for validation error messages.

    Every entry carries a stable `code` and its translation `message_key` next
    to the rendered text, so an API client can branch on the rule that failed
    without matching a translated string. `add()` records all three; the string
    APIs (`first()`, `all()`, `to_dict()`) are unchanged for templates and for
    callers written before the structured form existed.
    """

    def __init__(self, messages: Optional[Dict[str, List[str]]] = None):
        self._messages: Dict[str, List[str]] = {}
        self._structured: Dict[str, List[Dict[str, Any]]] = {}
        if messages:
            for key, val in messages.items():
                if isinstance(val, list):
                    values = list(val)
                elif isinstance(val, (str, bytes)):
                    values = [str(val)]
                elif val is not None:
                    values = [str(val)]
                else:
                    values = []
                for value in values:
                    self.add(key, str(value))

    def add(
        self,
        key: str,
        message: str,
        code: Optional[str] = None,
        message_key: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> MessageBag:
        """Add an error, with the stable code and translation key that produced it."""
        self._messages.setdefault(key, []).append(message)
        self._structured.setdefault(key, []).append({
            "code": code or "",
            "message_key": message_key or "",
            "message": message,
            "params": dict(params or {}),
        })
        return self

    def errors(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return `{field: [{code, message_key, message, params}, ...]}`.

        The shape an API client consumes: `code` is the rule (`required`,
        `email`, ...), `message_key` is `validation.<code>` and `message` is
        the same text `first()` returns.
        """
        return {
            key: [dict(entry) for entry in entries]
            for key, entries in self._structured.items() if entries
        }

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Dict-compatible setdefault."""
        return self._messages.setdefault(key, [] if default is None else default)

    def has(self, key: str) -> bool:
        """Determine if errors exist for a given field or prefix pattern."""
        if not key:
            return bool(self._messages)
        if key in self._messages and bool(self._messages[key]):
            return True
        # Wildcard or dot-notation support: e.g. "items.*"
        if "*" in key:
            prefix = key.split("*", 1)[0]
            return any(k.startswith(prefix) and bool(msgs) for k, msgs in self._messages.items())
        return False

    def first(self, key: Optional[str] = None, default: str = "") -> str:
        """Get the first error message for a given field or the entire bag."""
        if key is not None:
            msgs = self._messages.get(key)
            if msgs:
                return str(msgs[0])
            return default

        for msgs in self._messages.values():
            if msgs:
                return str(msgs[0])
        return default

    def get(self, key: str) -> List[str]:
        """Get all error messages for a given field."""
        return list(self._messages.get(key, []))

    def all(self) -> List[str]:
        """Flatten all error messages across all fields."""
        flattened: List[str] = []
        for msgs in self._messages.values():
            flattened.extend(msgs)
        return flattened

    def any(self) -> bool:
        """Determine if there are any error messages."""
        return any(bool(msgs) for msgs in self._messages.values())

    def count(self) -> int:
        """Get total number of messages."""
        return sum(len(msgs) for msgs in self._messages.values())

    def keys(self) -> List[str]:
        """Get all fields that have errors."""
        return [k for k, msgs in self._messages.items() if msgs]

    def items(self):
        """Return dict-style items."""
        return [(k, list(v)) for k, v in self._messages.items() if v]

    def values(self):
        """Return dict-style values."""
        return [list(v) for v in self._messages.values() if v]

    def to_dict(self) -> Dict[str, List[str]]:
        """Return raw messages dictionary."""
        return {k: list(v) for k, v in self._messages.items() if v}

    # -- Python protocols ------------------------------------------------------

    def __bool__(self) -> bool:
        return self.any()

    def __len__(self) -> int:
        return len(self.keys())

    def __contains__(self, key: str) -> bool:
        return self.has(key)

    def __getitem__(self, key: str) -> List[str]:
        return self.get(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def __repr__(self) -> str:
        return f"<MessageBag count={self.count()} fields={self.keys()}>"


# Alias for Forge template semantics
ViewErrorBag = MessageBag

__all__ = ["MessageBag", "ViewErrorBag"]
