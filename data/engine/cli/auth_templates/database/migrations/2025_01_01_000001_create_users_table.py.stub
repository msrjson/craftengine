"""Create the users table."""

from craft.migrations import Migration, Schema


def up():
    Schema.create_table("users", lambda t: (
        t.id(),
        t.uuid("uuid").nullable(),
        t.string("name"),
        t.string("email").unique(),
        t.string("password"),
        t.string("remember_token").nullable(),
        t.string("api_token").nullable(),
        t.timestamps(),
    ))


def down():
    Schema.drop_table("users")
