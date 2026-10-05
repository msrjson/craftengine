"""Create the catalog fixture's own table (forward-only)."""

from craft.migrations import Schema


def up():
    Schema.create_table("ext_test_catalog_items", lambda t: (
        t.id(),
        t.string("sku").unique(),
        t.timestamps(),
    ))
