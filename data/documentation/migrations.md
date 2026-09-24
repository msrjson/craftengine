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
