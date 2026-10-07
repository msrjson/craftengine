# Release synchronization

`dev.py release:sync` applies the pending migrations and runs the release
seeders, then records what it did. Run it on every deploy — it is idempotent and
does nothing when there is nothing to do.

## Why it exists

A migration creates a column; it does not create the *rows* the system needs to
serve. Those are born in a seeder, and a seeder that only runs when someone
remembers leaves the screen empty after a deploy on an environment nobody opens
a terminal on. `release:sync` does both, in order, in one step.

## The `VERSION` file

`VERSION` at the application root carries the release identity the deployed code
must match, `MAJOR.MINOR.PATCH-rNNNNN`. `release:sync` refuses to run when the
file disagrees with the running code (`RELEASE_VERSION_DRIFT`) or is missing
(`RELEASE_VERSION_FILE_MISSING`): a mismatch is a stale image or a half-finished
release, and migrating a node from code nobody can name is how a schema moves
without a record.

## The trail

Every run appends one row to `release_syncs` — the version, the migration and
seeder counts, the status and the duration. Nothing is deleted: the previous row
is the proof of which release left the database in its current state.
`release:status` reads it back, alongside the running identity and the `VERSION`
file.

## Commands

```bash
python dev.py release:status   # identity, VERSION file, last sync
python dev.py release:sync     # migrate, seed, record
```

On PostgreSQL the whole sync runs under the migrator's advisory lock
(`craft:migrations`), so two containers starting at once cannot migrate the same
node concurrently. On a driver without advisory locks it runs unlocked.
