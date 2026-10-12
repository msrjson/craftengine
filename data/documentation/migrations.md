# Migrations, Seeders & Factories

Craft provides database schema version control (Migrations) and database seeding tools (Seeders and Factories) to set up and manage database states across different environments.

---

## Migrations

Migrations are stored in `database/migrations/` and contain two functions: `up()` to create/modify tables, and `down()` to reverse the change.

### Example Migration

```python
from craft.migrations import Migration, Schema

def up():
    Schema.create_table("posts", lambda t: (
        t.id(),
        t.string("title").unique(),
        t.text("body"),
        t.boolean("published").default(False),
        t.foreign_id("user_id").constrained().cascade_on_delete(),
        t.timestamps(),
    ))

def down():
    Schema.drop_table("posts")
```

### Table Column Types

The table builder object (`t`) supports the following data type definitions:

- `t.id()`: Auto-incrementing or UUID primary key.
- `t.string(name)`: Standard character string.
- `t.text(name)`: Rich/long text block.
- `t.integer(name)`: Number field.
- `t.boolean(name)`: True/False field.
- `t.uuid(name)`: Plain (non-unique) UUID column.
- `t.uuid_key()`: Unique, indexed UUID column — the public identifier that models fill automatically alongside the numeric `id`.
- `t.uuid_primary()`: UUID as the primary key itself (pair with `key_type = "uuid"` on the model).
- `t.timestamps()`: Automatically generates `created_at` and `updated_at` datetime columns.
- `t.foreign_id(name).constrained()`: Creates a foreign key constraint linking to the referenced primary key.

### Running Migrations

Manage database schemas incrementally using the `dev.py` CLI:

```bash
# Run all pending forward migrations
python dev.py migrate

# Preview queries without modifying the database
python dev.py migrate --pretend

# View migration history and applied batches
python dev.py migrate:status
```

> **Data persistence:** Rollback and reset operations are refused in every environment. All schema evolution must be forward-only. See [Database Safety](database_safety.md).

---

## Seeders

Seeders populate your database with initial reference records and system data. Seeders should be written idempotently so they can run safely without purging or duplicating data. They inherit from `craft.seeding.Seeder` and define a `run` method:

### Example Seeder

```python
from craft.seeding import Seeder
from app.Models.User import User

class DatabaseSeeder(Seeder):
    def run(self):
        # 1. Idempotent check or creation
        if not User.query().where("email", "admin@craft.io").exists():
            User.create({
                "name": "Admin User",
                "email": "admin@craft.io",
                "password": "hashed-secret-password"
            })
```

Execute seeders by running:
```bash
python dev.py db seed
```

### Seeding once (`SEED_ONCE`)

A seeder that checks for a row before inserting it is idempotent only while
that row stays as it was seeded. Once someone edits the row, the check no
longer finds it and the next run inserts a second copy. A seeder that must
never run twice declares `SEED_ONCE`:

```python
from craft.seeding import Seeder


class PlatformCatalogSeeder(Seeder):
    SEED_ONCE = "platform_catalog"   # a stable key; or True to key on the module and class name

    def run(self):
        ...
```

`db seed`, `release:sync` and `Seeder.call()` look the key up in the
`seed_ledger` table before running the seeder, skip it when the key is there,
and record the key after a successful run. The ledger is append-only.

- The table comes from the migration
  `2026_10_07_000003_create_seed_ledger_table.py`. Before it has run there is
  no ledger: a once-only seeder runs and is **not** recorded, so migrate first.
- Renaming a seeder declared with `SEED_ONCE = True` changes its key and it
  runs again. Use a string when the class may move.

---

## Factories

Factories define the default attribute layout for a model. `definition()`
returns a plain dict — there is no bundled fake-data library, so use the
standard library, or add `faker` to your own project and call it yourself.

### Example Factory

```python
import random
import uuid

from craft.factories import Factory
from app.Models.Post import Post

class PostFactory(Factory):
    model = Post

    def definition(self):
        return {
            "title": f"Post {uuid.uuid4().hex[:8]}",
            "body": " ".join(random.choices(WORDS, k=30)),
            "published": True,
            "user_id": 1,
        }
```

Every value must be unique where the schema demands it — a factory that
returns a constant for a `unique` column fails on the second record.

Use factories within seeders or unit tests to generate multiple records quickly:
```python
# Create and save a single post to the database
post = PostFactory.new().create()

# Generate a list of 5 unsaved post model instances
posts = PostFactory.new().count(5).make()
```

## PostgreSQL schema features

Partial, expression, GIN/GiST/HNSW and `CONCURRENTLY` indexes, `CHECK` and
`EXCLUDE` constraints, declarative partitioning, managed extensions and
row-level security policies are covered in
[PostgreSQL](postgres.md#schema).

### Materialized views that block a migration (PostgreSQL only)

PostgreSQL refuses to alter a column a materialized view depends on, so a
database whose views were created outside the migrations cannot migrate. Opt in
to have the migrator step around them:

```ini
MIGRATION_SUSPEND_MATERIALIZED_VIEWS=true
```

With the flag on (`framework.MIGRATION_SUSPEND_MATERIALIZED_VIEWS`, default
`false`), `migrate` drops every materialized view before the pending batch and
recreates each one afterwards with its indexes, retrying in passes so a view
that depends on another comes back in the right order. The views are restored
even when a migration in the batch fails; `migrate --pretend` suspends nothing.

- Recreating a view recomputes its data, which is why this is off by default.
  On a large view the migration takes as long as the refresh.
- A view that cannot be recreated - its definition no longer matches the
  migrated schema - stops the run with `MIGRATION_VIEW_RESTORE_FAILED` and the
  names of the views still missing.
- On other drivers the flag does nothing.
