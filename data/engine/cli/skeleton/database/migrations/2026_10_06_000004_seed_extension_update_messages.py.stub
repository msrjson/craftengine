"""Seed missing ownership and extension update messages without replacing edits.

Category: Framework schema (extensions).
Relations: craft.extensions.messages seeds the engine catalog in three locales.
References: documentation/extensions.md.
"""

from craft.extensions.messages import seed_messages
from craft.facades import DB


def up() -> None:
    """Add only missing translation rows; schema and existing copy stay intact."""
    seed_messages(DB)
