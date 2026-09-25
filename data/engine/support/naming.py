"""Naming rules shared by the ORM and the code generators.

A model without `__table__` and the migration `make:model`/`make:crud` writes
for it must agree on the table name. They used to follow two different rules
(`Category` -> `categorys` in the ORM, `categories` in the migration), so a
hand-written model failed late with "relation does not exist".

Category: Core Framework (Support).
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

import re


def snake(value: str) -> str:
    """Return `value` in snake_case: `BlogPost` -> `blog_post`."""
    value = re.sub(r"[\-\s]+", "_", value)
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value)
    return re.sub(r"__+", "_", value).lower()


def plural(word: str) -> str:
    """Return the English plural of a snake_case word: `category` -> `categories`."""
    if word.endswith("y") and not word.endswith(("ay", "ey", "iy", "oy", "uy")):
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def table_for(model: str) -> str:
    """Return the table name for a model class name: `BlogPost` -> `blog_posts`."""
    return plural(snake(model))


__all__ = ["plural", "snake", "table_for"]
