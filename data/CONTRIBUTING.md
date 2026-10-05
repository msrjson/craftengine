# Contributing to Craft

Thanks for considering a contribution. This document covers how to get set up,
what the project expects from a change, and how to report problems.

## Getting set up

Fork the official repository,
<https://github.com/msrjson/craftengine>, then clone your fork:

```bash
git clone <your-fork-url> craft
cd craft
git remote add upstream https://github.com/msrjson/craftengine.git
pip install -e ".[dev]"

cp .env.example .env
python dev.py key:generate
python dev.py migrate --seed
python -m pytest
```

Docker gets you the same environment plus PostgreSQL:

```bash
docker compose up -d --build
docker exec framework python -m pytest
```

## Running the test suite

The suite must pass on **all three** targets before a pull request is ready.
Dialect bugs and version bugs only show up on the target that exercises them.

```bash
# SQLite in memory (the default)
python -m pytest

# PostgreSQL
docker exec framework-db psql -U craft -d craft_db -p 5499 -c "CREATE DATABASE craft_validation;"
CRAFT_TEST_DB=pgsql DB_HOST=127.0.0.1 DB_PORT=5499 \
  DB_DATABASE=craft_validation DB_USERNAME=craft DB_PASSWORD=secretpassword \
  python -m pytest

# Python 3.14, the minimum supported version
docker exec framework python -m pytest
```

Every test file must also pass **on its own**:

```bash
python -m pytest tests/test_orm_model.py
```

A file that only passes as part of the full run is relying on state another test
left behind. That has bitten this project more than once.

## What a good change looks like

**Source code is English.** Identifiers, comments, docstrings, commit messages.
User-facing strings go through the translation layer instead.

**Behaviour changes come with tests.** Not tests that assert the implementation,
tests that would fail if the behaviour regressed. For example, the eager-loading
tests count the SQL queries issued — asserting only on results would pass just as
happily with the N+1 bug they exist to prevent.

**Never degrade silently.** The single largest source of bugs found in this
codebase was code that swallowed an error and returned something plausible: a
view engine returning a placeholder instead of raising, a queue building a fake
payload, a form request returning input it never validated. All of them had
green tests. If a failure cannot be handled, let it raise or log it — do not
paper over it with `except Exception: pass`.

**Keep the diff to the change.** Reformatting unrelated code makes review harder.

## Adding a translation

Locales follow BCP 47: lowercase language, uppercase region — `en`, `pt`,
`pt-BR`, `es`. Lookups fall back `pt-BR → pt → en`, so a regional locale only
needs the keys where it genuinely differs from its base language.

Add entries to `database/seeders/TranslationSeeder.py`. The richer,
semantically-keyed catalog lives in `resources/lang/catalog.json`.

## Versioning and releases

Version is `MAJOR.MINOR.PATCH` plus a release counter (`rNNNNN`), both tracked
in two places that must stay in sync: `pyproject.toml` (`[project].version`)
and `engine/__init__.py` (`__version__`, `__release__`).

**The release counter always increments by exactly 1 on every cut release —
never reset, never skipped, regardless of what `MAJOR.MINOR.PATCH` does.**
`v3.11.0-r00001` was the first cut; the next one, even if it only bumps the
patch version, is `r00002`.

To cut a release:

1. Update `CHANGELOG.md`: rename `## [Unreleased]` to
   `## [X.Y.Z] rNNNNN — YYYY-MM-DD`, then add a fresh empty `## [Unreleased]`
   above it for whatever comes next.
2. Bump `pyproject.toml` and `engine/__init__.py` to match.
3. Run the whole suite on SQLite and PostgreSQL in the `framework` container.
4. Rehearse the CRM demo against the candidate:
   `sh .claude/scripts/rehearse-demo.sh` (workspace root). It installs the
   candidate like any project would and runs the demo's suite on SQLite and
   PostgreSQL; packaging and generator defects are invisible to the
   framework's own suite and surface only here. Do not publish while it fails.
5. Commit and push `master`, then `master:main`. CI runs both databases and
   creates the `vX.Y.Z-rNNNNN` tag and release itself - never tag by hand.

### Every change gets a CHANGELOG entry — no exceptions

Not just at release time. **The same commit or PR that makes a change adds
its line to `## [Unreleased]`.** This is what lets a developer or an AI agent
understand what happened to the framework without reconstructing it from
`git log` — memory and diffs decay, the changelog is the durable record.

Use the standard Keep a Changelog categories under `[Unreleased]`, creating
whichever ones you need:

- **Added** — a new feature, command, endpoint, or capability.
- **Changed** — existing behaviour that shifted (including dependency bumps
  that could affect behaviour, not just version-number churn).
- **Fixed** — a bug, however small. If it changed what the code returns,
  raises, or persists, it's a Fixed entry.
- **Security** — any vulnerability closed, any hardening applied, any
  authn/authz/CSRF/injection/secrets-handling change. Say what the exposure
  was, not just what the patch does — "X could bypass Y because Z" is what
  makes this useful to a future reader deciding whether they're affected.
- **Deprecated** / **Removed** — something going away, or already gone.

A one-line entry is fine for a small fix. A larger change (new subsystem,
security incident) gets a short paragraph — see the `[3.11.0] r00001` entry
for the level of detail expected: what changed, why, and what a reader should
independently verify rather than take on faith.

## Building a release

```bash
python -m pip install build twine
python -m build              # writes dist/*.whl and dist/*.tar.gz
python -m twine check dist/*
```

Building requires **setuptools 77+** — the project uses PEP 639 metadata
(`license` as an SPDX string plus `license-files`), which older versions reject.

Verify the artifact by installing it somewhere the source tree is not
importable, or you end up testing `engine/` on disk rather than the wheel:

```bash
unset PYTHONPATH            # a venv does not override it
python -m venv /tmp/clean
cd /tmp
/tmp/clean/bin/pip install /path/to/dist/craft-3.11.0-py3-none-any.whl
/tmp/clean/bin/python -c 'import services; print(services.__file__)'
/tmp/clean/bin/craft --help
```

`services.__file__` must point inside `site-packages`. If it points at your
checkout, the test proved nothing.

## Reporting a bug

This project is developed locally and is not published. Report problems to
**snarthost@gmail.com** with:

- what you expected and what happened instead
- the database driver and Python version
- the smallest snippet that reproduces it

For security issues, see [SECURITY.md](SECURITY.md).

## Landing a change

1. Branch from `master`.
2. Make the change, with tests.
3. Run the suite on all three targets.
4. Add an entry to `CHANGELOG.md` under the current release heading (see
   "Versioning and releases" above for cutting a new one).
5. Merge, with a commit message describing what changed and why.

## Licence

By contributing you agree that your work is licensed under the
[MIT License](LICENSE) that covers this project.
