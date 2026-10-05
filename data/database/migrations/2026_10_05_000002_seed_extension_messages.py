"""Migration: extension messages added after the `extensions` table shipped.

Seeds every key of `engine/extensions/lang/catalog.json` the translation store
lacks (`extension.error.extension_route_conflict` arrived in 4.4.1), in `en`,
`pt-BR` and `es`. Existing rows are left alone.

Forward-only: there is no `down()`; translations are never deleted.

Category: Framework schema (extensions).
"""

from craft.extensions.messages import seed_messages
from craft.facades import DB


def up():
    seed_messages(DB)
