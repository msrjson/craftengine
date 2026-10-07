---
task: p2-20261003-223123-relation-read-as-property-hint
outcome: resolved
agent: qwen@qwen-code (Qwen Code, local Ollama)
started_at: 2026-10-07T16:09:49Z
finished_at: 2026-10-07T16:16:11Z
---

## What changed

- `data/engine/orm/model.py`: a `_RelationMethod` descriptor now stands in for
  each relation method a `Model` subclass declares. `Model.__init_subclass__`
  finds them with `_is_relation_declaration()`, which scans the method's bytecode
  for a relation builder (`has_many`/`has_one`/`belongs_to`/`belongs_to_many`) -
  so only methods that actually declare a relation are wrapped, and no
  application code runs at class-definition time. Read from an instance the
  descriptor returns a `_RelationAccessor`: calling it builds the relation
  exactly as before, while reading an attribute from it - the missing-call
  mistake `post.author.name` - raises the hint instead of
  `'function' object has no attribute 'name'`. Read from the class it returns
  the plain function, so `with_()` and `Model.posts(model)` are unchanged.
- `data/engine/support/diagnostics.py`: new `MODEL_RELATION_NOT_CALLED` catalog
  message naming the model, the relation, the call form (`Model.relation().first()`)
  and the eager-load form (`Model.query().with_("relation")`).
- `data/tests/test_orm_model.py`: `TestRelationUsedAsAttribute` - the hint, a
  loaded relation resolved from the cache, calling the relation, and a plain
  attribute still read as before.
- `data/CHANGELOG.md`: entry under `[Unreleased]` → `### Fixed`.

## Verification

```bash
# the exact mistake now explains itself, and the class access is untouched
docker exec framework sh -lc 'cd /app && python -c "..."'
# HINT: Post.author is a relationship, not a loaded value. Call it to build the
# relation - Post.author().first() for one row or Post.author().get() for many -
# or eager load it up front with Post.query().with_(\"author\").
# class access is the function: True function
# built relation: BelongsTo

docker exec framework sh -lc 'cd /app && python -m pytest tests/test_orm_model.py tests/test_eager_loading.py -q'
# 71 passed in 1.21s

# full suite, SQLite (.env moved aside so the run reproduces CI)
docker exec framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2076 passed, 68 skipped in 124.75s

# full suite, PostgreSQL
docker exec -e CRAFT_TEST_DB=pgsql -e DB_SSLMODE=disable framework sh -lc 'cd /app && mv .env /tmp/env.bak; python -m pytest tests -q; mv /tmp/env.bak .env'
# 2139 passed, 5 skipped in 169.87s

docker exec framework sh -lc 'cd /app && ruff check engine'
# All checks passed!

cd data && python tools/check_engine_boundary.py
# ENGINE_BOUNDARY_NEW_FINDINGS 0

cd data && python3 ../.agents/rules/lint_language.py --config language-standard.toml
# Language standard: clean.
```

The task's suggested `tests/test_orm_relations.py` does not exist; the existing
relation module `tests/test_orm_model.py` carried the coverage instead.

## Follow-ups

None.
