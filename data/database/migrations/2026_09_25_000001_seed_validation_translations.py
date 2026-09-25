"""Migration: validation messages in every offered locale.

The `Validator` reports each failure as the translation key
`validation.<code>`; this writes the `en`, `pt-BR` and `es` rows for every
code, leaving alone any row the project already has, so an edited message
survives. Without the rows the English source text is shown.

Forward-only: there is no `down()`; translations are never deleted.

Category: Framework schema (validation).
References:
  - Guide: `documentation/validation.md`
"""

from craft.facades import DB
from craft.validation.messages import seed_translations


def up():
    seed_translations(DB)
