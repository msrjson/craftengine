"""Minimal ICU MessageFormat renderer: named placeholders and CLDR plurals.

Why this exists:
Building user-facing sentences by string concatenation or f-strings makes translations
inflexible, because grammatical gender, noun cases, and word ordering differ across
languages. ICU MessageFormat provides standard syntax for dynamic values and plurals:

    "You withdrew {amount} successfully."
    "{count, plural, =0 {No open orders} one {# open order} other {# open orders}}"

Supported features:
- `{name}` substitutes a named parameter, formatted with `str()`.
- `{name, plural, ...}` selects a branch matching the CLDR plural category of `name`
  for the active locale. `=N` matches an exact integer value and takes precedence.
  `#` inside the chosen branch renders the number itself.
- Branches may contain further placeholders, and curly braces nest correctly.

Failure policy:
A missing parameter or malformed message degrades gracefully by returning the raw
message unchanged rather than raising a 500 error in the middle of a request.

Category: Core Framework (Support / i18n).
Relations:
  - Consumed by `engine/support/translation.py` (`translate()` and `__()`).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Mapping

#: Locales whose plural rules follow the one/other shape where n=1 is one.
_PLURAL_ONE_OTHER = ("en", "de", "nl", "sv", "da", "no", "fi", "et", "el", "it", "es")

#: Locales where n in [0, 1] takes the `one` category in CLDR (e.g., pt-BR, fr).
_PLURAL_ZERO_IS_ONE = ("pt", "fr")


def plural_category(locale: str, number: float | int | Decimal) -> str:
    """Return the CLDR plural category of `number` for `locale`.

    Categories are standard CLDR names: 'zero', 'one', 'two', 'few', 'many', 'other'.
    English, Spanish, and Portuguese primarily use 'one' and 'other'.
    """
    language = (locale or "").replace("-", "_").split("_")[0].lower()

    try:
        value = abs(Decimal(str(number)))
    except Exception:
        return "other"

    is_integer = value == value.to_integral_value()

    if language in _PLURAL_ZERO_IS_ONE:
        return "one" if is_integer and value <= 1 else "other"

    return "one" if is_integer and value == 1 else "other"


def _find_matching_brace(text: str, start: int) -> int:
    """Index of the `}` closing the `{` at `start`, or -1 when unbalanced."""
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


_ARG_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,\s*(plural)\s*,(.*))?$", re.S)
_BRANCH_RE = re.compile(r"(=\d+|zero|one|two|few|many|other)\s*\{", re.S)


def _parse_branches(body: str) -> dict[str, str]:
    """Split `=0 {..} one {..} other {..}` into a selector -> template map."""
    branches: dict[str, str] = {}
    position = 0
    while True:
        match = _BRANCH_RE.search(body, position)
        if not match:
            break
        opening = match.end() - 1
        closing = _find_matching_brace(body, opening)
        if closing == -1:
            break
        branches[match.group(1)] = body[opening + 1 : closing]
        position = closing + 1
    return branches


def format_message(message: str, params: Mapping[str, Any], locale: str = "en") -> str:
    """Render an ICU `message`, substituting `params` for the active `locale`.

    Never raises: if a message is malformed or an argument is missing, the raw
    template is preserved so that broken copy is noticeable without crashing.
    """
    if not message or "{" not in message:
        return message or ""

    output: list[str] = []
    index = 0
    length = len(message)

    while index < length:
        char = message[index]

        if char != "{":
            output.append(char)
            index += 1
            continue

        closing = _find_matching_brace(message, index)
        if closing == -1:
            # Unbalanced brace: emit the rest verbatim
            output.append(message[index:])
            break

        inner = message[index + 1 : closing]
        parsed = _ARG_RE.match(inner)

        if not parsed:
            output.append(message[index : closing + 1])
            index = closing + 1
            continue

        name, kind, body = parsed.group(1), parsed.group(2), parsed.group(3)

        if name not in params:
            output.append(message[index : closing + 1])
            index = closing + 1
            continue

        value = params[name]

        if kind != "plural":
            output.append(str(value))
            index = closing + 1
            continue

        branches = _parse_branches(body or "")
        try:
            exact = f"={int(Decimal(str(value)))}"
        except Exception:
            exact = None

        template = None
        if exact is not None and exact in branches:
            template = branches[exact]
        if template is None:
            template = branches.get(plural_category(locale, value))
        if template is None:
            template = branches.get("other", "")

        rendered = format_message(template, params, locale)
        output.append(rendered.replace("#", str(value)))
        index = closing + 1

    return "".join(output)


__all__ = ["plural_category", "format_message"]
